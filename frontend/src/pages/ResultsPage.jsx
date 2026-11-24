import React, { useState } from "react";
import { QuotationStatusBadge } from "../components/QuotationStatusBadge";
import { getUiCopyForLanguage } from "../config/languages";
import { buildExportText, downloadTextFile } from "../utils/exportTxt";

export function ResultsPage({
  result,
  checkedTasks,
  onToggleTask,
  onDeleteResults,
  onStartNewAnalysis,
}) {
  const [activeTab, setActiveTab] = useState("overview");
  const [statusFilter, setStatusFilter] = useState("all");

  const { analysis } = result;
  const copy = getUiCopyForLanguage(result.explanation_language);
  const completedCount = analysis.action_steps.filter((_, idx) => Boolean(checkedTasks[idx])).length;

  const formatPage = (page, actualPage) => {
    const resolved = actualPage ?? page;
    return resolved !== null && resolved !== undefined ? `Page ${resolved}` : "page unknown";
  };

  const allEvidenceRows = [];

  analysis.simplified_passages.forEach((p) => {
    allEvidenceRows.push({
      category: "Simplified passage",
      originalQuote: p.original,
      explanation: p.simplified,
      pageDisplay: formatPage(p.page, p.actual_page),
      status: p.quotation_status,
      claimNote: p.claim_note,
      pageCorrected: p.page_corrected,
      pageNote: p.page_note,
    });
  });

  analysis.action_steps.forEach((s) => {
    allEvidenceRows.push({
      category: "Action step",
      originalQuote: s.evidence,
      explanation: `${s.task}: ${s.description}`,
      pageDisplay: formatPage(s.page, s.actual_page),
      status: s.quotation_status,
      claimNote: s.claim_note,
      pageCorrected: s.page_corrected,
      pageNote: s.page_note,
    });
  });

  analysis.deadlines.forEach((d) => {
    if (d.evidence) {
      allEvidenceRows.push({
        category: "Deadline",
        originalQuote: d.evidence,
        explanation: `${d.description} (${d.date_text})`,
        pageDisplay: formatPage(d.page, d.actual_page),
        status: d.quotation_status,
        claimNote: d.claim_note,
        pageCorrected: d.page_corrected,
        pageNote: d.page_note,
      });
    }
  });

  analysis.fees.forEach((f) => {
    if (f.evidence) {
      allEvidenceRows.push({
        category: "Fee",
        originalQuote: f.evidence,
        explanation: `${f.purpose}: ${f.amount}`,
        pageDisplay: formatPage(f.page, f.actual_page),
        status: f.quotation_status,
        claimNote: f.claim_note,
        pageCorrected: f.page_corrected,
        pageNote: f.page_note,
      });
    }
  });

  analysis.requirements.forEach((r) => {
    allEvidenceRows.push({
      category: `Requirement (${r.status})`,
      originalQuote: r.evidence,
      explanation: r.item,
      pageDisplay: formatPage(r.page, r.actual_page),
      status: r.quotation_status,
      claimNote: r.claim_note,
      pageCorrected: r.page_corrected,
      pageNote: r.page_note,
    });
  });

  const verifiableEvidence = allEvidenceRows.filter((row) => row.status !== "not_found");
  const unverifiedEvidence = allEvidenceRows.filter((row) => row.status === "not_found");

  const filteredVerifiable =
    statusFilter === "all"
      ? verifiableEvidence
      : verifiableEvidence.filter((row) => row.status === statusFilter);

  const handleDownloadTxt = () => {
    const content = buildExportText(result, checkedTasks);
    downloadTextFile(`civisterial-summary-${result.request_id.slice(0, 8)}.txt`, content);
  };

  return (
    <div dir={result.explanation_direction} lang={result.explanation_language}>
      <h1>Document analysis results</h1>

      <div
        className="no-print"
        style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem", marginBottom: "1.5rem" }}
      >
        <button type="button" className="gov-button" onClick={handleDownloadTxt}>
          {copy.downloadTxt}
        </button>
        <button
          type="button"
          className="gov-button gov-button--secondary"
          onClick={() => window.print()}
        >
          {copy.printA4}
        </button>
        <button
          type="button"
          className="gov-button gov-button--secondary"
          onClick={onStartNewAnalysis}
        >
          Start new analysis
        </button>
        <button
          type="button"
          className="gov-button gov-button--warning"
          onClick={onDeleteResults}
        >
          {copy.deleteMyResults}
        </button>
      </div>

      {analysis.warnings.length > 0 && (
        <div className="gov-warning-banner" role="region" aria-label="Document warnings">
          <h2 style={{ marginTop: 0, fontSize: "1.15rem" }}>Important notices</h2>
          <ul style={{ margin: 0, paddingInlineStart: "1.25rem" }}>
            {analysis.warnings.map((w, idx) => (
              <li key={idx}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div role="tablist" aria-label="Analysis sections" className="gov-tabs__list no-print">
        {[
          ["overview", copy.tabs.overview],
          ["simplified", copy.tabs.simplified],
          ["actionPlan", copy.tabs.actionPlan],
          ["deadlinesRequirements", copy.tabs.deadlinesRequirements],
          ["evidence", copy.tabs.evidence],
        ].map(([key, label]) => (
          <button
            key={key}
            type="button"
            role="tab"
            id={`tab-${key}`}
            aria-selected={activeTab === key}
            aria-controls={`panel-${key}`}
            className="gov-tabs__tab"
            onClick={() => setActiveTab(key)}
          >
            {label}
          </button>
        ))}
      </div>

      {activeTab === "overview" && (
        <section
          id="panel-overview"
          role="tabpanel"
          aria-labelledby="tab-overview"
          className="gov-tabs__panel"
        >
          <h2>{copy.tabs.overview}</h2>
          <p style={{ fontSize: "1.15rem" }}>{analysis.summary}</p>

          <dl className="gov-summary-list">
            <div className="gov-summary-list__row">
              <dt className="gov-summary-list__key">Document title</dt>
              <dd className="gov-summary-list__value">
                {analysis.document_title.value === "Not stated in the document."
                  ? "NOT_STATED — Not stated in the document."
                  : analysis.document_title.value}{" "}
                {analysis.document_title.evidence && (
                  <QuotationStatusBadge status={analysis.document_title.quotation_status} />
                )}
              </dd>
            </div>
            <div className="gov-summary-list__row">
              <dt className="gov-summary-list__key">Issuing authority</dt>
              <dd className="gov-summary-list__value">
                {analysis.issuing_authority.value === "Not stated in the document."
                  ? "NOT_STATED — Not stated in the document."
                  : analysis.issuing_authority.value}{" "}
                {analysis.issuing_authority.evidence && (
                  <QuotationStatusBadge status={analysis.issuing_authority.quotation_status} />
                )}
              </dd>
            </div>
            <div className="gov-summary-list__row">
              <dt className="gov-summary-list__key">Document type</dt>
              <dd className="gov-summary-list__value">
                {analysis.document_type.value === "Not stated in the document."
                  ? "NOT_STATED — Not stated in the document."
                  : analysis.document_type.value}{" "}
                {analysis.document_type.evidence && (
                  <QuotationStatusBadge status={analysis.document_type.quotation_status} />
                )}
              </dd>
            </div>
            <div className="gov-summary-list__row">
              <dt className="gov-summary-list__key">Readability</dt>
              <dd className="gov-summary-list__value">{analysis.readability}</dd>
            </div>
            <div className="gov-summary-list__row">
              <dt className="gov-summary-list__key">Detected document language</dt>
              <dd className="gov-summary-list__value">{result.detected_language_label}</dd>
            </div>
            <div className="gov-summary-list__row">
              <dt className="gov-summary-list__key">Explanation language</dt>
              <dd className="gov-summary-list__value">{result.explanation_language}</dd>
            </div>
            <div className="gov-summary-list__row">
              <dt className="gov-summary-list__key">Missing information</dt>
              <dd className="gov-summary-list__value">
                {analysis.missing_information.length === 0 ? (
                  "NOT_STATED"
                ) : (
                  <ul style={{ margin: 0, paddingInlineStart: "1.25rem" }}>
                    {analysis.missing_information.map((m, idx) => (
                      <li key={idx}>{m}</li>
                    ))}
                  </ul>
                )}
              </dd>
            </div>
          </dl>
        </section>
      )}

      {activeTab === "simplified" && (
        <section
          id="panel-simplified"
          role="tabpanel"
          aria-labelledby="tab-simplified"
          className="gov-tabs__panel"
        >
          <h2>{copy.tabs.simplified}</h2>
          <p className="gov-inset">{copy.interpretationForUserNote}</p>

          {analysis.simplified_passages.length === 0 ? (
            <p>NOT_STATED — No simplified passages were extracted.</p>
          ) : (
            <div className="gov-table-wrap">
              <table className="gov-table">
                <thead>
                  <tr>
                    <th scope="col">Original document quotation</th>
                    <th scope="col">Plain-language explanation</th>
                    <th scope="col">Page &amp; status</th>
                  </tr>
                </thead>
                <tbody>
                  {analysis.simplified_passages.map((passage, idx) => (
                    <tr key={idx}>
                      <td>
                        <blockquote className="gov-quote" dir="auto">
                          {passage.original}
                        </blockquote>
                      </td>
                      <td>
                        <p>{passage.simplified}</p>
                        <small>{copy.interpretationForUserNote}</small>
                      </td>
                      <td>
                        <div>{formatPage(passage.page, passage.actual_page)}</div>
                        <div style={{ marginTop: "0.35rem" }}>
                          <QuotationStatusBadge status={passage.quotation_status} />
                        </div>
                        {passage.page_corrected && (
                          <div style={{ marginTop: "0.35rem" }}>
                            <span className="gov-tag gov-tag--blue">Page reference corrected</span>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {activeTab === "actionPlan" && (
        <section
          id="panel-actionPlan"
          role="tabpanel"
          aria-labelledby="tab-actionPlan"
          className="gov-tabs__panel"
        >
          <h2>{copy.tabs.actionPlan}</h2>

          <div className="gov-warning-banner" role="status">
            <strong>{copy.checklistNotSavedWarning}</strong>
          </div>

          <p>
            <strong>
              Completed {completedCount} of {analysis.action_steps.length} tasks
            </strong>
          </p>

          {analysis.action_steps.length === 0 ? (
            <p>NOT_STATED — No action steps were stated in the document.</p>
          ) : (
            <ul className="gov-task-list">
              {analysis.action_steps.map((step, idx) => {
                const checkboxId = `action-task-${idx}`;
                return (
                  <li key={idx} className="gov-task-list__item">
                    <input
                      id={checkboxId}
                      type="checkbox"
                      className="gov-task-list__checkbox"
                      checked={Boolean(checkedTasks[idx])}
                      onChange={() => onToggleTask(idx)}
                    />
                    <div>
                      <label htmlFor={checkboxId} style={{ fontWeight: 700, cursor: "pointer" }}>
                        {step.task}
                      </label>
                      <p style={{ marginTop: "0.25rem" }}>{step.description}</p>
                      <p style={{ marginBottom: "0.25rem", fontSize: "0.9rem" }}>
                        <span className="gov-tag gov-tag--grey">
                          {step.ordering === "stated_in_document"
                            ? "Order stated in document"
                            : "AI-organised order"}
                        </span>{" "}
                        <QuotationStatusBadge status={step.quotation_status} />{" "}
                        <span>({formatPage(step.page, step.actual_page)})</span>
                      </p>
                      <small>{copy.interpretationForUserNote}</small>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      )}

      {activeTab === "deadlinesRequirements" && (
        <section
          id="panel-deadlinesRequirements"
          role="tabpanel"
          aria-labelledby="tab-deadlinesRequirements"
          className="gov-tabs__panel"
        >
          <h2>Deadlines</h2>
          {analysis.deadlines.length === 0 ? (
            <p>NO_DEADLINE</p>
          ) : (
            <div className="gov-table-wrap">
              <table className="gov-table">
                <thead>
                  <tr>
                    <th scope="col">Description</th>
                    <th scope="col">Date stated</th>
                    <th scope="col">Quotation &amp; check</th>
                  </tr>
                </thead>
                <tbody>
                  {analysis.deadlines.map((d, idx) => (
                    <tr key={idx}>
                      <td>{d.description}</td>
                      <td>
                        <strong>{d.date_text}</strong>
                        {d.ambiguous && (
                          <div style={{ marginTop: "0.35rem" }}>
                            <span className="gov-tag gov-tag--amber">
                              {copy.ambiguousDateWarning}
                            </span>
                          </div>
                        )}
                      </td>
                      <td>
                        <QuotationStatusBadge status={d.quotation_status} />
                        {d.claim_note && <p style={{ marginTop: "0.35rem" }}>{d.claim_note}</p>}
                        {d.evidence && (
                          <blockquote className="gov-quote" dir="auto">
                            {d.evidence}
                          </blockquote>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <h2>Fees</h2>
          {analysis.fees.length === 0 ? (
            <p>NO_FEE</p>
          ) : (
            <div className="gov-table-wrap">
              <table className="gov-table">
                <thead>
                  <tr>
                    <th scope="col">Purpose</th>
                    <th scope="col">Amount</th>
                    <th scope="col">Quotation &amp; check</th>
                  </tr>
                </thead>
                <tbody>
                  {analysis.fees.map((f, idx) => (
                    <tr key={idx}>
                      <td>{f.purpose}</td>
                      <td>
                        <strong>{f.amount}</strong>
                      </td>
                      <td>
                        <QuotationStatusBadge status={f.quotation_status} />
                        {f.claim_note && <p style={{ marginTop: "0.35rem" }}>{f.claim_note}</p>}
                        {f.evidence && (
                          <blockquote className="gov-quote" dir="auto">
                            {f.evidence}
                          </blockquote>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <h2>Requirements</h2>
          {analysis.requirements.length === 0 ? (
            <p>NOT_STATED</p>
          ) : (
            <div className="gov-table-wrap">
              <table className="gov-table">
                <thead>
                  <tr>
                    <th scope="col">Requirement</th>
                    <th scope="col">Status</th>
                    <th scope="col">Quotation &amp; check</th>
                  </tr>
                </thead>
                <tbody>
                  {analysis.requirements.map((r, idx) => (
                    <tr key={idx}>
                      <td>{r.item}</td>
                      <td>
                        <span
                          className={`gov-tag ${
                            r.status === "mandatory"
                              ? "gov-tag--blue"
                              : r.status === "optional"
                              ? "gov-tag--grey"
                              : "gov-tag--amber"
                          }`}
                        >
                          {r.status}
                        </span>
                      </td>
                      <td>
                        <QuotationStatusBadge status={r.quotation_status} />
                        {r.claim_note && <p style={{ marginTop: "0.35rem" }}>{r.claim_note}</p>}
                        <blockquote className="gov-quote" dir="auto">
                          {r.evidence}
                        </blockquote>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {activeTab === "evidence" && (
        <section
          id="panel-evidence"
          role="tabpanel"
          aria-labelledby="tab-evidence"
          className="gov-tabs__panel"
        >
          <h2>{copy.tabs.evidence}</h2>
          <p className="gov-inset">
            <strong>{copy.evidenceDisclaimer}</strong>
          </p>

          <div className="gov-form-group no-print">
            <label className="gov-label" htmlFor="evidence-status-filter">
              Filter by quotation status
            </label>
            <select
              id="evidence-status-filter"
              className="gov-select"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">All matched and review items ({verifiableEvidence.length})</option>
              <option value="exact_quotation_found">Exact quotation found</option>
              <option value="possible_match">Possible match: review required</option>
              <option value="needs_user_verification">Needs user verification</option>
            </select>
          </div>

          {filteredVerifiable.length === 0 ? (
            <p>NOT_STATED — No evidence items match the selected filter.</p>
          ) : (
            <div className="gov-table-wrap">
              <table className="gov-table">
                <thead>
                  <tr>
                    <th scope="col">Original document passage</th>
                    <th scope="col">Explanation</th>
                    <th scope="col">Page &amp; quotation status</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredVerifiable.map((row, idx) => (
                    <tr key={idx}>
                      <td>
                        <small>{row.category}</small>
                        <blockquote className="gov-quote" dir="auto">
                          {row.originalQuote}
                        </blockquote>
                      </td>
                      <td>{row.explanation}</td>
                      <td>
                        <div>{row.pageDisplay}</div>
                        <div style={{ marginTop: "0.35rem" }}>
                          <QuotationStatusBadge status={row.status} />
                        </div>
                        {row.pageCorrected && (
                          <div style={{ marginTop: "0.35rem" }}>
                            <span className="gov-tag gov-tag--blue">Page reference corrected</span>
                            {row.pageNote && <p style={{ marginTop: "0.25rem" }}>{row.pageNote}</p>}
                          </div>
                        )}
                        {row.claimNote && <p style={{ marginTop: "0.35rem" }}>{row.claimNote}</p>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {unverifiedEvidence.length > 0 && (
            <details className="gov-details">
              <summary>Could not verify ({unverifiedEvidence.length})</summary>
              <div className="gov-table-wrap">
                <table className="gov-table">
                  <thead>
                    <tr>
                      <th scope="col">Unmatched quotation</th>
                      <th scope="col">Explanation</th>
                      <th scope="col">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {unverifiedEvidence.map((row, idx) => (
                      <tr key={idx}>
                        <td>
                          <blockquote className="gov-quote" dir="auto">
                            {row.originalQuote}
                          </blockquote>
                        </td>
                        <td>{row.explanation}</td>
                        <td>
                          <QuotationStatusBadge status={row.status} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          )}
        </section>
      )}
    </div>
  );
}