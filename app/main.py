"""FastAPI entrypoint for the QueueStorm Warmup classifier service."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__
from .classifier import classify, human_review_required
from .safety import build_summary, message_requests_credentials
from .schemas import (
    HealthResponse,
    SortTicketRequest,
    SortTicketResponse,
)

logger = logging.getLogger("queue_classifier")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s :: %(message)s")


app = FastAPI(
    title="QueueStorm Warmup Classifier",
    version=__version__,
    description="Reads a single CRM ticket message and returns a structured classification.",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logger(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.info(
        "%s %s -> %s in %.1fms",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["meta"])
async def health() -> HealthResponse:
    """Liveness probe — must respond within 10s."""
    return HealthResponse(status="ok", service="queue-classifier", version=__version__)


@app.post("/sort-ticket", response_model=SortTicketResponse, tags=["classify"])
async def sort_ticket(payload: SortTicketRequest) -> SortTicketResponse:
    """Classify a single ticket. Returns structured JSON (max 30s)."""
    message = payload.message.strip()

    classification = classify(message=message, locale=payload.locale)

    # Build the agent summary from a fixed template — never from user text.
    summary = build_summary(classification, message=message)

    needs_review = human_review_required(classification.case_type, classification.severity)

    # Extra caution: if the customer's *message itself* is asking us for
    # credentials, that is a phishing attempt and must be human-reviewed even
    # if the keyword scorer missed it.
    if message_requests_credentials(message):
        needs_review = True

    return SortTicketResponse(
        ticket_id=payload.ticket_id,
        case_type=classification.case_type,
        severity=classification.severity,
        department=classification.department,
        agent_summary=summary,
        human_review_required=needs_review,
        confidence=classification.confidence,
    )


# ---------------------------------------------------------------------------
# Error handlers — keep responses JSON-shaped.
# ---------------------------------------------------------------------------


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "request_id": str(uuid.uuid4()),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception while processing %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "detail": str(exc),
            "request_id": str(uuid.uuid4()),
        },
    )


def _dev_info() -> Dict[str, Any]:
    """Helper for the local CLI smoke test."""
    return {"service": "queue-classifier", "version": __version__}


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
