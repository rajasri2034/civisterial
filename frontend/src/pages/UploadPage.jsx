import React, { useRef, useState } from "react";
import { LanguageSelector } from "../components/LanguageSelector";

const MAX_BYTES = 10 * 1024 * 1024;
const ALLOWED_MIME = new Set(["application/pdf", "image/png", "image/jpeg"]);

export function UploadPage({
  languages,
  documentLanguage,
  explanationLanguage,
  onDocumentLanguageChange,
  onExplanationLanguageChange,
  onAnalysisComplete,
  onCancelWorkflow,
}) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [errors, setErrors] = useState([]);
  const [stage, setStage] = useState("idle");
  const [statusMessage, setStatusMessage] = useState("");
  const [inspection, setInspection] = useState(null);
  const [awaitingImageConfirm, setAwaitingImageConfirm] = useState(false);

  const abortRef = useRef(null);
  const errorSummaryRef = useRef(null);

  const reportErrors = (errs) => {
    setErrors(errs);
    setStage("idle");
    setStatusMessage("");
    requestAnimationFrame(() => {
      errorSummaryRef.current?.focus();
    });
  };

  const validateClientInputs = (file) => {
    const issues = [];
    if (!file) {
      issues.push("Select a PDF, PNG, or JPEG document to upload.");
    } else {
      const lowerName = file.name.toLowerCase();
      const validExt =
        lowerName.endsWith(".pdf") ||
        lowerName.endsWith(".png") ||
        lowerName.endsWith(".jpg") ||
        lowerName.endsWith(".jpeg");
      if (!ALLOWED_MIME.has(file.type) && !validExt) {
        issues.push("The selected file must be a PDF, PNG, or JPEG.");
      }
      if (file.size === 0) {
        issues.push("The selected file is empty.");
      } else if (file.size > MAX_BYTES) {
        issues.push("The selected file must be smaller than 10 MB.");
      }
    }

    const expLangObj = languages.find((l) => l.code === explanationLanguage);
    if (
      !expLangObj ||
      expLangObj.tier === "unavailable" ||
      !expLangObj.supports_explanation_output
    ) {
      issues.push(
        "The selected explanation language is unsupported. Choose another supported language."
      );
    }

    if (documentLanguage !== "auto") {
      const docLangObj = languages.find((l) => l.code === documentLanguage);
      if (
        !docLangObj ||
        docLangObj.tier === "unavailable" ||
        !docLangObj.supports_document_input
      ) {
        issues.push(
          "The selected document language is unsupported. Choose Auto-detect or another supported language."
        );
      }
    }

    return issues;
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0] ?? null;
    setSelectedFile(file);
    setInspection(null);
    setAwaitingImageConfirm(false);
    setErrors([]);
  };

  const handleCancelActiveRequest = () => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setStage("idle");
    setAwaitingImageConfirm(false);
    setStatusMessage("Analysis cancelled.");
    onCancelWorkflow();
  };

  const runFullAnalysis = async (file, confirmedPublicOrSynthetic) => {
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      setStage("analysing");
      setStatusMessage("Stage 2 of 3: Analysing document in your selected language...");

      const formData = new FormData();
      formData.append("file", file);
      formData.append("document_language", documentLanguage);
      formData.append("explanation_language", explanationLanguage);
      if (confirmedPublicOrSynthetic) {
        formData.append(
          "image_confirmation",
          "I confirm this is a public or synthetic document"
        );
      }

      const analyzeRes = await fetch("/api/analyze", {
        method: "POST",
        body: formData,
        signal: controller.signal,
      });

      setStage("checking");
      setStatusMessage("Stage 3 of 3: Checking quotations against the document...");

      if (!analyzeRes.ok) {
        const errBody = await analyzeRes.json().catch(() => ({}));
        reportErrors([errBody.error || "Unable to analyse the uploaded document."]);
        return;
      }

      const data = await analyzeRes.json();
      setStage("idle");
      setStatusMessage("Analysis complete.");
      onAnalysisComplete(data);
    } catch (err) {
      if (err?.name === "AbortError") {
        return;
      }
      reportErrors(["A network error occurred while analysing the document."]);
    } finally {
      abortRef.current = null;
    }
  };

  const handleInspectAndSubmit = async (e) => {
    e.preventDefault();
    const validationErrors = validateClientInputs(selectedFile);
    if (validationErrors.length > 0 || !selectedFile) {
      reportErrors(validationErrors);
      return;
    }

    setErrors([]);
    setAwaitingImageConfirm(false);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      setStage("reading");
      setStatusMessage("Stage 1 of 3: Reading file and detecting document language...");

      const formData = new FormData();
      formData.append("file", selectedFile);

      const inspectRes = await fetch("/api/inspect", {
        method: "POST",
        body: formData,
        signal: controller.signal,
      });

      if (!inspectRes.ok) {
        const errBody = await inspectRes.json().catch(() => ({}));
        reportErrors([errBody.error || "Unable to read the uploaded file."]);
        return;
      }

      const inspected = await inspectRes.json();
      setInspection(inspected);

      if (inspected.has_image_based_content) {
        setStage("idle");
        setAwaitingImageConfirm(true);
        setStatusMessage(
          "Image-based content detected. Confirmation required before sending."
        );
        return;
      }

      await runFullAnalysis(selectedFile, false);
    } catch (err) {
      if (err?.name === "AbortError") {
        return;
      }
      reportErrors(["A network error occurred while reading the document."]);
    }
  };

  return (
    <div>
      <h1>Upload a document</h1>

      {errors.length > 0 && (
        <div
          ref={errorSummaryRef}
          className="gov-error-summary"
          role="alert"
          tabIndex={-1}
          aria-labelledby="error-summary-title"
        >
          <h2 id="error-summary-title" className="gov-error-summary__title">
            There is a problem
          </h2>
          <ul style={{ margin: 0, paddingInlineStart: "1.25rem" }}>
            {errors.map((err, i) => (
              <li key={i}>{err}</li>
            ))}
          </ul>
        </div>
      )}

      <LanguageSelector
        languages={languages}
        documentLanguage={documentLanguage}
        explanationLanguage={explanationLanguage}
        detectedLabel={inspection?.detected_language_label ?? null}
        detectionUncertain={inspection?.language_detection_uncertain ?? false}
        onDocumentLanguageChange={onDocumentLanguageChange}
        onExplanationLanguageChange={onExplanationLanguageChange}
      />

      <form onSubmit={handleInspectAndSubmit} noValidate>
        <div className="gov-form-group">
          <label className="gov-label" htmlFor="document-file-input">
            Upload a file
          </label>
          <span className="gov-hint" id="file-upload-hint">
            Accepted file types: PDF, PNG, or JPEG. Maximum file size: 10 MB.
          </span>
          <input
            id="document-file-input"
            name="file"
            type="file"
            className="gov-file-input"
            accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
            aria-describedby="file-upload-hint"
            onChange={handleFileChange}
            disabled={stage !== "idle"}
          />
        </div>

        <ol className="gov-steps" aria-label="Analysis stages">
          <li
            className={`gov-steps__item ${
              stage === "reading"
                ? "gov-steps__item--active"
                : stage === "analysing" || stage === "checking"
                ? "gov-steps__item--done"
                : ""
            }`}
          >
            1. Reading
          </li>
          <li
            className={`gov-steps__item ${
              stage === "analysing"
                ? "gov-steps__item--active"
                : stage === "checking"
                ? "gov-steps__item--done"
                : ""
            }`}
          >
            2. Analysing
          </li>
          <li
            className={`gov-steps__item ${
              stage === "checking" ? "gov-steps__item--active" : ""
            }`}
          >
            3. Checking quotations
          </li>
        </ol>

        <div aria-live="polite" className="gov-inset" style={{ minHeight: "3rem" }}>
          {statusMessage || "Ready to read your document."}
        </div>

        {awaitingImageConfirm && selectedFile && (
          <div className="gov-warning-banner" role="region" aria-label="Image confirmation required">
            <h2 style={{ marginTop: 0, fontSize: "1.2rem" }}>Confirm before sending images</h2>
            <p>
              Personal details in images are not hidden before analysis. Only continue with a public or sample document.
            </p>
            <p>
              By selecting Continue, you declare that this upload is a public or synthetic document for this MVP.
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem" }}>
              <button
                type="button"
                className="gov-button"
                onClick={() => {
                  setAwaitingImageConfirm(false);
                  void runFullAnalysis(selectedFile, true);
                }}
              >
                Continue
              </button>
              <button
                type="button"
                className="gov-button gov-button--secondary"
                onClick={handleCancelActiveRequest}
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {!awaitingImageConfirm && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem" }}>
            <button type="submit" className="gov-button" disabled={stage !== "idle"}>
              Analyse document
            </button>
            <button
              type="button"
              className="gov-button gov-button--secondary"
              onClick={handleCancelActiveRequest}
            >
              Cancel
            </button>
          </div>
        )}
      </form>
    </div>
  );
}