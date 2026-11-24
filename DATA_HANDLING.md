# Civisterial — Data Handling & External AI Service Record

- **External AI Service:** Google Gemini API (`google-genai` Python SDK)
- **Model Identifier:** Configured via `GEMINI_MODEL` environment variable (default: `gemini-2.5-flash`)
- **Account / Billing Tier:** not yet verified
- **Data Logging & Retention Policy (Provider Side):** not yet verified
- **Date Current Terms Were Checked:** not yet verified

## Application-Level Safeguards
1. **Text PDFs:** Extracted per page in an isolated worker process, redacted deterministically in request memory before transmission, and sent with explicit page markers (`--- Page N ---`). Original unredacted values are never transmitted or logged.
2. **Images & Image-Based PDF Pages:** Never transmitted unless the caller supplies an explicit `image_confirmation` declaration affirming that the uploaded material is a **public or synthetic document** for this MVP. Because the system cannot automatically verify whether a document is public or synthetic, this is enforced strictly as an explicit user declaration.
3. **Zero Body Logging:** Request payloads, uploaded files, extracted text, redaction mappings, and model responses are never written to application logs.