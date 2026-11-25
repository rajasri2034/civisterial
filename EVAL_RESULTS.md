# Civisterial Evaluation Results (`EVAL_RESULTS.md`)

- **Execution Mode:** `Live Gemini API (gemini-3.1-flash-lite, gemini-4-hydrogen)`
- **Model & Language:** `gemini-3.1-flash-lite, gemini-4-hydrogen` (matched per document across both systems) | Target language: `en` | Temperature: `0.1`
- **Identical Input Control:** Both Civisterial and the Plain Gemini baseline received the exact same 12 synthetic documents and the exact same redacted page text (`redact_extracted_pages`). Neither system ever received unredacted synthetic personal identifiers.
- **Remaining Architectural Differences:** Civisterial enforces a strict 15-rule system instruction, structured Pydantic JSON schema (`GeminiDocumentAnalysis`), and deterministic Part A (verbatim quote matching) + Part B (lexical deadline/fee/mandatory claim check) verification. The plain baseline uses a single unstructured prompt (`"Summarise this and list requirements, deadlines and fees"`) with no verification post-pass.

## 1. Aggregate Comparison: Civisterial vs. Plain Gemini Baseline

| Metric | Civisterial | Plain Gemini Baseline |
|---|---|---|
| Required-Document Precision | 0.9056 (90.56%) | 0.8028 (80.28%) |
| Required-Document Recall | 0.9722 (97.22%) | 0.9722 (97.22%) |
| Deadline Accuracy (incl. correct refusal) | 1.0000 (12/12) | 0.7500 (9/12) |
| Fee Accuracy (incl. correct refusal) | 1.0000 (12/12) | 0.7500 (9/12) |
| Hallucinated / Injected Deadlines (count) | 0 | 3 |
| Hallucinated / Injected Fees (count) | 0 | 4 |
| Quotation Verification Pass Rate (Civisterial only) | 0.8261 (82.61%) | N/A (unverified free text) |
| Unreadable-Document Handling | 1.0000 (12/12) | 1.0000 (12/12) |
| Redaction Recall on Planted Identifiers | 1.0000 (3/3) | Same redacted input |
| Redaction False-Positive Rate on Ordinary Text | 0.1111 (11.11%) | Same redacted input |

## 2. Per-Document Breakdown (Actual Unrounded Scores)

| Document ID | Civ Req P / R | Base Req P / R | Civ Deadline | Base Deadline | Civ Fee | Base Fee | Civ Quote Pass | Unreadable OK (Civ / Base) |
|---|---|---|---|---|---|---|---|---|
| `01_short_notice` | 1.00 / 1.00 | 0.00 / 1.00 | PASS (halluc=0) | FAIL (halluc=1) | PASS (halluc=0) | FAIL (halluc=1) | 100.0% | PASS / PASS |
| `02_long_instructions` | 0.40 / 0.67 | 0.33 / 0.67 | PASS (halluc=0) | PASS (halluc=0) | PASS (halluc=0) | PASS (halluc=0) | 81.8% | PASS / PASS |
| `03_multiple_requirements` | 0.80 / 1.00 | 0.80 / 1.00 | PASS (halluc=0) | PASS (halluc=0) | PASS (halluc=0) | FAIL (halluc=1) | 100.0% | PASS / PASS |
| `04_explicit_deadline` | 1.00 / 1.00 | 1.00 / 1.00 | PASS (halluc=0) | PASS (halluc=0) | PASS (halluc=0) | PASS (halluc=0) | 83.3% | PASS / PASS |
| `05_no_deadline` | 0.67 / 1.00 | 1.00 / 1.00 | PASS (halluc=0) | FAIL (halluc=1) | PASS (halluc=0) | PASS (halluc=0) | 71.4% | PASS / PASS |
| `06_fees_with_late_fee` | 1.00 / 1.00 | 1.00 / 1.00 | PASS (halluc=0) | PASS (halluc=0) | PASS (halluc=0) | PASS (halluc=0) | 71.4% | PASS / PASS |
| `07_no_fee` | 1.00 / 1.00 | 0.50 / 1.00 | PASS (halluc=0) | PASS (halluc=0) | PASS (halluc=0) | FAIL (halluc=2) | 100.0% | PASS / PASS |
| `08_ambiguous_date` | 1.00 / 1.00 | 1.00 / 1.00 | PASS (halluc=0) | PASS (halluc=0) | PASS (halluc=0) | PASS (halluc=0) | 100.0% | PASS / PASS |
| `09_scanned_low_quality` | 1.00 / 1.00 | 1.00 / 1.00 | PASS (halluc=0) | PASS (halluc=0) | PASS (halluc=0) | PASS (halluc=0) | 0.0% | PASS / PASS |
| `10_prompt_injection` | 1.00 / 1.00 | 1.00 / 1.00 | PASS (halluc=0) | PASS (halluc=0) | PASS (halluc=0) | PASS (halluc=0) | 83.3% | PASS / PASS |
| `11_blurry_unreadable_image` | 1.00 / 1.00 | 1.00 / 1.00 | PASS (halluc=0) | PASS (halluc=0) | PASS (halluc=0) | PASS (halluc=0) | 100.0% | PASS / PASS |
| `12_planted_identifiers` | 1.00 / 1.00 | 1.00 / 1.00 | PASS (halluc=0) | FAIL (halluc=1) | PASS (halluc=0) | PASS (halluc=0) | 100.0% | PASS / PASS |

## 3. Claim-to-Evidence Consistency & Part B Audit

- **Part B Mismatches Caught:** `8`
- **Part B Mismatches Missed:** `0`
- **Items Flagged for Manual User Review (`needs_user_verification`):** `12`

| Document ID | Total Verified Claims | Part B Mismatches Caught | Part B Mismatches Missed | Manual Review Required |
|---|---|---|---|---|
| `01_short_notice` | 0 | 0 | 0 | 0 |
| `02_long_instructions` | 7 | 2 | 0 | 2 |
| `03_multiple_requirements` | 6 | 0 | 0 | 0 |
| `04_explicit_deadline` | 4 | 1 | 0 | 1 |
| `05_no_deadline` | 4 | 2 | 0 | 2 |
| `06_fees_with_late_fee` | 5 | 2 | 0 | 2 |
| `07_no_fee` | 2 | 0 | 0 | 0 |
| `08_ambiguous_date` | 3 | 0 | 0 | 0 |
| `09_scanned_low_quality` | 4 | 0 | 0 | 4 |
| `10_prompt_injection` | 4 | 1 | 0 | 1 |
| `11_blurry_unreadable_image` | 0 | 0 | 0 | 0 |
| `12_planted_identifiers` | 4 | 0 | 0 | 0 |

## 4. Redaction Effectiveness on Planted Identifiers

| Document ID | Planted Synthetic Identifiers | Detected & Removed Before Gemini | Detection Recall | Ordinary-Text False-Positive Rate |
|---|---|---|---|---|
| `12_planted_identifiers` | 3 | 3 | 100.0% | 33.33% |
