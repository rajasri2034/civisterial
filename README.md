# Civisterial — Data Handling, Privacy & Model Configuration

Civisterial is built as a **stateless, zero-retention** administrative document assistant. Every uploaded file and extracted text buffer is processed strictly in volatile memory for the duration of a single HTTP request and is never persisted to disk, databases, browser storage, or application logs.

---

## 1. End-to-End Document Lifecycle

1. **Client-Side Selection & Stateless Browser Policy**
   - Users select a PDF, PNG, or JPEG file (up to **10 MB**) in the browser.
   - The frontend uses zero persistent browser storage: no `localStorage`, no `sessionStorage`, no `document.cookie`, and no third-party analytics or tracking scripts.
   - Closing or refreshing the tab clears all in-memory React state immediately.

2. **In-Memory Inspection (`/api/inspect`)**
   - Uploaded bytes are read into Python memory (`BytesIO`), validated by magic-byte signature (`%PDF-`, PNG, or JPEG header) and file size, and inspected page-by-page.
   - No temporary files are written to `/tmp` or local storage.

3. **Automated Text PII Redaction & Image Consent Gate (`/api/analyze`)**
   - **Text-layer PDFs:** Before any text is sent to the Gemini API, deterministic regex and pattern-matching rules mask common personal identifiers in memory—including email addresses, phone numbers, Social Security / national ID numbers, passport/driver-license patterns, bank/IBAN account numbers, and street addresses—replacing them with typed tokens such as `[REDACTED_EMAIL]` or `[REDACTED_ID]`.
   - **Scanned / Image Pages:** Image bytes cannot be reliably masked with text regex rules. Whenever a PDF contains image-only pages or the user uploads a PNG/JPEG, Civisterial requires an explicit user confirmation checkbox (`consent_unredacted_images=true`) before transmitting page images to the model.

4. **Response Delivery & Immediate Memory Release**
   - The backend returns a structured JSON response containing the plain-language summary, action checklist, deadlines, fees, verbatim source quotes, and a redaction summary count.
   - Request buffers go out of scope immediately upon response completion and are garbage-collected.

---

## 2. Model Configuration

Civisterial separates its hosted production model configuration from its code-level fallback default:

- **Hosted Production Configuration (Render):** Configured via `GEMINI_MODEL=gemini-3.5-flash` in `render.yaml` and the Render web service environment variables.
- **Code Fallback Default:** If `GEMINI_MODEL` is unset in local development or custom deployments, the FastAPI backend (`backend/app/config.py`) falls back to `gemini-2.5-flash`.
- **Offline Evaluation Mode:** When `MOCK_MODE=true`, the backend returns deterministic fixture responses without making external Gemini API calls.

---

## 3. Logging & Telemetry Policy

- **No Document Content in Logs:** Request handlers, middleware, and exception formatters never log raw document text, redacted text, file names, base64 image payloads, or model outputs.
- **No Secret Exposure:** API keys (`GEMINI_API_KEY`) are injected strictly via server-side environment variables and are never bundled into frontend assets or returned in HTTP responses.
- **Transport & Browser Security Headers:**
  - All production traffic between Vercel (`https://civisterial.vercel.app`) and Render (`https://civisterial-api.onrender.com`) runs over HTTPS.
  - Strict `Content-Security-Policy`, `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff`, and `Permissions-Policy` headers restrict network connections solely to the configured backend origin.

---

## 4. User Export & Disclaimers

- **Client-Generated Exports:** Downloading a `.txt` summary or printing an A4 copy happens locally inside the user's browser from in-memory state without any additional server round-trip.
- **Non-Legal Guidance Notice:** Civisterial provides plain-language administrative guidance only and does not constitute legal, financial, or official government advice. Users should verify all actions and deadlines against the quoted sections of their original notice.