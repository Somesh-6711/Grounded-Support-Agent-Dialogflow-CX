"""CES demo service for Google Conversational Agents (formerly Dialogflow CX).

One FastAPI app, two integration surfaces:

  /tools/*   REST endpoints described by openapi/tools.yaml. A generative
             Playbook calls these through an OpenAPI Tool. This is the
             modern path and the one the interview will care about.

  /webhook   A classic Dialogflow CX webhook speaking WebhookRequest /
             WebhookResponse, dispatched on fulfillmentInfo.tag. Included
             because Conversational Agents is hybrid: generative playbooks
             sitting alongside deterministic flows, and flows still fulfil
             through webhooks.

  /healthz   Cloud Run health probe.
  /stats     P50/P95/P99 per route, so latency is a number and not a feeling.

All data is synthetic. See app/mock_data.py.
"""

import logging
import time
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.guardrails import (
    GuardrailError,
    redact,
    require_confirmation,
    validate_account_id,
    validate_date,
    validate_free_text,
    validate_zip,
)
from app.mock_data import (
    ACCOUNTS,
    BOOKED_APPOINTMENTS,
    ESCALATIONS,
    OUTAGES,
    available_slots,
)
from app.observability import LATENCY

logging.basicConfig(
    level=logging.INFO,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","msg":%(message)s}',
)
log = logging.getLogger("ces-demo")

app = FastAPI(
    title="CES Demo Tool Service",
    description="Account, outage and dispatch tools for a Conversational Agents playbook.",
    version="1.0.0",
)


# --------------------------------------------------------------------------
# Middleware: request id, latency, redacted structured logging
# --------------------------------------------------------------------------

@app.middleware("http")
async def observe(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    started = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["x-request-id"] = request_id
        return response
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000
        route = request.url.path
        LATENCY.record(route, elapsed_ms, is_error=status >= 400)
        log.info(
            redact(
                f'"{route} status={status} latency_ms={elapsed_ms:.1f} '
                f'request_id={request_id}"'
            )
        )


@app.exception_handler(GuardrailError)
async def guardrail_handler(request: Request, exc: GuardrailError):
    """Guardrail rejections are returned in a shape the model can read and
    act on, without leaking stack traces or internal identifiers."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"ok": False, "error_code": exc.code, "message": exc.message},
    )


# --------------------------------------------------------------------------
# Tool request models
# --------------------------------------------------------------------------

class AccountRequest(BaseModel):
    account_id: str = Field(..., description="Customer account ID, format OPT-12345678.")


class OutageRequest(BaseModel):
    zip_code: str = Field(..., description="5-digit service ZIP code.")


class SlotsRequest(BaseModel):
    zip_code: str = Field(..., description="5-digit service ZIP code.")


class ScheduleRequest(BaseModel):
    account_id: str = Field(..., description="Customer account ID, format OPT-12345678.")
    preferred_date: str = Field(..., description="Requested date, YYYY-MM-DD.")
    window: str = Field(..., description="Arrival window, e.g. 08:00-12:00.")
    confirm: bool = Field(
        False,
        description=(
            "Must be true. Set this only after the customer has explicitly "
            "agreed to the specific date and window."
        ),
    )


class EscalateRequest(BaseModel):
    account_id: str = Field(..., description="Customer account ID, format OPT-12345678.")
    reason: str = Field(..., description="Short reason for handing off to a human.")
    sentiment: str = Field(
        "neutral", description="One of: neutral, frustrated, angry."
    )
    confirm: bool = Field(
        False, description="Must be true. Confirm the customer wants a human."
    )


# --------------------------------------------------------------------------
# Tool endpoints — called by the playbook via the OpenAPI tool
# --------------------------------------------------------------------------

@app.post("/tools/account-status", operation_id="get_account_status")
def get_account_status(body: AccountRequest) -> dict[str, Any]:
    account_id = validate_account_id(body.account_id)
    account = ACCOUNTS.get(account_id)
    if not account:
        raise GuardrailError(
            code="account_not_found",
            message="No account matches that ID. Ask the customer to re-read it.",
            status_code=404,
        )
    return {"ok": True, **account}


@app.post("/tools/outage-check", operation_id="check_outage")
def check_outage(body: OutageRequest) -> dict[str, Any]:
    zip_code = validate_zip(body.zip_code)
    outage = OUTAGES.get(zip_code)
    if outage is None:
        return {
            "ok": True,
            "zip_code": zip_code,
            "outage_active": False,
            "note": "No incident data for this ZIP. Treat as no known outage.",
        }
    return {"ok": True, "zip_code": zip_code, **outage}


@app.post("/tools/appointment-slots", operation_id="list_appointment_slots")
def list_appointment_slots(body: SlotsRequest) -> dict[str, Any]:
    zip_code = validate_zip(body.zip_code)
    return {"ok": True, "zip_code": zip_code, "slots": available_slots()}


@app.post("/tools/schedule-technician", operation_id="schedule_technician")
def schedule_technician(body: ScheduleRequest) -> dict[str, Any]:
    require_confirmation("schedule_technician", body.confirm)
    account_id = validate_account_id(body.account_id)
    preferred_date = validate_date(body.preferred_date)
    window = validate_free_text(body.window, "window")

    if account_id not in ACCOUNTS:
        raise GuardrailError(
            code="account_not_found",
            message="No account matches that ID.",
            status_code=404,
        )

    valid = {(s["date"], s["window"]) for s in available_slots()}
    if (preferred_date, window) not in valid:
        raise GuardrailError(
            code="slot_unavailable",
            message=(
                "That date and window is not available. Call "
                "list_appointment_slots and offer the customer a real option."
            ),
        )

    booking = {
        "confirmation_number": f"APT-{uuid.uuid4().hex[:8].upper()}",
        "account_id": account_id,
        "date": preferred_date,
        "window": window,
    }
    BOOKED_APPOINTMENTS.append(booking)
    return {"ok": True, **booking}


@app.post("/tools/escalate", operation_id="escalate_to_human")
def escalate_to_human(body: EscalateRequest) -> dict[str, Any]:
    require_confirmation("escalate_to_human", body.confirm)
    account_id = validate_account_id(body.account_id)
    reason = validate_free_text(body.reason, "reason")
    sentiment = body.sentiment if body.sentiment in {"neutral", "frustrated", "angry"} else "neutral"

    ticket = {
        "ticket_id": f"ESC-{uuid.uuid4().hex[:8].upper()}",
        "account_id": account_id,
        "reason": reason,
        "sentiment": sentiment,
        "queue": "tier-2-voice" if sentiment == "angry" else "tier-1-chat",
    }
    ESCALATIONS.append(ticket)
    return {"ok": True, **ticket}


# --------------------------------------------------------------------------
# Classic Dialogflow CX webhook — flow fulfilment
# --------------------------------------------------------------------------

@app.post("/webhook")
async def cx_webhook(request: Request) -> dict[str, Any]:
    """Speaks the Dialogflow CX WebhookRequest / WebhookResponse contract.

    Dispatch is on fulfillmentInfo.tag, which you set on the fulfillment in
    the flow. Session parameters written back under sessionInfo.parameters
    are visible to later pages and to the playbook if the flow hands off.
    """
    payload = await request.json()
    tag = (payload.get("fulfillmentInfo") or {}).get("tag", "")
    params = (payload.get("sessionInfo") or {}).get("parameters") or {}

    if tag == "lookup-account":
        return _handle_lookup_account(params)
    if tag == "check-outage":
        return _handle_check_outage(params)

    return _cx_response(
        "I ran into a configuration problem on my side. Let me get you to a specialist."
    )


def _handle_lookup_account(params: dict) -> dict[str, Any]:
    raw = str(params.get("account_id") or "")
    try:
        account_id = validate_account_id(raw)
    except GuardrailError as exc:
        return _cx_response(exc.message, {"account_valid": False})

    account = ACCOUNTS.get(account_id)
    if not account:
        return _cx_response(
            "I couldn't find that account. Could you read the ID back to me?",
            {"account_valid": False},
        )

    balance = account["balance_due_usd"]
    if account["service_status"] == "suspended_nonpayment":
        message = (
            f"That account is currently suspended for non-payment, with "
            f"${balance:.2f} outstanding. I can walk you through restoring service."
        )
    elif balance > 0:
        message = (
            f"Your {account['plan']} plan is active. You have ${balance:.2f} due "
            f"on {account['due_date']}."
        )
    else:
        message = f"Your {account['plan']} plan is active with nothing currently due."

    return _cx_response(
        message,
        {
            "account_valid": True,
            "service_status": account["service_status"],
            "service_zip": account["service_zip"],
        },
    )


def _handle_check_outage(params: dict) -> dict[str, Any]:
    raw = str(params.get("zip_code") or params.get("service_zip") or "")
    try:
        zip_code = validate_zip(raw)
    except GuardrailError as exc:
        return _cx_response(exc.message, {"outage_active": False})

    outage = OUTAGES.get(zip_code, {"outage_active": False})
    if outage.get("outage_active"):
        message = (
            f"There is a known outage in {zip_code} affecting "
            f"{', '.join(outage['services_affected'])}. Crews are on it, with "
            f"service expected back around {outage['estimated_restore']}."
        )
    else:
        message = (
            f"I'm not seeing a network outage in {zip_code}, so this is likely "
            f"something specific to your equipment. Let's troubleshoot it."
        )

    return _cx_response(
        message,
        {"outage_active": bool(outage.get("outage_active")), "zip_code": zip_code},
    )


def _cx_response(text: str, parameters: dict | None = None) -> dict[str, Any]:
    """Build a WebhookResponse. Session parameters are optional."""
    response: dict[str, Any] = {
        "fulfillmentResponse": {"messages": [{"text": {"text": [text]}}]}
    }
    if parameters:
        response["sessionInfo"] = {"parameters": parameters}
    return response


# --------------------------------------------------------------------------
# Operational endpoints
# --------------------------------------------------------------------------

@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/stats")
def stats() -> dict[str, Any]:
    return LATENCY.snapshot()
