import React, { useState } from "react";

function tierBadgeLabel(tier) {
  return tier === "validated" ? "Verified check" : "Beta translation";
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
  const [filterText, setFilterText] = useState("");

  const query = filterText.trim().toLowerCase();
  const filteredLanguages = query
    ? languages.filter(
        (l) =>
          l.name.toLowerCase().includes(query) ||
          l.native_name.toLowerCase().includes(query) ||
          l.code.toLowerCase().includes(query)
      )
    : languages;

  // Always keep currently selected language visible in dropdown even when filtering
  const ensureSelectedIncluded = (selectedCode) => {
    if (!selectedCode || selectedCode === "auto") return filteredLanguages;
    const exists = filteredLanguages.some((l) => l.code === selectedCode);
    if (exists) return filteredLanguages;
    const found = languages.find((l) => l.code === selectedCode);
    return found ? [found, ...filteredLanguages] : filteredLanguages;
  };

  const docOptions = ensureSelectedIncluded(documentLanguage);
  const expOptions = ensureSelectedIncluded(explanationLanguage);

  const selectedExp = languages.find((l) => l.code === explanationLanguage);

  return (
    <section aria-labelledby="language-settings-heading">
      <h2 id="language-settings-heading">Language settings</h2>

      <div className="gov-inset" role="note">
        <p style={{ marginTop: 0 }}>
          <strong>
            Civisterial can generate explanations in any language supported by Gemini. Full automated claim-checking is currently calibrated for English, Tamil, and Hindi; other languages show exact quote verification and require manual review of deadlines and mandatory terms.
          </strong>
        </p>
        <p style={{ marginBottom: 0 }}>
          Quotes are always preserved verbatim in the document&apos;s original language.
        </p>
      </div>

      <div className="gov-form-group">
        <label className="gov-label" htmlFor="language-search-input">
          Filter languages (by English name, native script, or BCP-47 code)
        </label>
        <input
          id="language-search-input"
          type="text"
          className="gov-file-input"
          placeholder="e.g., Tamil, தமிழ், Hindi, French, te, ar..."
          value={filterText}
          onChange={(e) => setFilterText(e.target.value)}
        />
      </div>

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
            {docOptions.map((lang) => (
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
            {expOptions.map((lang) => (
              <option key={lang.code} value={lang.code}>
                {lang.name} ({lang.native_name}) — [{tierBadgeLabel(lang.tier)}]
              </option>
            ))}
          </select>

          {selectedExp && (
            <p style={{ marginTop: "0.5rem", marginBottom: 0 }}>
              <span
                className={`gov-tag ${
                  selectedExp.tier === "validated" ? "gov-tag--green" : "gov-tag--amber"
                }`}
              >
                {tierBadgeLabel(selectedExp.tier)}
              </span>{" "}
              {selectedExp.notes}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}

export default LanguageSelector;