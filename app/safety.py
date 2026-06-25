"""Safe agent-summary builder.

Section 5 of the task PDF explicitly fails any response whose ``agent_summary``
asks the customer for a PIN, OTP, password, or full card number. To eliminate
that risk, every summary here is composed from a *fixed template* — no
substrings of the customer's free-text message are interpolated into the
output.
"""

from __future__ import annotations

import re

from .classifier import Classification
from .schemas import CaseType


# ---------------------------------------------------------------------------
# Fixed templates (never read from the customer message)
# ---------------------------------------------------------------------------


_SUMMARY_TEMPLATES: dict[CaseType, str] = {
    CaseType.wrong_transfer: (
        "Customer reports sending money to an unintended recipient and requests recovery."
    ),
    CaseType.payment_failed: (
        "Customer reports a payment that failed while the account balance appears to have been deducted."
    ),
    CaseType.refund_request: (
        "Customer requests a refund for a recent transaction."
    ),
    CaseType.phishing_or_social_engineering: (
        "Customer reports a suspicious interaction requesting sensitive credentials; flagged for fraud review."
    ),
    CaseType.other: (
        "Customer reports a general service issue that does not match a known dispute category."
    ),
}


_FALLBACK_SUMMARY = (
    "Customer inquiry requires review by a human agent."
)


# ---------------------------------------------------------------------------
# Defence-in-depth: regex blocklist that must NEVER appear in a summary.
# ---------------------------------------------------------------------------


_UNSAFE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"share\s+(?:your|the|my)?\s*(?:otp|pin|password|cvv|card)", re.IGNORECASE),
    re.compile(r"send\s+(?:your|the|my)?\s*(?:otp|pin|password|cvv|card)", re.IGNORECASE),
    re.compile(r"give\s+(?:your|the|my)?\s*(?:otp|pin|password|cvv|card)", re.IGNORECASE),
    re.compile(r"tell\s+(?:your|the|my)?\s*(?:otp|pin|password|cvv|card)", re.IGNORECASE),
    re.compile(r"provide\s+(?:your|the|my)?\s*(?:otp|pin|password|cvv|card)", re.IGNORECASE),
    re.compile(r"(?:otp|pin|password|cvv)\s+(?:number|code|kya|koto)", re.IGNORECASE),
    re.compile(r"পিন\s*(?:নম্বর|দিন|জানান)", re.IGNORECASE),
    re.compile(r"ওটিপি\s*(?:নম্বর|দিন|জানান)", re.IGNORECASE),
]


def build_summary(classification: Classification, message: str = "") -> str:
    """Return a fixed, safe summary for the given classification.

    The optional ``message`` argument is accepted only to keep callers simple —
    it is *never* interpolated into the output.
    """
    base = _SUMMARY_TEMPLATES.get(classification.case_type, _FALLBACK_SUMMARY)

    if classification.is_contested_refund and classification.case_type == CaseType.refund_request:
        base = (
            "Customer disputes a recent transaction and requests investigation and refund."
        )

    # Defence-in-depth: even though templates are fixed, scan the output.
    if _contains_unsafe(base):
        return _FALLBACK_SUMMARY

    return base


def _contains_unsafe(text: str) -> bool:
    return any(p.search(text) for p in _UNSAFE_PATTERNS)


__all__ = ["build_summary"]


def message_requests_credentials(message: str) -> bool:
    """Detect if the *customer message itself* is asking the agent for
    credentials — used to flag the ticket for human review.

    This is informational; it never affects the agent_summary content.
    """
    if not message:
        return False
    patterns = [
        r"(?:send|share|give|tell|provide)\s+(?:me\s+)?(?:your|the)?\s*(?:otp|pin|password|cvv|card)",
        r"(?:ওটিপি|পিন|পাসওয়ার্ড)\s*(?:দিন|পাঠান|জানান)",
    ]
    return any(re.search(p, message, re.IGNORECASE | re.UNICODE) for p in patterns)
