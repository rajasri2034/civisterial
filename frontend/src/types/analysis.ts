export type QuotationStatus =
  | "exact_quotation_found"
  | "possible_match"
  | "not_found"
  | "needs_user_verification";

export type ClaimCheckStatus =
  | "passed"
  | "failed"
  | "needs_user_verification"
  | "not_applicable";

export interface PageExtraction {
  page_number: number;
  kind: "text" | "image_based" | "empty";
  char_count: number;
  text: string;
  redacted_text: string;
  redaction_status: "redacted" | "nothing_detected" | "not_applicable_image_page";
  redaction_applied: boolean;
  redaction_counts: Record<string, number>;
  notice: string | null;
}

export interface InspectUploadResponse {
  request_id: string;
  file_type: "pdf" | "png" | "jpeg";
  page_count: number;
  has_image_based_content: boolean;
  requires_image_confirmation: boolean;
  detected_language_code: string;
  detected_language_label: string;
  language_detection_uncertain: boolean;
  pages: PageExtraction[];
}

export interface VerificationFields {
  quotation_status: QuotationStatus;
  quotation_label: string;
  claim_check: ClaimCheckStatus;
  claim_note: string | null;
  actual_page: number | null;
  page_corrected: boolean;
  page_note: string | null;
  similarity_score: number;
}

export interface VerifiedMetadataField extends VerificationFields {
  value: string;
  evidence: string;
  page: number | null;
}

export interface VerifiedSimplifiedPassage extends VerificationFields {
  original: string;
  simplified: string;
  page: number | null;
}

export interface VerifiedRequirementItem extends VerificationFields {
  item: string;
  status: "mandatory" | "optional" | "unclear";
  evidence: string;
  page: number | null;
}

export interface VerifiedActionStepItem extends VerificationFields {
  task: string;
  description: string;
  evidence: string;
  page: number | null;
  ordering: "stated_in_document" | "ai_organised";
}

export interface VerifiedDeadlineItem extends VerificationFields {
  description: string;
  date_text: string;
  ambiguous: boolean;
  evidence: string;
  page: number | null;
}

export interface VerifiedFeeItem extends VerificationFields {
  amount: string;
  purpose: string;
  evidence: string;
  page: number | null;
}

export interface VerifiedDocumentAnalysis {
  readability: "good" | "poor" | "unreadable";
  document_title: VerifiedMetadataField;
  issuing_authority: VerifiedMetadataField;
  document_type: VerifiedMetadataField;
  summary: string;
  simplified_passages: VerifiedSimplifiedPassage[];
  requirements: VerifiedRequirementItem[];
  action_steps: VerifiedActionStepItem[];
  deadlines: VerifiedDeadlineItem[];
  fees: VerifiedFeeItem[];
  missing_information: string[];
  warnings: string[];
  verification_limitation_note: string;
}

export interface AnalyzeUploadResponse {
  request_id: string;
  file_type: "pdf" | "png" | "jpeg";
  page_count: number;
  has_image_based_content: boolean;
  image_confirmation_provided: boolean;
  detected_language_code: string;
  detected_language_label: string;
  language_detection_uncertain: boolean;
  document_language: string;
  explanation_language: string;
  explanation_direction: "ltr" | "rtl";
  pages: PageExtraction[];
  analysis: VerifiedDocumentAnalysis;
  disclaimer: string;
}
