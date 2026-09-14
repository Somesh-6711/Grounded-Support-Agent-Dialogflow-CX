"""Guardrails for agent-callable endpoints.

The agent decides *what* to call. This module decides what is allowed to
happen when it does. Three separate concerns:

1. Input validation  — reject malformed identifiers before any lookup runs.
2. Action policy     — read actions are open, write actions require an
                       explicit confirmation flag set by a human turn.
3. Log redaction     — account identifiers never reach stdout in the clear.

The same shape as the SQL-agent controls: read-only by default, an allowlist
for anything with side effects, and a hard ceiling on input size.
"""

import re

ACCOUNT_ID_RE = re.compile(r"^OPT-\d{8}$")
ZIP_RE = re.compile(r"^\d{5}$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

MAX_FREE_TEXT_CHARS = 500

# Actions with no side effects. Safe for the model to call unprompted.
READ_ACTIONS = {"get_account_status", "check_outage", "list_appointment_slots"}

# Actions that mutate state or page a human. Require confirm=true, which the
# playbook is instructed to set only after the customer says yes in words.
WRITE_ACTIONS = {"schedule_technician", "escalate_to_human"}


class GuardrailError(Exception):
    """Raised when a request violates policy. Surfaced as a 4xx with a
    model-readable message and no internal detail."""

    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def validate_account_id(value: str) -> str:
    if not value or not ACCOUNT_ID_RE.match(value.strip()):
        raise GuardrailError(
            code="invalid_account_id",
            message="Account ID must look like OPT- followed by 8 digits.",
        )
    return value.strip()


def validate_zip(value: str) -> str:
    if not value or not ZIP_RE.match(value.strip()):
        raise GuardrailError(
            code="invalid_zip",
            message="ZIP code must be exactly 5 digits.",
        )
    return value.strip()


def validate_date(value: str) -> str:
    if not value or not ISO_DATE_RE.match(value.strip()):
        raise GuardrailError(
            code="invalid_date",
            message="Date must be in YYYY-MM-DD format.",
        )
    return value.strip()


def validate_free_text(value: str, field: str) -> str:
    text = (value or "").strip()
    if not text:
        raise GuardrailError(code="missing_field", message=f"{field} is required.")
    if len(text) > MAX_FREE_TEXT_CHARS:
        raise GuardrailError(
            code="field_too_long",
            message=f"{field} must be under {MAX_FREE_TEXT_CHARS} characters.",
        )
    return text


def require_confirmation(action: str, confirmed: bool) -> None:
    """Human-in-the-loop gate. A generative agent is perfectly capable of
    deciding on its own that a truck should be dispatched. It does not get to."""
    if action in WRITE_ACTIONS and not confirmed:
        raise GuardrailError(
            code="confirmation_required",
            message=(
                "This action changes the customer's account. Ask the customer "
                "to confirm in their own words, then call again with confirm=true."
            ),
            status_code=409,
        )


_ACCOUNT_PATTERN = re.compile(r"OPT-\d{8}")
_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_PHONE_PATTERN = re.compile(r"\+?\d[\d\s().-]{8,}\d")


def redact(text: str) -> str:
    """Mask identifiers before anything is written to logs."""
    text = _ACCOUNT_PATTERN.sub(lambda m: f"OPT-****{m.group(0)[-4:]}", text)
    text = _EMAIL_PATTERN.sub("<email>", text)
    text = _PHONE_PATTERN.sub("<phone>", text)
    return text
