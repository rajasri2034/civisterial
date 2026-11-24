/**
 * Resolve backend API URL from Vite environment configuration.
 * Contains zero API keys or secrets.
 */
const RAW_API_BASE = (import.meta.env.VITE_API_BASE_URL || "").trim().replace(/\/+$/, "");

export function apiUrl(path) {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return RAW_API_BASE ? `${RAW_API_BASE}${cleanPath}` : cleanPath;
}

/**
 * Map HTTP status codes and backend error categories to plain, friendly user messages.
 * Never exposes stack traces, exception class names, or internal technical details.
 */
export function mapFriendlyApiError(status, backendMessage = "") {
  const lower = String(backendMessage || "").toLowerCase();

  if (lower.includes("unreadable") || lower.includes("read this document clearly")) {
    return "We couldn't read this document clearly. Please upload a higher-quality image or PDF.";
  }

  if (
    lower.includes("not contain enough readable information") ||
    lower.includes("too little") ||
    lower.includes("empty")
  ) {
    return "This document does not contain enough readable information for reliable analysis.";
  }

  if (status === 429 || lower.includes("rate limit") || lower.includes("too many requests")) {
    return "Too many documents were submitted in a short time. Please wait a minute and try again.";
  }

  if (status === 504 || lower.includes("timed out") || lower.includes("took too long")) {
    return "The analysis took too long to complete. Please try again shortly.";
  }

  if (status === 413 || lower.includes("maximum allowed size") || lower.includes("10 mb")) {
    return "The selected file exceeds the 10 MB limit. Please upload a smaller file.";
  }

  if (status === 400 || status === 422) {
    // Preserve safe, user-actionable validation guidance while stripping technical tokens
    if (
      lower.includes("public or synthetic") ||
      lower.includes("image_confirmation") ||
      lower.includes("not currently supported") ||
      lower.includes("pdf, png, or jpeg") ||
      lower.includes("encrypted") ||
      lower.includes("password") ||
      lower.includes("page")
    ) {
      return backendMessage;
    }
    return "We could not process this file. Please check that it is a valid PDF, PNG, or JPEG under 10 MB.";
  }

  if (status >= 500 || status === 502 || status === 503) {
    return "The analysis service is temporarily unavailable. Please try again in a few moments.";
  }

  return "Unable to complete document analysis right now. Please try again.";
}