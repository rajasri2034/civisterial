# Civisterial

**Civisterial** is a grounded, privacy-conscious civic and administrative document-explanation web application. It converts bureaucratic notices, circulars, application instructions, and forms into plain-language summaries, structured requirement checklists, verified deadlines, and exact fee breakdowns—while enforcing verbatim quote verification and pre-inference PII redaction.

---

## 1. The Problem

Public and administrative documents are frequently written in dense legalistic language, span multiple pages, or mix mandatory rules with optional guidance and publication dates. When citizens paste these documents into general-purpose AI chatbots:
1. **Hallucinated Deadlines & Fees:** Standard prompts frequently mistake a document's issue/print date for a submission deadline or invent typical fees when none are stated.
2. **Unverified Paraphrases:** Users cannot tell whether a summarized requirement actually appears in the source document or was inferred by the model.
3. **Uncontrolled Data Exposure:** Raw personal identifiers (phone numbers, email addresses, tax IDs, street addresses) and scanned images are transmitted directly to third-party APIs and stored in browser history or chat logs.

---

## 2. How It Works

1. **Inspection Gate (`POST /api/inspect`):** When a user selects a PDF or image file, the backend validates magic bytes and inspects pages in an isolated subprocess (`parser_worker.py`). If any page is image-based (a raster image or scanned PDF without a text layer), the UI pauses and requires explicit user confirmation (`image_confirmed=true`) before sending image bytes to Gemini.
2. **Pre-Inference PII Redaction (`redactor.py`):** Before calling Gemini, Civisterial masks emails, phone numbers, PAN-style identifiers, and street addresses in extracted text layers (`[REDACTED_EMAIL]`, `[REDACTED_PHONE]`, `[REDACTED_ID]`, `[REDACTED_ADDRESS]`). Masked identifiers are never restored in the output.
3. **Grounded Structured Extraction (`gemini_service.py`):** Redacted text (and explicitly confirmed images) is sent over HTTPS to Google Gemini (`gemini-3.5-flash` with fallback to `gemini-3.1-flash-lite` / `gemini-3.8-flash`) with `temperature=0.1`, a strict 10-rule document-only system instruction, and a Pydantic JSON schema (`GeminiDocumentAnalysis`).
4. **Two-Part Deterministic Verification (`verification_engine.py`):**
   - **Part A (Quotation Verification):** Checks every `evidence` and `original` quote character-for-character against the redacted source text and tags each item as `exact_quotation_found`, `possible_match`, or `needs_user_verification`.
   - **Part B (Lexical Claim Consistency Audit):** Audits extracted deadlines, fees, and mandatory/optional statuses against lexical cues in the quoted text so unsupported claims are downgraded to `needs_user_verification`.
5. **Stateless Delivery:** Results render in active React component state with clear verification badges and no client-side persistence.

---

## 3. System Architecture

```text
┌─────────────────────────────┐   HTTPS (Stateless, No Storage)   ┌──────────────────────────────────┐
│       React Frontend        │ ────────────────────────────────► │         FastAPI Backend          │
│ • Upload & Language Picker  │                                   │ • Rate Limiting & CORS           │
│ • Explicit Image Consent    │ ◄──────────────────────────────── │ • Magic-Byte & Size Validation   │
│ • Verification Badge UI     │     Verified JSON Response        │ • Safe Metadata-Only Access Logs │
└─────────────────────────────┘                                   └────────────────┬─────────────────┘
                                                                                   │
                                                                                   ▼
┌─────────────────────────────┐   Strict Pydantic Schema          ┌──────────────────────────────────┐
│  Verification Engine        │ ◄──────────────────────────────── │    Isolated Parser Subprocess    │
│ • Part A: Verbatim Quote    │                                   │ • PyMuPDF / Image Extraction     │
│ • Part B: Lexical Claim     │   Redacted Text + Confirmed Imgs  │ • Pre-Inference PII Redaction    │
└─────────────────────────────┘ ────────────────────────────────► └────────────────┬─────────────────┘
                                                                                   │
                                                                                   ▼
                                                                  ┌──────────────────────────────────┐
                                                                  │        Google Gemini API         │
                                                                  │   (Structured JSON Output)       │
                                                                  └──────────────────────────────────┘