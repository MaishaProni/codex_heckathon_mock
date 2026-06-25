"""Test the public sample cases from section 7 of the task PDF, plus edge cases."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


# ---------------------------------------------------------------------------
# Section 7 — Public sample cases
# ---------------------------------------------------------------------------


SAMPLES = [
    {
        "id": "T-001",
        "message": "I sent 3000 to wrong number",
        "case_type": "wrong_transfer",
        "severity": "high",
    },
    {
        "id": "T-002",
        "message": "Payment failed but balance deducted",
        "case_type": "payment_failed",
        "severity": "high",
    },
    {
        "id": "T-003",
        "message": "Someone called asking my OTP, is that bKash?",
        "case_type": "phishing_or_social_engineering",
        "severity": "critical",
    },
    {
        "id": "T-004",
        "message": "Please refund my last transaction, I changed my mind",
        "case_type": "refund_request",
        "severity": "low",
    },
    {
        "id": "T-005",
        "message": "App crashed when I opened it",
        "case_type": "other",
        "severity": "low",
    },
]


@pytest.mark.parametrize("sample", SAMPLES, ids=[s["id"] for s in SAMPLES])
def test_public_sample_case(sample):
    resp = client.post(
        "/sort-ticket",
        json={
            "ticket_id": sample["id"],
            "channel": "app",
            "locale": "en",
            "message": sample["message"],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ticket_id"] == sample["id"]
    assert body["case_type"] == sample["case_type"], body
    assert body["severity"] == sample["severity"], body
    assert 0.0 <= float(body["confidence"]) <= 1.0
    assert isinstance(body["agent_summary"], str) and body["agent_summary"].strip()


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "queue-classifier"
    assert "version" in body


# ---------------------------------------------------------------------------
# Section 5 — Safety rule: summaries must NEVER ask for credentials.
# ---------------------------------------------------------------------------


_UNSAFE_TRIGGERS = [
    "share your otp",
    "send me your pin",
    "give me the password",
    "tell me your cvv",
    "provide your card number",
]


@pytest.mark.parametrize("trigger", _UNSAFE_TRIGGERS)
def test_summary_never_asks_for_credentials(trigger):
    # We feed the *trigger* as the customer message (e.g. attacker text);
    # the agent_summary we return must NOT echo or include that text.
    resp = client.post(
        "/sort-ticket",
        json={
            "ticket_id": "T-safety",
            "channel": "app",
            "locale": "en",
            "message": f"Hey support, can you {trigger} so I can verify?",
        },
    )
    assert resp.status_code == 200, resp.text
    summary = resp.json()["agent_summary"].lower()
    for forbidden in ("otp", "pin", "password", "cvv", "card number"):
        # We allow the *word* "credentials" in the phishing template, but we
        # never ask the customer to share/send/provide it.
        assert "share your " + forbidden not in summary
        assert "send your " + forbidden not in summary
        assert "give your " + forbidden not in summary
        assert "tell your " + forbidden not in summary
        assert "provide your " + forbidden not in summary


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


def test_missing_ticket_id_is_rejected():
    resp = client.post(
        "/sort-ticket",
        json={"message": "Wrong transfer to 01711"},
    )
    assert resp.status_code == 422


def test_missing_message_is_rejected():
    resp = client.post(
        "/sort-ticket",
        json={"ticket_id": "T-006"},
    )
    assert resp.status_code == 422


def test_invalid_channel_is_rejected():
    resp = client.post(
        "/sort-ticket",
        json={"ticket_id": "T-007", "channel": "telegram", "message": "Refund please"},
    )
    assert resp.status_code == 422


def test_invalid_case_type_in_response_is_impossible():
    # Sanity: the response should always be one of the documented enums.
    valid = {
        "wrong_transfer",
        "payment_failed",
        "refund_request",
        "phishing_or_social_engineering",
        "other",
    }
    for sample in SAMPLES:
        resp = client.post(
            "/sort-ticket",
            json={"ticket_id": sample["id"], "message": sample["message"]},
        )
        assert resp.status_code == 200
        assert resp.json()["case_type"] in valid


# ---------------------------------------------------------------------------
# Routing — phishing must always go to fraud_risk
# ---------------------------------------------------------------------------


def test_phishing_routes_to_fraud_risk():
    resp = client.post(
        "/sort-ticket",
        json={
            "ticket_id": "T-phish",
            "message": "Urgent: send your OTP now or your account will be blocked.",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["case_type"] == "phishing_or_social_engineering"
    assert body["department"] == "fraud_risk"
    assert body["severity"] == "critical"
    assert body["human_review_required"] is True


def test_contested_refund_routes_to_dispute_resolution():
    resp = client.post(
        "/sort-ticket",
        json={
            "ticket_id": "T-refund",
            "message": "Please refund this transaction, I didn't make this payment, it was unauthorised.",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["case_type"] == "refund_request"
    assert body["department"] == "dispute_resolution"
    assert body["severity"] in {"medium", "high"}
