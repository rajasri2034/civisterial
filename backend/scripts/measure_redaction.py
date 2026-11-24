"""Evaluation script reporting detection recall on planted synthetic PII
and false-positive rate on ordinary administrative text.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.redactor import redact_extracted_pages, verhoeff_compute_check_digit


def _synth_aadhaar(prefix_11: str, sep: str = " ") -> str:
    full = prefix_11 + verhoeff_compute_check_digit(prefix_11)
    if sep:
        return f"{full[:4]}{sep}{full[4:8]}{sep}{full[8:]}"
    return full


def run_benchmark() -> None:
    planted_items = [
        ("AADHAAR", _synth_aadhaar("23456789123", " ")),
        ("AADHAAR", _synth_aadhaar("87654321987", "-")),
        ("AADHAAR", _synth_aadhaar("34567891234", "")),
        ("PHONE", "+91 98765 43210"),
        ("PHONE", "9123456780"),
        ("PHONE", "+44 20 7946 0123"),
        ("EMAIL", "citizen.alpha@example.org"),
        ("EMAIL", "welfare.desk@example.gov.in"),
        ("BANK_ACCOUNT", "30918273645129"),
        ("BANK_ACCOUNT", "918273645019"),
        ("IFSC", "ICIC0000456"),
        ("IFSC", "PUNB0123400"),
        ("PAN", "LMNOP4321Q"),
        ("PAN", "BCDEF9876H"),
    ]

    planted_corpus = (
        f"1. Primary applicant Aadhaar {planted_items[0][1]} and spouse Aadhaar {planted_items[1][1]}.\n"
        f"2. Compact Aadhaar record {planted_items[2][1]}.\n"
        f"3. Primary mobile {planted_items[3][1]}, alternate {planted_items[4][1]}, UK line {planted_items[5][1]}.\n"
        f"4. Emails: {planted_items[6][1]} and {planted_items[7][1]}.\n"
        f"5. Disbursement Bank Account {planted_items[8][1]} (IFSC {planted_items[10][1]}) "
        f"and secondary A/C {planted_items[9][1]} (IFSC {planted_items[11][1]}).\n"
        f"6. Tax PAN {planted_items[12][1]} and co-applicant PAN {planted_items[13][1]}.\n"
    )

    ordinary_corpus_lines = [
        "Notice of Assessment dated 14/09/2026 under Section 143(1) of the Municipal Act.",
        "Total statutory fee payable is Rs. 12,500.00 (INR 12500) before 30/10/2026.",
        "Quote Application Reference REF-202609148821 and Case No. 987654321012 in all letters.",
        "Building Permit #440192837465 is valid for 24 months from the date of issue.",
        "Ward Office 14, Block B, Anna Salai, Chennai 600002, Tamil Nadu.",
        "Appeal hearings are scheduled between 10:30 AM and 04:00 PM on working days.",
        "Receipt Voucher 2026-11-24-0091827364 confirms acknowledgement of your filing.",
        "Standard processing turnaround is 15 to 21 working days excluding public holidays.",
    ]
    ordinary_corpus = "\n".join(ordinary_corpus_lines)

    # Evaluate Recall on Planted Corpus
    redacted_planted = redact_extracted_pages(
        [{"page_number": 1, "kind": "text", "text": planted_corpus, "notice": None}]
    )[0]
    masked_planted_text = redacted_planted["redacted_text"]

    detected_count = sum(1 for _, val in planted_items if val not in masked_planted_text)
    total_planted = len(planted_items)
    recall = (detected_count / total_planted) * 100.0

    # Evaluate False Positives on Ordinary Text
    redacted_ordinary = redact_extracted_pages(
        [{"page_number": 1, "kind": "text", "text": ordinary_corpus, "notice": None}]
    )[0]
    fp_tokens = re.findall(r"\[[A-Z_]+_\d+\]", redacted_ordinary["redacted_text"])
    ordinary_token_count = len(ordinary_corpus.split())
    fp_rate = (len(fp_tokens) / ordinary_token_count) * 100.0

    print("=== Civisterial Redaction Evaluation ===")
    print(f"Planted identifiers : {detected_count}/{total_planted} detected (Recall: {recall:.1f}%)")
    print(f"Counts by type      : {redacted_planted['redaction_counts']}")
    print(
        f"Ordinary text FPs   : {len(fp_tokens)} false positives across {ordinary_token_count} tokens "
        f"(FPR: {fp_rate:.2f}%)"
    )


if __name__ == "__main__":
    run_benchmark()

    