# Privacy & Third-Party Data Handling (`PRIVACY.md`)

**Date Checked:** November 25, 2026

## 1. Exact Gemini API Service, Model, and Account Configuration

- **API Service:** Google Gemini Developer API (`generativelanguage.googleapis.com` via the official `google-genai` Python SDK)
- **Primary Model Configured:** `gemini-3.5-flash` (with automatic failover to `gemini-3.1-flash-lite` / `gemini-3.8-flash`)
- **Account / Billing Tier Configuration:** Google AI Studio / Gemini Developer API key configured via server-side environment variable (`GEMINI_API_KEY`).
  - **Free Tier (`Unpaid Services`):** Used when the API key belongs to a Google Cloud project without an active linked billing account.
  - **Paid Tier (`Paid Services`, Usage Tiers 1–3):** Applies only when the API key belongs to a Google Cloud project with an active linked billing account (or when requests originate from the EEA, Switzerland, or the UK, where Google applies Paid Services data-use rules).

> **Important Free-Tier Rule:** When Civisterial is running on a **Free Tier** Gemini API key, **only public or synthetic documents may be uploaded**. Do not upload personal, confidential, financial, medical, or non-public documents on a Free Tier deployment.

---

## 2. Plain-Language Summary of Google Gemini API Data Handling Terms

Based on the **Gemini API Additional Terms of Service** and **Gemini API Abuse Monitoring Guidelines** reviewed on **November 25, 2026**:

1. **How Google Uses Your Data (Free Tier vs. Paid Tier):**
   - **On the Free Tier (Unpaid Quota):** Google may retain submitted prompts, uploaded media/context, and generated responses, and authorized human reviewers may read and annotate them to train and improve Google products and AI models.
   - **On the Paid Tier (Billed Google Cloud Project):** Google states that prompts and responses are **not** used to train or fine-tune general Google AI/ML models, except models specifically used for safety and policy enforcement.
2. **Abuse Monitoring & Temporary Retention (Both Free and Paid Tiers):**
   - Even on a **Paid Tier** account, Google retains API prompts, contextual information, and generated outputs for **55 days** for automated and (if flagged for suspected policy violations) manual abuse monitoring to enforce the Generative AI Prohibited Use Policy and comply with legal obligations.
   - **A Paid Tier configuration does not by itself mean data is deleted immediately or that every privacy concern is resolved.** We do **not** claim that Google deletes transmitted data immediately.
3. **What Is Transmitted to Google Gemini:**
   - **For text-based PDFs:** Only the **redacted text layer** (after regex/rule-based removal of emails, phone numbers, PAN/taxpayer IDs, and street addresses) plus the system prompt and selected language codes are sent over HTTPS.
   - **For image files (PNG, JPEG, WebP) or scanned/image-only PDF pages:** Nothing is sent during initial inspection (`/api/inspect`). Only after the user explicitly checks the confirmation box (`image_confirmed=true`) are the raw image bytes sent to Gemini for vision/OCR extraction. **Images and rasterized scan pages are NOT redacted before transmission.**
   - **Never restored:** Redacted placeholders (`[REDACTED_EMAIL]`, `[REDACTED_PHONE]`, `[REDACTED_ID]`, `[REDACTED_ADDRESS]`) are **never** reversed or restored in the returned JSON or UI.

---

## 3. Storage & Logging Boundaries (Civisterial vs. Hosting Provider vs. Google)

| Layer | Controlled By | What Is Stored or Logged | What Is Excluded |
|---|---|---|---|
| **Browser Frontend** | Civisterial (`frontend/`) | React component state in the active browser tab only. Closing or refreshing the tab clears the result. | Zero `localStorage`, zero `sessionStorage`, zero `document.cookie`, zero third-party analytics or ad trackers. |
| **Application Backend** | Civisterial (`backend/`) | Structured operational access log (`request_id`, HTTP `method`, `route`, `status`, `duration_ms`) and error exception types. Temporary upload files created during parsing are removed in `finally` blocks after request completion. | No database, no user accounts, no document archive, no raw document text, and no request bodies in application logs. |
| **Cloud Hosting Infrastructure** | Vercel / Netlify (frontend) & Render / Railway (backend) | Infrastructure-level HTTP metadata (client IP, timestamp, status code, user-agent), platform runtime logs, and crash/restart diagnostics managed by the hosting provider. | Application access logs are configured (`--no-access-log`) to exclude request bodies and document content. |
| **AI Inference Provider** | Google (`generativelanguage.googleapis.com`) | Redacted text prompt (and confirmed image bytes, if uploaded) plus structured JSON response, governed by Google's Gemini API Terms (including 55-day abuse-monitoring retention). | Unredacted text-layer identifiers stripped prior to API call; unconfirmed images (blocked with HTTP `400`). |

---

## 4. What Could Not Be Independently Verified

- **Provider-Side Deletion Timing:** While Civisterial's code creates no persistent database records and deletes temporary parse files immediately upon request completion, we **cannot independently verify** the internal storage subsystems, backup purging schedules, or physical deletion timelines of Render, Railway, Vercel, Netlify, or Google's servers. Therefore, Civisterial makes **no absolute guarantees** regarding infrastructure-level retention or immediate deletion by third-party cloud providers.
- **Residual Identifiers in Unstructured Text or Images:** Automated redaction relies on pattern matching for common identifier formats (emails, phone numbers, PAN-style IDs, street addresses). Unusual identifier formats, handwritten notes, or text embedded inside images/scans are **not** guaranteed to be redacted.