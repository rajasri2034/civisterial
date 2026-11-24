import React from "react";

function tierBadgeLabel(tier) {
  if (tier === "verified") return "Verified";
  if (tier === "experimental") return "Experimental";
  return "Unavailable";
}

export function LanguageSelector({
  languages,
  documentLanguage,
  explanationLanguage,
  detectedLabel,
  detectionUncertain,
  onDocumentLanguageChange,
  onExplanationLanguageChange,
}) {
  const selectedExp = languages.find((l) => l.code === explanationLanguage);
  const selectedDoc =
    documentLanguage === "auto"
      ? null
      : languages.find((l) => l.code === documentLanguage);

  const isExplanationUnsupported =
    Boolean(explanationLanguage) &&
    (!selectedExp ||
      selectedExp.tier === "unavailable" ||
      !selectedExp.supports_explanation_output);

  const isDocumentUnsupported =
    documentLanguage !== "auto" &&
    (!selectedDoc ||
      selectedDoc.tier === "unavailable" ||
      !selectedDoc.supports_document_input);

  return (
    <section aria-labelledby="language-settings-heading">
      <h2 id="language-settings-heading">Language settings</h2>
      <p className="gov-inset">
        Quotes are shown in the original language. Explanations are provided in your selected language.
      </p>

      <div className="gov-language-grid">
        <div className="gov-form-group">
          <label className="gov-label" htmlFor="doc-lang-select">
            Document language
          </label>
          <span className="gov-hint" id="doc-lang-hint">
            Auto-detect runs first, or choose the document language manually.
          </span>
          <select
            id="doc-lang-select"
            className="gov-select"
            aria-describedby="doc-lang-hint"
            value={documentLanguage}
            onChange={(e) => onDocumentLanguageChange(e.target.value)}
          >
            <option value="auto">Auto-detect (default)</option>
            {languages.map((lang) => (
              <option key={lang.code} value={lang.code}>
                {lang.name} ({lang.native_name}) — [{tierBadgeLabel(lang.tier)}]
              </option>
            ))}
          </select>

          {detectedLabel && (
            <p style={{ marginTop: "0.5rem", marginBottom: 0 }}>
              <strong>Detected document language:</strong> {detectedLabel}
              {detectionUncertain && (
                <>
                  {" "}
                  <span className="gov-tag gov-tag--amber">
                    Uncertain detection — verify or select manually
                  </span>
                </>
              )}
            </p>
          )}

          {isDocumentUnsupported && (
            <div className="gov-warning-banner" role="alert">
              <strong>Selected document language is unavailable:</strong>{" "}
              {selectedDoc
                ? `${selectedDoc.name} (${selectedDoc.native_name}) is marked unavailable.`
                : `"${documentLanguage}" is not supported.`}{" "}
              Civisterial will not silently fall back to English. Please select Auto-detect or another supported language.
            </div>
          )}
        </div>

        <div className="gov-form-group">
          <label className="gov-label" htmlFor="exp-lang-select">
            Explanation language
          </label>
          <span className="gov-hint" id="exp-lang-hint">
            Choose the language for plain-language explanations, checklist tasks, and exports.
          </span>
          <select
            id="exp-lang-select"
            className="gov-select"
            aria-describedby="exp-lang-hint"
            value={explanationLanguage}
            onChange={(e) => onExplanationLanguageChange(e.target.value)}
          >
            {languages.map((lang) => (
              <option key={lang.code} value={lang.code}>
                {lang.name} ({lang.native_name}) — [{tierBadgeLabel(lang.tier)}]
              </option>
            ))}
          </select>

          {selectedExp && selectedExp.tier === "experimental" && (
            <p style={{ marginTop: "0.5rem", marginBottom: 0 }}>
              <span className="gov-tag gov-tag--amber">Experimental language</span>{" "}
              {selectedExp.notes}
            </p>
          )}

          {isExplanationUnsupported && (
            <div className="gov-warning-banner" role="alert">
              <strong>Selected explanation language is unsupported:</strong>{" "}
              {selectedExp
                ? `${selectedExp.name} (${selectedExp.native_name}) is currently unavailable.`
                : `"${explanationLanguage}" is not supported.`}{" "}
              Civisterial will not silently fall back to English. Please select another supported language.
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

export default LanguageSelector;