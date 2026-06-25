# QueueStorm Ticket Classifier

A FastAPI service that classifies bKash customer support tickets using keyword-based rules.

Built for the SUST CSE Carnival 2026 — Codex Community Hackathon Mock Preliminary Round.

---

## Overview

**POST /sort-ticket** accepts a customer message and returns:
- `case_type` — wrong_transfer, payment_failed, refund_request, phishing_or_social_engineering, or other
- `severity` — low, medium, high, or critical
- `department` — customer_support, dispute_resolution, payments_ops, or fraud_risk
- `agent_summary` — 1–2 neutral sentences for a support agent
- `human_review_required` — true for phishing or critical cases
- `confidence` — float 0–1

**LLM used:** No — pure keyword rule-based classification.

---

## Build & Run (Local)

### Prerequisites
- Python 3.11+

### Steps

```powershell
# 1. Clone the repo
git clone <your-repo-url>
cd codex_heckathon_mock

# 2. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the server
uvicorn app.main:app --reload
```

Server runs at `http://localhost:8000`

---

## Testing

### Option A — Browser (easiest)

Open `http://localhost:8000/docs` in your browser.  
Click **POST /sort-ticket** → **Try it out** → paste a body → **Execute**.

### Option B — PowerShell (Windows)

> Use `Invoke-RestMethod`, not `curl` — PowerShell's built-in `curl` alias does not handle JSON correctly.

**Health check:**
```powershell
Invoke-RestMethod http://localhost:8000/health
```

**All 5 sample cases:**
```powershell
# 1. Wrong transfer → expect: wrong_transfer, high
Invoke-RestMethod -Method Post -Uri http://localhost:8000/sort-ticket -ContentType "application/json" -Body '{"ticket_id":"T-001","message":"I sent 3000 to wrong number"}'

# 2. Payment failed → expect: payment_failed, high
Invoke-RestMethod -Method Post -Uri http://localhost:8000/sort-ticket -ContentType "application/json" -Body '{"ticket_id":"T-002","message":"Payment failed but balance deducted"}'

# 3. Phishing → expect: phishing_or_social_engineering, critical, human_review_required: True
Invoke-RestMethod -Method Post -Uri http://localhost:8000/sort-ticket -ContentType "application/json" -Body '{"ticket_id":"T-003","message":"Someone called asking my OTP, is that bKash?"}'

# 4. Refund → expect: refund_request, low
Invoke-RestMethod -Method Post -Uri http://localhost:8000/sort-ticket -ContentType "application/json" -Body '{"ticket_id":"T-004","message":"Please refund my last transaction, I changed my mind"}'

# 5. Other → expect: other, low
Invoke-RestMethod -Method Post -Uri http://localhost:8000/sort-ticket -ContentType "application/json" -Body '{"ticket_id":"T-005","message":"App crashed when I opened it"}'
```

### Option C — bash / Linux / macOS

```bash
curl -s -X POST http://localhost:8000/sort-ticket \
  -H "Content-Type: application/json" \
  -d '{"ticket_id":"T-001","message":"I sent 3000 to wrong number"}'
```

### Expected Results

| # | case_type | severity | human_review_required |
|---|---|---|---|
| T-001 | wrong_transfer | high | false |
| T-002 | payment_failed | high | false |
| T-003 | phishing_or_social_engineering | critical | **true** |
| T-004 | refund_request | low | false |
| T-005 | other | low | false |

---

## Render Deployment

1. Push this repo to a public GitHub repository
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Render auto-detects `render.yaml` — build and start commands are pre-configured
5. Click **Deploy** — Render provides a free HTTPS URL automatically

No environment variables required.

---

## Project Structure

```
codex_heckathon_mock/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app + routes
│   ├── models.py        # Pydantic request/response schemas
│   └── classifier.py    # Keyword rule-based classification
├── requirements.txt
├── .gitignore
├── render.yaml
├── PLAN.md
└── README.md
```
