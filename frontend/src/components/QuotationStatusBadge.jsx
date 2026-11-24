import React from "react";

export function QuotationStatusBadge({ status }) {
  switch (status) {
    case "exact_quotation_found":
      return (
        <span className="gov-tag gov-tag--green">
          <span aria-hidden="true">✓</span> Exact quotation found
        </span>
      );
    case "possible_match":
      return (
        <span className="gov-tag gov-tag--amber">
          <span aria-hidden="true">~</span> Possible match: review required
        </span>
      );
    case "not_found":
      return (
        <span className="gov-tag gov-tag--red">
          <span aria-hidden="true">✕</span> Not found
        </span>
      );
    case "needs_user_verification":
    default:
      return (
        <span className="gov-tag gov-tag--amber">
          <span aria-hidden="true">!</span> Needs user verification
        </span>
      );
  }
}

export default QuotationStatusBadge;