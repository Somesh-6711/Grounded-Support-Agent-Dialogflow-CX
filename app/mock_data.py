"""Synthetic data for the CES demo agent.

None of this is real. Account IDs, balances, outages and slots are invented so
the agent has something deterministic to call. Swap this module for a real
repository layer and nothing else in the service changes.
"""

from datetime import date, timedelta

ACCOUNTS = {
    "OPT-10045512": {
        "account_id": "OPT-10045512",
        "plan": "1 Gig Internet + Mobile",
        "service_status": "active",
        "balance_due_usd": 89.99,
        "due_date": "2026-09-28",
        "autopay_enabled": False,
        "service_zip": "11101",
        "open_tickets": 0,
    },
    "OPT-20031877": {
        "account_id": "OPT-20031877",
        "plan": "500 Mbps Internet",
        "service_status": "degraded",
        "balance_due_usd": 0.00,
        "due_date": None,
        "autopay_enabled": True,
        "service_zip": "11375",
        "open_tickets": 1,
    },
    "OPT-30099001": {
        "account_id": "OPT-30099001",
        "plan": "Internet + TV Core",
        "service_status": "suspended_nonpayment",
        "balance_due_usd": 214.50,
        "due_date": "2026-08-15",
        "autopay_enabled": False,
        "service_zip": "07030",
        "open_tickets": 2,
    },
}

OUTAGES = {
    "11375": {
        "outage_active": True,
        "incident_id": "INC-2026-0914-QNS",
        "services_affected": ["internet", "tv"],
        "estimated_restore": "2026-09-14T18:00:00Z",
        "cause": "fiber cut during municipal roadwork",
    },
    "11101": {
        "outage_active": False,
        "incident_id": None,
        "services_affected": [],
        "estimated_restore": None,
        "cause": None,
    },
    "07030": {
        "outage_active": False,
        "incident_id": None,
        "services_affected": [],
        "estimated_restore": None,
        "cause": None,
    },
}


def available_slots(days_ahead: int = 5) -> list[dict]:
    """Deterministic fake technician availability starting tomorrow."""
    today = date(2026, 9, 12)
    slots = []
    for offset in range(1, days_ahead + 1):
        day = today + timedelta(days=offset)
        if day.weekday() == 6:  # no Sunday dispatch
            continue
        slots.append({"date": day.isoformat(), "window": "08:00-12:00"})
        slots.append({"date": day.isoformat(), "window": "13:00-17:00"})
    return slots


# In-memory side effects, reset on every cold start. Enough to prove the
# write path works and that it is gated behind an explicit confirmation.
BOOKED_APPOINTMENTS: list[dict] = []
ESCALATIONS: list[dict] = []
