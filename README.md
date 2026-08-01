# 📧 Email Harness QA Agent

An AI-powered web application that reviews your emails **before you hit send**. Paste an email, get a professional QA report with actionable fixes — combining deterministic rule checks with DeepSeek AI semantic analysis.

![Status](https://img.shields.io/badge/status-ready%20to%20send-brightgreen)

---

## ✨ Features

- **🔍 Hybrid Validation** — Fast deterministic rules for structure + AI for tone, clarity, and professionalism
- **📊 Professional QA Report** — Overall status, validation summary, per-issue breakdown with "why it matters" and recommendations
- **🛡️ False-Positive Prevention** — Defense-in-depth filtering for Harness CI/CD template expressions and signature formatting nitpicks
- **📋 6 Sample Emails** — Cycle through 5 problematic emails + 1 perfect email to see the full capability
- **⚡ Fast & Lightweight** — Single-page vanilla JS frontend, Flask backend, no database
- **🔧 Mock Mode** — Fully functional without an API key (heuristic checks)

---

## 🎯 How It Works

```
Paste Email → Parse → Rule Engine (4 validators) → DeepSeek AI → Filter → QA Report
```

| Step | Component | What It Does |
|---|---|---|
| 1 | **Email Parser** | Extracts sender, recipients, subject, greeting, body, closing, signature |
| 2 | **Rule Engine** | 4 deterministic validators: Subject, Recipient, Greeting, Duplicate Content |
| 3 | **DeepSeek AI** | Semantic review: grammar, spelling, clarity, tone, professionalism, CTA |
| 4 | **False-Positive Filter** | Removes noise (Harness template expressions, signature nitpicks) |
| 5 | **QA Report** | Overall status, summary, issues with fixes, final recommendation |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- A DeepSeek API key (optional — works without it)

### Setup

```bash
# Clone the repo
git clone https://github.com/bot041/Email-Harness-QA-Agent.git
cd Email-Harness-QA-Agent

# Create virtual environment
python -m venv .venv
source .venv/Scripts/activate  # Windows
# source .venv/bin/activate    # Mac/Linux

# Install dependencies
pip install flask==3.1.0 requests==2.32.3 python-dotenv==1.1.0

# Configure (optional — app works without this)
cp .env.example .env
# Edit .env with your DeepSeek API key

# Run
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

---

## 📊 Report Statuses

| Status | Meaning |
|---|---|
| ✅ **Ready to Send** | Zero issues — good to go |
| ⚠️ **Needs Review** | Issues found — review and fix before sending |
| ❌ **Not Ready to Send** | Critical issues (missing subject, no recipient, empty body) |

---

## 🏗️ Project Structure

```
├── app.py                      # Entry point
├── app/
│   ├── agents/
│   │   └── email_harness.py    # ★ Central orchestrator
│   ├── validators/
│   │   ├── models.py           # Issue, ValidationResult, QAReport
│   │   └── rule_engine.py      # 4 deterministic validators
│   ├── services/
│   │   └── deepseek_service.py # DeepSeek API + mock fallback
│   ├── utils/
│   │   └── email_parser.py     # Regex-based email parser
│   ├── routes/
│   │   └── main.py             # Flask routes
│   ├── templates/
│   │   └── index.html          # Single-page UI
│   └── static/
│       ├── css/style.css       # Styles
│       └── js/app.js           # Frontend logic
├── .env.example                # Environment template
├── Requirements_spec.txt       # Full project specification
└── Documentation.txt           # Complete technical documentation
```

---

## 🔑 API Endpoints

| Method | Route | Description |
|---|---|---|
| `GET` | `/` | Web interface |
| `POST` | `/review` | Review an email → QA report |
| `GET` | `/health` | Health check + API status |

---

## 🛡️ Guardrails

The system prevents false positives at multiple layers:

- **Prompt Layer** — DeepSeek is instructed to ignore Harness template expressions (`<+pipeline.*>`) and minor signature formatting
- **Filter Layer** — Post-processing removes any remaining false positives about template expressions
- **Assessment Layer** — If all AI issues were false positives, status auto-corrects to prevent contradictory reports

---

## 📝 Design Decisions

| Decision | Rationale |
|---|---|
| **Single Agent** over multi-agent | Simpler, faster, no orchestration overhead |
| **Rules + AI** over AI-only | Rules are instant & reliable for structure; AI handles semantics |
| **Vanilla JS** over React | Single-page, single-flow — no framework needed |
| **Regex Parser** over ML parser | Email headers are predictable patterns |
| **DeepSeek** over GPT-4 | 10-20x cheaper, comparable quality, OpenAI-compatible API |
| **No database** | Each review is independent — no storage needed |

---

## 📄 Documentation

- **[Requirements_spec.txt](Requirements_spec.txt)** — Full requirements & dependencies
- **[Documentation.txt](Documentation.txt)** — Complete technical documentation with deep dives into every component

---

## 🔮 Future Enhancements

- Gmail & Outlook API integration
- Attachment validation
- Link checking
- PII detection
- Custom company policy rules
- PDF report export
- Dark mode

---
