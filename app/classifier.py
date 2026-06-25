from .models import TicketRequest, TicketResponse

# (pattern_list, case_type, severity, department, summary_template)
_RULES = [
    (
        ["otp", "o.t.p", "someone called", "verify account", "verify your account",
         "share your", "asking for your", "ওটিপি", "পিন", "পাসওয়ার্ড"],
        "phishing_or_social_engineering", "critical", "fraud_risk",
        "Customer reports a suspicious contact attempting to obtain account credentials.",
    ),
    (
        ["wrong number", "wrong account", "sent to wrong", "wrong recipient",
         "wrong person", "ভুল নম্বর", "ভুল অ্যাকাউন্ট"],
        "wrong_transfer", "high", "dispute_resolution",
        "Customer reports sending money to an unintended recipient and requests recovery.",
    ),
    (
        ["payment failed", "transaction failed", "balance deducted", "money deducted",
         "charge failed", "পেমেন্ট ব্যর্থ", "লেনদেন ব্যর্থ"],
        "payment_failed", "high", "payments_ops",
        "Customer reports a failed transaction where their balance may have been deducted.",
    ),
    (
        ["refund", "get it back", "get my money back", "return the money",
         "money back", "ফেরত", "রিফান্ড"],
        "refund_request", "low", "customer_support",
        "Customer is requesting a refund for a recent transaction.",
    ),
]

_CONTESTED_KEYWORDS = ["dispute", "contested", "not authorized", "unauthorized", "fraud", "scam"]


def classify(ticket: TicketRequest) -> TicketResponse:
    lower = ticket.message.lower()

    for patterns, case_type, severity, department, summary in _RULES:
        if any(p in lower for p in patterns):
            if case_type == "refund_request" and any(k in lower for k in _CONTESTED_KEYWORDS):
                severity = "medium"
                department = "dispute_resolution"
            human_review = case_type == "phishing_or_social_engineering" or severity == "critical"
            return TicketResponse(
                ticket_id=ticket.ticket_id,
                case_type=case_type,
                severity=severity,
                department=department,
                agent_summary=summary,
                human_review_required=human_review,
                confidence=0.72,
            )

    return TicketResponse(
        ticket_id=ticket.ticket_id,
        case_type="other",
        severity="low",
        department="customer_support",
        agent_summary="Customer has submitted a general inquiry or reported an unspecified issue.",
        human_review_required=False,
        confidence=0.60,
    )
