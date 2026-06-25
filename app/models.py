from typing import Optional
from pydantic import BaseModel


class TicketRequest(BaseModel):
    ticket_id: str
    channel: Optional[str] = None
    locale: Optional[str] = None
    message: str


class TicketResponse(BaseModel):
    ticket_id: str
    case_type: str
    severity: str
    department: str
    agent_summary: str
    human_review_required: bool
    confidence: float
