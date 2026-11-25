# Civisterial Security & Privacy Assessment (`SECURITY.md`)

> **Scope & Limitations Notice:** Civisterial is designed with defense-in-depth controls for stateless document explanation, client-side PII masking on text layers, and isolated document parsing. **No software system is completely secure or privacy-proof.** Users must review the unresolved limitations documented below before uploading sensitive personal documents.

---

## 1. Implemented Security & Privacy Controls

1. **Stateless Execution & Zero Persistent Storage**
   - No database, user accounts, authentication tokens, cookies, `localStorage`, `sessionStorage`, or third-party analytics scripts exist in the application.
   - Analysis results live exclusively in browser React component state and are cleared immediately upon clicking **Delete my results**, cancelling an analysis, or closing/reloading the page.
   - Backend HTTP responses include `Cache-Control: no-store, no-cache, must-revalidate, max-age=0` and `Pragma: no-cache`.

2. **Upload Boundaries, Rate Limiting & HTTP Method Enforcement**
   - Uploads are restricted to `POST /api/inspect` and `POST /api/analyze` (`multipart/form-data`, max 1 file, max 4 fields). Disallowed HTTP methods return `405 Method Not Allowed`.
   - Streaming body size checks enforce a hard **10 MB** upload ceiling (`413 Payload Too Large` on excess).
   - IP-based rate limiting via `slowapi` (`RATE_LIMIT_ANALYZE`, default `10/minute`) returns `429 Too Many Requests` under rapid request bursts.

3. **Isolated Subprocess Document Parsing (`parser_worker.py`)**
   - PDF and raster image parsing runs inside a separate child process with isolated working directory, stripped environment variables (`GEMINI_API_KEY` is never passed to the parser worker), bounded page count (`MAX_PDF_PAGES = 25`), bounded raster pixel count (`MAX_IMAGE_PIXELS`), and a hard execution timeout (`WORKER_TIMEOUT_SECONDS`) that terminates hung or expensive files.
   - Magic-byte file signature inspection (`%PDF-`, PNG header, JPEG SOI) rejects spoofed file extensions and malformed polyglot headers before parsing.
   - Encrypted/password-protected PDFs are rejected (`400 Bad Request`). PDF JavaScript actions and embedded file attachments are never executed or extracted.

4. **Text-Layer PII Redaction & Image Confirmation Gate (`redactor.py`)**
   - Extracted text layers pass through deterministic regex + Presidio NER masking (`[EMAIL]`, `[PHONE]`, `[ID_NUMBER]`, `[PERSON]`, `[ADDRESS]`) before any text is sent to Gemini or returned to the client.
   - Raster images (`PNG`, `JPEG`) and PDF pages containing embedded images or zero text layer (`image_based`) **cannot** be automatically redacted; the backend independently rejects any request containing image-based pages unless `image_confirmation` explicitly declares that the upload is a public or synthetic document.
   - Per-page redaction status and masked entity counts are returned in the API payload and displayed in the UI.

5. **Request Cancellation & Temporary-File Hygiene (`security.py` & `main.py`)**
   - Frontend uses `fetch` with `AbortController` so clicking **Cancel** immediately aborts the HTTP connection.
   - Backend monitors `request.is_disconnected()` during analysis, cancels active tasks on disconnect, terminates active parser worker processes, and sweeps any newly created files in the isolated temp directory inside `finally:` blocks.
   - `MultiPartParser.spool_max_size` is configured to `10 MB` (`UPLOAD_SPOOL_THRESHOLD_BYTES`) so valid uploads within the 10 MB limit are buffered in memory rather than spooled to disk by Starlette's multipart parser.

6. **Secret Management, CORS & HTTP Security Headers**
   - `GEMINI_API_KEY` is read strictly on the backend from environment variables; the frontend bundle uses only `VITE_API_BASE_URL` and contains zero API keys.
   - CORS restricts browser cross-origin access to `FRONTEND_ORIGIN` with `allow_credentials=False`.
   - Security middleware sets `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, and `Permissions-Policy: camera=(), microphone=(), geolocation=()`.
   - Exception handlers normalize errors into safe messages and strip internal file paths, stack traces, and environment values.

---

## 2. Security Verification Suite Results

All automated checks are implemented in `backend/tests/test_security_suite.py`, `backend/tests/test_frontend_privacy_and_cancel.py`, and `backend/tests/test_security_foundation.py`.

| # | Security Test Area | Verification Method | Status | Observed Result |
|---|---|---|---|---|
| 1 | Upload limits, rate limits & HTTP methods | `test_1_upload_limits_rate_limits_and_http_methods` | **PASS** | `GET/PUT/DELETE /api/analyze` return `405`; >10 MB payload returns `413`; >10 req/min burst triggers `429`. |
| 2 | Stateless isolation & concurrent requests | `test_2_no_history_endpoints_and_concurrent_request_isolation` | **PASS** | History/results routes return `404`; concurrent `alpha.pdf` and `beta.pdf` requests show zero cross-request data leakage. |
| 3 | Malicious uploads (fake headers, polyglot, encrypted, JS/attachments, traversal) | `test_3_malicious_uploads_rejected_or_safely_contained` | **PASS** | Fake PDF header and encrypted PDF return `400`; unconfirmed PNG+ZIP polyglot returns `400`; embedded JS/attachments are ignored; `../../../../` filename never writes outside temp dir. |
| 4 | Denial-of-service & worker resource limits | `test_4_dos_huge_page_count_and_worker_timeout` | **PASS** | >25-page PDF rejected (`400`); hung worker subprocess terminated at timeout and returns clean HTTP error. |
| 5 | API key exposure (bundle, API, errors, Git history) | `test_5_no_api_key_in_frontend_responses_errors_or_git_history` | **PASS** | Zero occurrences of `GEMINI_API_KEY` or `AIza...` patterns in frontend source/build, API responses, error payloads, or recent `git log -p`. |
| 6 | Temp-file cleanup & multipart spooling | `test_6_temp_file_cleanup_and_multipart_spooling` | **PASS** | Valid uploads (<10 MB) created **0** files in the isolated temp directory (in-memory multipart buffering confirmed); corrupt uploads and mid-flight client cancellations left **0** leftover temp files. |
| 7 | Accidental personal-data logging | `test_7_no_personal_data_written_to_logs` | **PASS** | Captured `DEBUG`/`INFO`/`ERROR` logs contained zero occurrences of uploaded fake name, email, phone, or ID values. |
| 8 | Privacy redaction & image confirmation gate | `test_8_privacy_redaction_image_gate_and_mixed_pdf_status` | **PASS** | Mixed PDF rejected (`400`) without `image_confirmation`; with confirmation, Page 1 PII is masked (`[EMAIL]`, `[PHONE]`, `[ID_NUMBER]`) and Page 2 is flagged `image_based` (`redaction_applied: false`). |
| 9 | CORS, security headers & sanitized errors | `test_9_cors_security_headers_and_sanitized_errors` | **PASS** | Disallowed origin receives no `Access-Control-Allow-Origin` header; `nosniff`, `DENY`, `no-store`, and `no-referrer` headers verified; errors contain no stack traces or local paths. |

---

## 3. Known & Unresolved Security/Privacy Limitations

The following limitations are known and remain unresolved in the current MVP:

1. **No Automated Redaction on Images or Scanned PDFs:** Images (`PNG`, `JPEG`) and PDF pages containing embedded images or raster scans are **not** redacted before transmission to the Gemini API. Only digital PDF text layers undergo regex/NER masking.
2. **Heuristic Text Redaction Coverage:** Automated regex and NER redaction targets common emails, phone numbers, government ID patterns, and names, but may miss unusual identifier formats, handwritten text, or context-specific sensitive details. Conversely, aggressive masking can occasionally redact non-sensitive numbers.
3. **External LLM Data Processing:** Redacted text layers (and user-confirmed public/synthetic images) are transmitted over TLS to the Google Gemini API for inference. Retention and handling at the model provider layer are governed by the configured Google AI / Gemini API terms.
4. **In-Memory Rate Limiting Scope:** `slowapi` rate limiting uses in-memory storage per backend worker process and keys by client IP (`get_remote_address`). Behind a reverse proxy or multi-worker deployment, distributed rate limiting (e.g., Redis) and trusted `X-Forwarded-For` configuration are required.
5. **HTTPS Enforcement Relies on Deployment Proxy:** The FastAPI/Uvicorn application serves HTTP locally; TLS/HTTPS termination and HSTS (`Strict-Transport-Security`) must be enforced at the production reverse proxy / hosting platform (e.g., Render, Cloud Run, Nginx, or Cloudflare).