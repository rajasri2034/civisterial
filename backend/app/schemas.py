from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

PageKind = Literal["text", "image_based", "empty"]
RedactionStatus = Literal["redacted", "nothing_detected", "not_applicable_image_page"]
QuotationStatus = Literal[
    "exact_quotation_found",
    "possible_match",
    "not_found",
    "needs_user_verification",
]
ClaimCheckStatus = Literal[
    "passed",
    "failed",
    "needs_user_verification",
    "not_applicable",
]

NOT_STATED_SENTINEL = "Not stated in the document."


class PageExtraction(BaseModel):
    page_number: int
    kind: PageKind
    char_count: int
    text: str
    redacted_text: str
    redaction_status: RedactionStatus
    redaction_applied: bool
    redaction_counts: dict[str, int]
    notice: str | None = None


class InspectUploadResponse(BaseModel):
    request_id: str
    file_type: Literal["pdf", "png", "jpeg"]
    page_count: int
    has_image_based_content: bool
    requires_image_confirmation: bool
    detected_language_code: str
    detected_language_label: str
    language_detection_uncertain: bool
    pages: list[PageExtraction]


# --- Gemini Extraction Models ---


class DocumentMetadataField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str
    evidence: str = ""
    page: int | None = None

    @model_validator(mode="after")
    def check_evidence_when_stated(self) -> "DocumentMetadataField":
        cleaned = self.value.strip()
        if cleaned == NOT_STATED_SENTINEL:
            self.evidence = ""
            self.page = None
        elif not self.evidence.strip():
            raise ValueError(
                "Identified document metadata must include an exact verbatim evidence quotation."
            )
        return self


class SimplifiedPassage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    original: str
    simplified: str
    page: int | None = None

    @model_validator(mode="after")
    def require_original_quote(self) -> "SimplifiedPassage":
        if not self.original.strip():
            raise ValueError("simplified_passages.original must carry an exact verbatim quote.")
        return self


class RequirementItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item: str
    status: Literal["mandatory", "optional", "unclear"]
    evidence: str
    page: int | None = None

    @model_validator(mode="after")
    def require_evidence(self) -> "RequirementItem":
        if not self.evidence.strip():
            raise ValueError("requirements.evidence must carry an exact verbatim quotation.")
        return self


class ActionStepItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: str
    description: str
    evidence: str
    page: int | None = None
    ordering: Literal["stated_in_document", "ai_organised"]

    @model_validator(mode="after")
    def require_evidence(self) -> "ActionStepItem":
        if not self.evidence.strip():
            raise ValueError("action_steps.evidence must carry an exact verbatim quotation.")
        return self


class DeadlineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str
    date_text: str
    ambiguous: bool
    evidence: str
    page: int | None = None

    @model_validator(mode="after")
    def check_deadline_evidence(self) -> "DeadlineItem":
        if self.date_text.strip() in ("NO_DEADLINE", NOT_STATED_SENTINEL):
            self.evidence = ""
        elif not self.evidence.strip():
            raise ValueError("deadlines.evidence must carry an exact verbatim quotation.")
        return self


class FeeItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: str
    purpose: str
    evidence: str
    page: int | None = None

    @model_validator(mode="after")
    def check_fee_evidence(self) -> "FeeItem":
        if self.amount.strip() in ("NO_FEE", NOT_STATED_SENTINEL):
            self.evidence = ""
        elif not self.evidence.strip():
            raise ValueError("fees.evidence must carry an exact verbatim quotation.")
        return self


class GeminiDocumentAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    readability: Literal["good", "poor", "unreadable"]
    document_title: DocumentMetadataField
    issuing_authority: DocumentMetadataField
    document_type: DocumentMetadataField
    summary: str
    simplified_passages: list[SimplifiedPassage] = Field(default_factory=list)
    requirements: list[RequirementItem] = Field(default_factory=list)
    action_steps: list[ActionStepItem] = Field(default_factory=list)
    deadlines: list[DeadlineItem] = Field(default_factory=list)
    fees: list[FeeItem] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class VerificationMetadataMixin(BaseModel):
    quotation_status: QuotationStatus
    quotation_label: str
    claim_check: ClaimCheckStatus
    claim_note: str | None = None
    actual_page: int | None = None
    page_corrected: bool = False
    page_note: str | None = None
    similarity_score: float = 0.0


class VerifiedDocumentMetadataField(DocumentMetadataField, VerificationMetadataMixin):
    pass


class VerifiedSimplifiedPassage(SimplifiedPassage, VerificationMetadataMixin):
    pass


class VerifiedRequirementItem(RequirementItem, VerificationMetadataMixin):
    pass


class VerifiedActionStepItem(ActionStepItem, VerificationMetadataMixin):
    pass


class VerifiedDeadlineItem(DeadlineItem, VerificationMetadataMixin):
    pass


class VerifiedFeeItem(FeeItem, VerificationMetadataMixin):
    pass


class VerifiedDocumentAnalysis(BaseModel):
    readability: Literal["good", "poor", "unreadable"]
    document_title: VerifiedDocumentMetadataField
    issuing_authority: VerifiedDocumentMetadataField
    document_type: VerifiedDocumentMetadataField
    summary: str
    simplified_passages: list[VerifiedSimplifiedPassage] = Field(default_factory=list)
    requirements: list[VerifiedRequirementItem] = Field(default_factory=list)
    action_steps: list[VerifiedActionStepItem] = Field(default_factory=list)
    deadlines: list[VerifiedDeadlineItem] = Field(default_factory=list)
    fees: list[VerifiedFeeItem] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    verification_limitation_note: str


class AnalyzeUploadResponse(BaseModel):
    request_id: str
    file_type: Literal["pdf", "png", "jpeg"]
    page_count: int
    has_image_based_content: bool
    image_confirmation_provided: bool
    detected_language_code: str
    detected_language_label: str
    language_detection_uncertain: bool
    document_language: str
    explanation_language: str
    explanation_direction: Literal["ltr", "rtl"]
    pages: list[PageExtraction]
    analysis: VerifiedDocumentAnalysis
    disclaimer: str = (
        "This tool provides plain-language administrative guidance, not legal advice."
    )