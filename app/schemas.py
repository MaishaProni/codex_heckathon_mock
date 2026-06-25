"""Pydantic schemas mirroring the official Request / Response contracts."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enums — must match the values listed in the task PDF (sections 3 & 4)
# ---------------------------------------------------------------------------


class Channel(str, Enum):
    app = "app"
    sms = "sms"
    call_center = "call_center"
    merchant_portal = "merchant_portal"


class Locale(str, Enum):
    bn = "bn"
    en = "en"
    mixed = "mixed"


class CaseType(str, Enum):
    wrong_transfer = "wrong_transfer"
    payment_failed = "payment_failed"
    refund_request = "refund_request"
    phishing_or_social_engineering = "phishing_or_social_engineering"
    other = "other"


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Department(str, Enum):
    customer_support = "customer_support"
    dispute_resolution = "dispute_resolution"
    payments_ops = "payments_ops"
    fraud_risk = "fraud_risk"


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------


class SortTicketRequest(BaseModel):
    """Inbound CRM ticket payload."""

    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    ticket_id: str = Field(..., min_length=1, description="Echoed back in the response")
    channel: Optional[Channel] = Field(
        default=None, description="app | sms | call_center | merchant_portal"
    )
    locale: Optional[Locale] = Field(default=None, description="bn | en | mixed")
    message: str = Field(..., min_length=1, description="Free-text customer complaint")


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


class SortTicketResponse(BaseModel):
    """Outbound classification payload."""

    model_config = ConfigDict(use_enum_values=True)

    ticket_id: str
    case_type: CaseType
    severity: Severity
    department: Department
    agent_summary: str
    human_review_required: bool
    confidence: float = Field(..., ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str