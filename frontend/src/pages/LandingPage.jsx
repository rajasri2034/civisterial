import React from "react";

export function LandingPage({ onStart }) {
  return (
    <div>
      <h1>Civisterial</h1>
      <p style={{ fontSize: "1.25rem" }}>
        Understand government letters, notices, and forms in plain language while checking every detail against exact quotations from your document.
      </p>

      <button type="button" className="gov-button" onClick={onStart}>
        Start now
      </button>

      <h2>How it works</h2>
      <ol style={{ paddingInlineStart: "1.5rem", maxWidth: "65ch" }}>
        <li style={{ marginBottom: "0.75rem" }}>
          <strong>Choose your languages:</strong> Keep automatic document language detection or select the document language manually, and pick your preferred explanation language independently.
        </li>
        <li style={{ marginBottom: "0.75rem" }}>
          <strong>Upload your document:</strong> Select a PDF, PNG, or JPEG file up to 10 MB.
        </li>
        <li style={{ marginBottom: "0.75rem" }}>
          <strong>Automatic text redaction &amp; image check:</strong> Personal identifiers in PDF text are masked in memory before AI processing, and image pages require your explicit confirmation.
        </li>
        <li style={{ marginBottom: "0.75rem" }}>
          <strong>Plain-language breakdown:</strong> Read a clear overview, simplified passages, action checklist, deadlines, and fees in your chosen language.
        </li>
        <li style={{ marginBottom: "0.75rem" }}>
          <strong>Check exact quotations &amp; export:</strong> Compare every item against the original document quote, then download a .txt summary or print an A4 copy before leaving.
        </li>
      </ol>

      <div className="gov-warning-banner" role="region" aria-label="Privacy and accuracy notice">
        <h2 style={{ marginTop: 0, fontSize: "1.2rem" }}>Privacy and accuracy notice</h2>
        <p style={{ marginBottom: 0 }}>
          Content is sent to Google Gemini for analysis. Nothing is stored by Civisterial. Images are not redacted. Use public or synthetic documents only for this beta.
        </p>
      </div>
    </div>
  );
}