from typing import Literal
from pydantic import BaseModel, Field, model_validator

PageKind = Literal["text", "image_based", "empty"]
RedactionStatus = Literal["redacted", "nothing_detected", "not_applicable_image_page"]

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


class DocumentMetadataField(BaseModel):
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
    original: str
    simplified: str
    page: int | None = None

    @model_validator(mode="after")
    def require_original_quote(self) -> "SimplifiedPassage":
        if not self.original.strip():
            raise ValueError("simplified_passages.original must carry an exact verbatim quote.")
        return self


class RequirementItem(BaseModel):
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


class AnalyzeUploadResponse(BaseModel):
    request_id: str
    file_type: Literal["pdf", "png", "jpeg"]
    page_count: int
    has_image_based_content: bool
    image_confirmation_provided: bool
    pages: list[PageExtraction]
    analysis: GeminiDocumentAnalysis
    disclaimer: str = (
        "This tool provides plain-language administrative guidance, not legal advice."
    )