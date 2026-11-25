const DEFAULT_PROD_API_BASE_URL = "https://civisterial-api.onrender.com";

const rawBaseUrl = (import.meta.env.VITE_API_BASE_URL || "").trim();

export const API_BASE_URL = rawBaseUrl
  ? rawBaseUrl.replace(/\/+$/, "")
  : import.meta.env.PROD
    ? DEFAULT_PROD_API_BASE_URL
    : "";

export const API_ENDPOINTS = {
  health: "/api/health",
  languages: "/api/languages",
  inspect: "/api/inspect",
  analyze: "/api/analyze",
};

export function apiUrl(path) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
}

export function mapFriendlyApiError(statusOrError, fallbackDetail = "") {
  if (statusOrError && typeof statusOrError === "object") {
    if (statusOrError.name === "AbortError") {
      return "Analysis was cancelled.";
    }
    const status = statusOrError.status;
    const message = statusOrError.message || fallbackDetail;
    if (status) {
      return mapFriendlyApiError(status, message);
    }
    if (
      typeof message === "string" &&
      (message.includes("Failed to fetch") || message.includes("NetworkError"))
    ) {
      return "Could not reach the Civisterial server. Please wait a few seconds and try again.";
    }
    return message || "An unexpected error occurred while processing the document.";
  }

  const status = Number(statusOrError);
  if (status === 400) {
    return fallbackDetail || "The uploaded file could not be read. Please check the file and try again.";
  }
  if (status === 413) {
    return "This file exceeds the 10 MB upload limit.";
  }
  if (status === 415) {
    return "Unsupported file format. Please upload a PDF, PNG, or JPEG file.";
  }
  if (status === 422) {
    return fallbackDetail || "Invalid request options. Please check your selected languages and file.";
  }
  if (status === 429) {
    return "Too many requests right now. Please wait a moment and try again.";
  }
  if (status >= 500) {
    return fallbackDetail || "The server encountered an error while analyzing the document. Please try again.";
  }

  return fallbackDetail || "An unexpected error occurred while processing the document.";
}

export async function fetchJson(path, options = {}) {
  const response = await fetch(apiUrl(path), {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.headers || {}),
    },
  });

  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json")
    ? await response.json()
    : null;

  if (!response.ok) {
    const detail =
      (data && (data.detail || data.message || data.error)) ||
      `Request failed with status ${response.status}`;
    const error = new Error(
      typeof detail === "string" ? detail : JSON.stringify(detail)
    );
    error.status = response.status;
    error.payload = data;
    throw error;
  }

  return data;
}