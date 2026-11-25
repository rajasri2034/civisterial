# Civisterial

**Plain-language government document explainer with verbatim quotation verification, automated in-memory PII redaction, and multilingual guidance.**

[![Live Web App](https://img.shields.io/badge/Live_App-civisterial.vercel.app-0F766E?style=for-the-badge)](https://civisterial.vercel.app)
[![Live API](https://img.shields.io/badge/API_Docs-civisterial--api.onrender.com-1E3A8A?style=for-the-badge)](https://civisterial-api.onrender.com/docs)
[![Accessibility Score](https://img.shields.io/badge/Lighthouse_Accessibility-100%2F100-15803D?style=for-the-badge)](https://civisterial.vercel.app)

> **Disclaimer:** Civisterial provides plain-language administrative guidance only — not legal, financial, or official government advice. Always verify dates, fees, and obligations against the quoted passages from your original document.

---

## Live Deployment

| Service | Platform | URL |
| :--- | :--- | :--- |
| **Frontend Web Application** | Vercel | https://civisterial.vercel.app |
| **Backend REST API** | Render | https://civisterial-api.onrender.com |
| **Interactive API Docs (Swagger)** | Render | https://civisterial-api.onrender.com/docs |
| **Health Check Endpoint** | Render | https://civisterial-api.onrender.com/api/health |

*(Note: The Render backend runs on a free instance and may take ~30 seconds to wake up on the very first request after 15 minutes of inactivity.)*

---

## Overview

Official letters, tax notices, municipal forms, and benefit decisions are often written in dense legal or bureaucratic terminology. Misreading a single line can lead to missed deadlines, unpaid fees, or rejected applications.

**Civisterial** bridges that gap while preventing AI hallucinations:
1. **Plain-Language Breakdown:** Converts complex notices into a structured **Overview**, **Simplified Text**, **Action Plan**, **Deadlines & Requirements**, and **Evidence** view.
2. **Verbatim Quotation Verification:** Every extracted deadline, fee, and requirement is paired with an exact quote from the source document and verified against the original text (`Exact quotation found` / `NO_DEADLINE`).
3. **Privacy-First Zero-Retention Architecture:** Documents are processed strictly in volatile memory—never written to disk, databases, or browser storage—with deterministic PII redaction before AI inference.
4. **Independent Multilingual Input & Output:** Automatically detects the document's language (or accepts manual BCP-47 selection) and generates explanations in the user's preferred language (including English `en`, Tamil `ta`, Hindi `hi`, and other Gemini-supported languages).

---

## Key Features

### Privacy & Security Controls
- **Stateless Client Browser Policy:** Uses zero `localStorage`, zero `sessionStorage`, zero `document.cookie`, and zero third-party analytics or tracking scripts.
- **Automated In-Memory Text Redaction:** Masks emails, phone numbers, national IDs, passport/license identifiers, bank/IBAN numbers, and street addresses in PDF text layers (`[REDACTED_EMAIL]`, `[REDACTED_ID]`, etc.) before sending text to Gemini.
- **Explicit Image Consent Gate:** Detects image-only PDF pages and PNG/JPEG uploads via `/api/inspect` and requires explicit user confirmation (`consent_unredacted_images=true`) before transmitting unredacted page images.
- **Hardened HTTP Security Headers:** Enforces strict `Content-Security-Policy`, `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff`, and `Permissions-Policy` rules.

### Document Analysis & Accessibility
- **Multi-Format Upload:** Supports **PDF**, **PNG**, and **JPEG** documents up to **10 MB**, validated via magic-byte headers.
- **5-Tab Structured Results:**
  - **Overview:** High-level purpose of the notice, issuing authority, and summary status.
  - **Simplified text:** Clause-by-clause plain-language translation alongside original wording.
  - **Action plan:** Step-by-step checklist of required actions.
  - **Deadlines and requirements:** Explicit deadline detection (`NO_DEADLINE` when none exists), fee tables, and mandatory requirements with verbatim quote verification.
  - **Evidence:** Complete audit trail of source quotations and redaction counts.
- **Client-Side Export:** Download a `.txt` summary or print a formatted A4 reference sheet directly from browser memory.
- **WCAG-Aligned Accessibility:** Verified at **100/100** on Lighthouse Accessibility and **100/100** on Lighthouse Best Practices, with full keyboard `Tab` navigation and clear contrast.

---

## System Architecture

```text
┌──────────────────────────────────────────────────────────────────────┐
│                     Frontend (React + Vite on Vercel)                │
│  • Stateless UI (no localStorage / sessionStorage / cookies)         │
│  • Independent Document & Explanation Language Selectors             │
│  • Two-step flow: /api/inspect (redaction preview) → /api/analyze    │
│  • Local .txt export & A4 print view                                 │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │ HTTPS + Strict CORS & CSP
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                   Backend (FastAPI + Python on Render)               │
│  • Magic-byte file validation (PDF / PNG / JPEG, max 10 MB)          │
│  • In-memory BytesIO parsing & deterministic regex PII redaction     │
│  • Image-page detection & explicit consent enforcement               │
│  • Verbatim quote grounding & NO_DEADLINE verification               │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │ Redacted Text / Consented Images
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       Google Gemini API                              │
│  • Production: gemini-3.5-flash (via GEMINI_MODEL env var)           │
│  • Code fallback default: gemini-2.5-flash                           │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```text
civisterial/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS middleware, API routes
│   │   ├── config.py            # Environment & model configuration
│   │   ├── redaction.py         # Deterministic in-memory PII masking
│   │   ├── inspector.py         # Magic-byte & PDF page inspection
│   │   └── analyzer.py          # Gemini structured extraction & quote check
│   ├── tests/                   # Backend pytest & security test suite
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # LanguageSelector, redaction & result views
│   │   ├── config/
│   │   │   └── api.js           # Production API base URL & friendly errors
│   │   ├── pages/               # Landing, UploadPage, and Results views
│   │   └── styles/
│   │       └── global.css       # High-contrast accessible typography & layout
│   ├── index.html               # Strict CSP meta policy & IBM Plex fonts
│   ├── vercel.json              # Vercel SPA rewrites & security headers
│   └── package.json
├── eval/
│   └── fixtures/                # Sample test notices (including 05_no_deadline.pdf)
├── DATA_HANDLING.md             # Zero-retention lifecycle & model documentation
└── render.yaml                  # Render web service deployment blueprint
```

---

## API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Returns backend service status and readiness. |
| `GET` | `/api/languages` | Returns supported BCP-47 document and explanation languages. |
| `POST` | `/api/inspect` | Inspects an uploaded file in memory for page count, text vs. image pages, and PII redaction preview. |
| `POST` | `/api/analyze` | Redacts PII in memory, queries Gemini, and returns plain-language explanations with verified verbatim quotes. |

---

## Local Development Setup

### Prerequisites
- **Python 3.11+**
- **Node.js 20+** and **npm**
- A **Google AI Studio API Key** (`GEMINI_API_KEY`)

### 1. Start the FastAPI Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:GEMINI_API_KEY="your_google_ai_studio_api_key"
$env:FRONTEND_ORIGIN="http://localhost:5173"
$env:MOCK_MODE="false"

uvicorn app.main:app --reload --port 8000
```

### 2. Start the React + Vite Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser. In local development, Vite connects directly to `http://localhost:8000`.

---

## Running Tests & Evaluation

### Backend Tests
```powershell
cd backend
pytest
```

### Frontend Production Build Verification
```powershell
cd frontend
npm run build
```

### Sample Evaluation Fixture
To verify explicit deadline-absence detection and verbatim fee quoting end-to-end, upload `eval/fixtures/05_no_deadline.pdf` in the web interface and confirm:
- **Deadlines:** `NO_DEADLINE`
- **Fees:** Refundable security deposit (`Rs. 300`) matched with `✓ Exact quotation found`

---

## Documentation & Privacy Policy

Full technical details on in-memory processing, PII redaction patterns, logging exclusions, and model configuration (`gemini-3.5-flash` in production / `gemini-2.5-flash` fallback default) are documented in [`DATA_HANDLING.md`](./DATA_HANDLING.md).