"""Smoke tests for the CES demo service.

These are the tests you point at in an interview when someone asks how you
know an agent tool works. Not "I tried it in the console" — a suite that
covers the happy path, the guardrail rejections, and the webhook contract.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# --- tool endpoints -------------------------------------------------------

def test_account_status_happy_path():
    r = client.post("/tools/account-status", json={"account_id": "OPT-10045512"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["plan"] == "1 Gig Internet + Mobile"
    assert body["balance_due_usd"] == 89.99


def test_account_status_rejects_malformed_id():
    r = client.post("/tools/account-status", json={"account_id": "12345"})
    assert r.status_code == 400
    assert r.json()["error_code"] == "invalid_account_id"


def test_account_status_unknown_account():
    r = client.post("/tools/account-status", json={"account_id": "OPT-99999999"})
    assert r.status_code == 404
    assert r.json()["error_code"] == "account_not_found"


def test_outage_check_active():
    r = client.post("/tools/outage-check", json={"zip_code": "11375"})
    assert r.status_code == 200
    body = r.json()
    assert body["outage_active"] is True
    assert body["incident_id"] == "INC-2026-0914-QNS"


def test_outage_check_unknown_zip_is_safe_default():
    r = client.post("/tools/outage-check", json={"zip_code": "99999"})
    assert r.status_code == 200
    assert r.json()["outage_active"] is False


# --- human-in-the-loop gate ----------------------------------------------

def test_schedule_requires_confirmation():
    slots = client.post("/tools/appointment-slots", json={"zip_code": "11101"}).json()
    slot = slots["slots"][0]
    r = client.post(
        "/tools/schedule-technician",
        json={
            "account_id": "OPT-10045512",
            "preferred_date": slot["date"],
            "window": slot["window"],
            "confirm": False,
        },
    )
    assert r.status_code == 409
    assert r.json()["error_code"] == "confirmation_required"


def test_schedule_succeeds_when_confirmed():
    slots = client.post("/tools/appointment-slots", json={"zip_code": "11101"}).json()
    slot = slots["slots"][0]
    r = client.post(
        "/tools/schedule-technician",
        json={
            "account_id": "OPT-10045512",
            "preferred_date": slot["date"],
            "window": slot["window"],
            "confirm": True,
        },
    )
    assert r.status_code == 200
    assert r.json()["confirmation_number"].startswith("APT-")


def test_schedule_rejects_invented_slot():
    r = client.post(
        "/tools/schedule-technician",
        json={
            "account_id": "OPT-10045512",
            "preferred_date": "2026-12-25",
            "window": "03:00-04:00",
            "confirm": True,
        },
    )
    assert r.status_code == 400
    assert r.json()["error_code"] == "slot_unavailable"


def test_escalation_routes_angry_to_tier_two():
    r = client.post(
        "/tools/escalate",
        json={
            "account_id": "OPT-30099001",
            "reason": "Third failed install visit",
            "sentiment": "angry",
            "confirm": True,
        },
    )
    assert r.status_code == 200
    assert r.json()["queue"] == "tier-2-voice"


# --- classic CX webhook contract -----------------------------------------

def test_webhook_lookup_account_returns_cx_shape():
    r = client.post(
        "/webhook",
        json={
            "fulfillmentInfo": {"tag": "lookup-account"},
            "sessionInfo": {"parameters": {"account_id": "OPT-30099001"}},
        },
    )
    assert r.status_code == 200
    body = r.json()
    text = body["fulfillmentResponse"]["messages"][0]["text"]["text"][0]
    assert "suspended" in text
    assert body["sessionInfo"]["parameters"]["account_valid"] is True


def test_webhook_unknown_tag_degrades_gracefully():
    r = client.post("/webhook", json={"fulfillmentInfo": {"tag": "nonsense"}})
    assert r.status_code == 200
    assert "fulfillmentResponse" in r.json()


# --- ops ------------------------------------------------------------------

def test_healthz():
    assert client.get("/healthz").json() == {"status": "ok"}


def test_stats_reports_percentiles():
    client.post("/tools/outage-check", json={"zip_code": "11101"})
    body = client.get("/stats").json()
    assert "/tools/outage-check" in body["routes"]
    assert "p95_ms" in body["routes"]["/tools/outage-check"]
