from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .classifier import classify
from .models import TicketRequest, TicketResponse

app = FastAPI(title="QueueStorm Ticket Classifier")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "ticket-classifier"}


@app.post("/sort-ticket", response_model=TicketResponse)
def sort_ticket(ticket: TicketRequest):
    if not ticket.message or not ticket.message.strip():
        raise HTTPException(status_code=422, detail="message field is required and cannot be empty")
    return classify(ticket)
