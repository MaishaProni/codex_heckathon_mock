"""Rules-based ticket classifier.

Design goals:
    * Deterministic, no LLM dependency, no secrets.
    * Order of precedence (highest first):
        phishing > payment_failed > wrong_transfer > refund_request > other.
    * Confidence is derived from the number of matched keywords per category.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .schemas import CaseType, Department, Severity


# ---------------------------------------------------------------------------
# Keyword groups (English + Bangla). Patterns are regex with IGNORECASE.
# ---------------------------------------------------------------------------


_PHISHING_PATTERNS: List[re.Pattern[str]] = [
    r"\botp\b",
    r"\bpin\b",
    r"\bpassword\b",
    r"\bcvv\b",
    r"card number",
    r"credit card",
    r"security code",
    r"verification code",
    r"share (?:your|the|my)?\s*(?:otp|pin|password|cvv|card)",
    r"send (?:your|the|my)?\s*(?:otp|pin|password|cvv|card)",
    r"give (?:your|the|my)?\s*(?:otp|pin|password|cvv|card)",
    r"tell (?:your|the|my)?\s*(?:otp|pin|password|cvv|card)",
    r"provide (?:your|the|my)?\s*(?:otp|pin|password|cvv|card)",
    r"asked for (?:my|the)?\s*(?:otp|pin|password|cvv)",
    r"asking for (?:my|the)?\s*(?:otp|pin|password|cvv)",
    r"calling (?:me|and)",
    r"smishing",
    r"phishing",
    r"scam",
    r"fraud(?:ster)?",
    r"fake (?:sms|call|message)",
    r"suspicious (?:call|sms|message|email|link)",
    r"hack(?:ed|er)?",
    r"\bসিকিউরিটি কোড\b",
    r"\bওটিপি\b",
    r"\bপিন\b",
    r"\bপাসওয়ার্ড\b",
]


_PAYMENT_FAILED_PATTERNS: List[re.Pattern[str]] = [
    r"payment (?:failed|didn'?t go through|not (?:completed|received))",
    r"transaction (?:failed|wasn'?t|was not) (?:completed|successful|received)",
    r"transaction (?:failed|didn'?t go through)",
    r"money (?:was|got|has been) (?:deducted|debited|charged)",
    r"balance (?:was|got|has been) (?:deducted|debited)",
    r"charged but (?:didn'?t|haven'?t|not) (?:receive|received)",
    r"paid but (?:didn'?t|haven'?t|not) (?:receive|received|get)",
    r"deducted but (?:didn'?t|haven'?t|not) (?:receive|received)",
    r"\bdeclined\b",
    r"\bunsuccessful\b",
    r"\bpending\b",
]


_WRONG_TRANSFER_PATTERNS: List[re.Pattern[str]] = [
    r"wrong (?:number|recipient|account|person)",
    r"sent (?:it )?to (?:the )?wrong",
    r"transferred (?:it )?to (?:the )?wrong",
    r"send (?:it )?to (?:the )?wrong",
    r"mistakenly sent",
    r"sent (?:money|cash|taka|bdt|amount) to (?:the )?wrong",
    r"transferred (?:money|cash|taka|bdt|amount) to (?:the )?wrong",
    r"sent (?:money|cash|taka|bdt|amount) by mistake",
    r"by mistake sent",
    r"\baccidentally sent\b",
    r"\bwrongly sent\b",
    r"\brecover(?:y)?\b",
    r"\bget (?:it|back) (?:my )?(?:money|amount|taka|bdt)\b",
    r"\bভুল (?:নম্বর|অ্যাকাউন্ট|ব্যক্তি)\b",
]


_REFUND_PATTERNS: List[re.Pattern[str]] = [
    r"\brefund\b",
    r"\bmoney back\b",
    r"\bget (?:my )?money back\b",
    r"\breimburse(?:ment)?\b",
    r"\bchargeback\b",
    r"return (?:my )?money",
    r"cancel (?:my )?(?:order|transaction|payment)",
    r"changed my mind",
    r"\bফেরত\b",
    r"\bটাকা ফেরত\b",
]


_CONTESTED_REFUND_TERMS: List[re.Pattern[str]] = [
    r"unauthori[sz]ed",
    r"\bstolen\b",
    r"charged without",
    r"didn'?t (?:make|do|authorize|approve)",
    r"i (?:did|didn'?t) not (?:make|authorize)",
    r"double (?:charged|debited|deducted)",
    r"\bduplicate\b",
]


_OTHER_FALLBACK_TERMS: List[re.Pattern[str]] = [
    r"app (?:crash(?:ed)?|not (?:working|opening))",
    r"can'?t (?:open|login|sign in|use) (?:the )?app",
    r"\bbug\b",
    r"\bglitch\b",
    r"slow (?:app|service)",
    r"\bapp (?:সমস্যা|কাজ করছে না)\b",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _count_matches(patterns: List[str], text: str) -> Tuple[int, List[str]]:
    """Return (match_count, matched_terms) for a list of regex patterns."""
    matched: List[str] = []
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.UNICODE)
        if m:
            matched.append(m.group(0).lower())
    return len(matched), matched


@dataclass
class Classification:
    case_type: CaseType
    severity: Severity
    department: Department
    confidence: float
    is_contested_refund: bool = False
    amount_hint: str = ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify(message: str, locale: str | None = None) -> Classification:
    """Classify a single ticket message."""
    if not message or not message.strip():
        # Defensive default — schema already requires non-empty, but be safe.
        return Classification(
            case_type=CaseType.other,
            severity=Severity.low,
            department=Department.customer_support,
            confidence=0.5,
        )

    text = message.strip()

    phishing_count, phishing_terms = _count_matches(_PHISHING_PATTERNS, text)
    payment_count, payment_terms = _count_matches(_PAYMENT_FAILED_PATTERNS, text)
    wrong_count, wrong_terms = _count_matches(_WRONG_TRANSFER_PATTERNS, text)
    refund_count, refund_terms = _count_matches(_REFUND_PATTERNS, text)
    contested_count, _ = _count_matches(_CONTESTED_REFUND_TERMS, text)
    other_count, _ = _count_matches(_OTHER_FALLBACK_TERMS, text)

    # --- Case type precedence (highest first) -----------------------------
    # Phishing trumps everything — even if a refund/transfer is mentioned, the
    # request is dominated by a social-engineering attempt.
    if phishing_count >= 1:
        case_type = CaseType.phishing_or_social_engineering
        confidence = _confidence(phishing_count, base=0.85)
        return Classification(
            case_type=case_type,
            severity=Severity.critical,
            department=Department.fraud_risk,
            confidence=confidence,
        )

    # Payment-failed outranks wrong-transfer because "balance deducted but no
    # transfer made" is a payment_ops concern, not a recovery one.
    if payment_count >= 1 and payment_count >= wrong_count:
        case_type = CaseType.payment_failed
        confidence = _confidence(payment_count, base=0.8)
        return Classification(
            case_type=case_type,
            severity=Severity.high,
            department=Department.payments_ops,
            confidence=confidence,
        )

    if wrong_count >= 1:
        case_type = CaseType.wrong_transfer
        confidence = _confidence(wrong_count, base=0.85)
        return Classification(
            case_type=case_type,
            severity=Severity.high,
            department=Department.dispute_resolution,
            confidence=confidence,
        )

    if refund_count >= 1:
        case_type = CaseType.refund_request
        is_contested = contested_count >= 1
        severity = Severity.medium if is_contested else Severity.low
        department = (
            Department.dispute_resolution if is_contested else Department.customer_support
        )
        confidence = _confidence(refund_count + contested_count, base=0.75)
        return Classification(
            case_type=case_type,
            severity=severity,
            department=department,
            confidence=confidence,
            is_contested_refund=is_contested,
        )

    # Fallback
    confidence = _confidence(other_count, base=0.6)
    return Classification(
        case_type=CaseType.other,
        severity=Severity.low,
        department=Department.customer_support,
        confidence=confidence,
    )


def human_review_required(case_type: CaseType, severity: Severity) -> bool:
    """Per section 3 of the spec: critical or phishing must be human-reviewed."""
    return severity == Severity.critical or case_type == CaseType.phishing_or_social_engineering


def _confidence(matches: int, base: float = 0.6) -> float:
    """Confidence rises with the number of matched signals and caps at 0.99."""
    return round(min(0.99, base + 0.05 * matches), 2)


def extract_amount_hint(message: str) -> str:
    """Pull the first numeric / taka / BDT amount hint, if any."""
    patterns = [
        r"\b(\d{1,9}(?:[,]\d{2,3})?)\s*(?:taka|bdt|tk|inr|rs|usd)?\b",
        r"\b(?:taka|bdt|tk|inr|rs|usd)\s*(\d{1,9}(?:[,]\d{2,3})?)\b",
    ]
    for pat in patterns:
        m = re.search(pat, message, re.IGNORECASE | re.UNICODE)
        if m:
            return m.group(0).strip()
    return ""


__all__: List[str] = [
    "Classification",
    "classify",
    "extract_amount_hint",
    "human_review_required",
]