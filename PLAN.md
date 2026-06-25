# QueueStorm Warmup: Ticket Classifier Service Plan

## Context

This is for the SUST CSE Carnival 2026 / Codex Community Hackathon Mock Preliminary Round.
The task is to build a small HTTP service that classifies bKash customer support tickets into
case type, severity, department, and produces a one-line agent summary — using Claude AI for
classification, deployed publicly over HTTPS within the 1-hour window.

---

## Tech Stack

| Concern | Choice | Reason |
|---|---|---|
| Language | Python 3.11 | Fastest to build + best Claude SDK support |
| Framework | FastAPI | Auto docs, Pydantic validation, async-ready |
| Classifier | Claude Haiku 4.5 via `anthropic` SDK | Accurate, fast (<5s), handles Bengali/mixed locale natively |
| Fallback | Keyword rules | In case API key missing or LLM errors |
| Deployment | Render (free tier) | Auto-HTTPS, GitHub deploy, env vars UI |

---

## Project Structure

```
codex_heckathon_mock/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app + route handlers
│   ├── models.py        # Pydantic request + response schemas
│   ├── classifier.py    # LLM classification + keyword fallback
│   └── prompts.py       # System prompt constant
├── requirements.txt
├── .env.example         # Shows ANTHROPIC_API_KEY=your_key_here (no real secret)
├── .gitignore           # .env, __pycache__, .venv
├── render.yaml          # Render deployment config
└── README.md            # Runbook with local + Render deploy steps
```

---

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Returns `{"status": "ok", "service": "ticket-classifier"}` |
| POST | `/sort-ticket` | Accepts ticket JSON, returns classification JSON |

---

## Classification Logic

### LLM Path (primary)
Call Claude Haiku 4.5 with a structured system prompt. Returns raw JSON with all required fields.

### Rule-based Fallback (if LLM fails/unavailable)

| Keywords | case_type | severity | department |
|---|---|---|---|
| otp, pin, password, someone called, verify account, ওটিপি, পিন | phishing_or_social_engineering | critical | fraud_risk |
| wrong number, wrong account, sent to wrong, ভুল নম্বর | wrong_transfer | high | dispute_resolution |
| payment failed, transaction failed, balance deducted, পেমেন্ট ব্যর্থ | payment_failed | high | payments_ops |
| refund, get it back, return, ফেরত | refund_request | low | customer_support |
| (none match) | other | low | customer_support |

### human_review_required
`true` when `case_type == "phishing_or_social_engineering"` OR `severity == "critical"`

---

## Safety Rule
`agent_summary` must **never** contain: PIN, OTP, password, full card number.
Enforced in both the LLM system prompt and the rule-based fallback templates.

---

## Deployment (Render)
1. Push repo to GitHub (public)
2. New Web Service → connect repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add env var `ANTHROPIC_API_KEY` in Render dashboard (never in repo)

---

## Verification Checklist
- [ ] `GET /health` returns 200 within 10s
- [ ] `POST /sort-ticket` returns correct `case_type` for all 5 sample cases
- [ ] `human_review_required: true` for phishing + critical cases
- [ ] `agent_summary` never contains PIN/OTP/password
- [ ] Works with `locale: "bn"` (Bengali input)
- [ ] Fallback fires when `ANTHROPIC_API_KEY` is unset
- [ ] Live HTTPS URL responds correctly
