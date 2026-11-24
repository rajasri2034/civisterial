function exactStatusText(status) {
  switch (status) {
    case "exact_quotation_found":
      return "Exact quotation found";
    case "possible_match":
      return "Possible match: review required";
    case "not_found":
      return "Not found";
    default:
      return "Needs user verification";
  }
}

export function buildExportText(result, checkedTasks) {
  const { analysis } = result;
  const lines = [
    "CIVISTERIAL — PLAIN-LANGUAGE ADMINISTRATIVE DOCUMENT SUMMARY",
    "============================================================",
    `Disclaimer: ${result.disclaimer}`,
    "Evidence notice: This shows the quotation exists in your document. It does not confirm our explanation is correct.",
    `Document language: ${result.document_language} (${result.detected_language_label})`,
    `Explanation language: ${result.explanation_language}`,
    `Readability: ${analysis.readability}`,
    "",
    "1. OVERVIEW",
    "-----------",
    `Document title: ${analysis.document_title.value} [${exactStatusText(analysis.document_title.quotation_status)}]`,
    `Issuing authority: ${analysis.issuing_authority.value} [${exactStatusText(analysis.issuing_authority.quotation_status)}]`,
    `Document type: ${analysis.document_type.value} [${exactStatusText(analysis.document_type.quotation_status)}]`,
    "",
    "Summary:",
    analysis.summary,
    "",
    "2. SIMPLIFIED PASSAGES",
    "----------------------",
  ];

  if (analysis.simplified_passages.length === 0) {
    lines.push("NOT_STATED");
  } else {
    analysis.simplified_passages.forEach((p, idx) => {
      lines.push(
        `[${idx + 1}] Page: ${p.actual_page ?? p.page ?? "page unknown"} | Status: ${exactStatusText(p.quotation_status)}`
      );
      lines.push(`    Original quote: "${p.original}"`);
      lines.push(`    Simplified explanation: ${p.simplified}`);
    });
  }

  lines.push("", "3. ACTION PLAN & CHECKLIST", "--------------------------");
  if (analysis.action_steps.length === 0) {
    lines.push("NOT_STATED");
  } else {
    analysis.action_steps.forEach((step, idx) => {
      const mark = checkedTasks[idx] ? "[x]" : "[ ]";
      lines.push(
        `${mark} ${idx + 1}. ${step.task} (${step.ordering}) — ${step.description}`
      );
      lines.push(
        `    Page: ${step.actual_page ?? step.page ?? "page unknown"} | Status: ${exactStatusText(step.quotation_status)}`
      );
      lines.push(`    Original quote: "${step.evidence}"`);
    });
  }

  lines.push("", "4. DEADLINES", "------------");
  if (analysis.deadlines.length === 0) {
    lines.push("NO_DEADLINE");
  } else {
    analysis.deadlines.forEach((d, idx) => {
      const amb = d.ambiguous ? " [Please confirm this date]" : "";
      lines.push(
        `[${idx + 1}] ${d.description}: ${d.date_text}${amb} | Status: ${exactStatusText(d.quotation_status)}`
      );
      if (d.evidence) {
        lines.push(`    Original quote: "${d.evidence}"`);
      }
    });
  }

  lines.push("", "5. FEES", "-------");
  if (analysis.fees.length === 0) {
    lines.push("NO_FEE");
  } else {
    analysis.fees.forEach((f, idx) => {
      lines.push(
        `[${idx + 1}] ${f.purpose}: ${f.amount} | Status: ${exactStatusText(f.quotation_status)}`
      );
      if (f.evidence) {
        lines.push(`    Original quote: "${f.evidence}"`);
      }
    });
  }

  lines.push("", "6. REQUIREMENTS", "---------------");
  if (analysis.requirements.length === 0) {
    lines.push("NOT_STATED");
  } else {
    analysis.requirements.forEach((r, idx) => {
      lines.push(
        `[${idx + 1}] [${r.status.toUpperCase()}] ${r.item} | Status: ${exactStatusText(r.quotation_status)}`
      );
      lines.push(`    Original quote: "${r.evidence}"`);
    });
  }

  lines.push("", "7. MISSING INFORMATION & WARNINGS", "---------------------------------");
  lines.push(
    analysis.missing_information.length > 0
      ? `Missing information: ${analysis.missing_information.join("; ")}`
      : "Missing information: NOT_STATED"
  );
  if (analysis.warnings.length > 0) {
    analysis.warnings.forEach((w) => lines.push(`Warning: ${w}`));
  }

  return lines.join("\n");
}

export function downloadTextFile(filename, content) {
  const blob = new Blob(["\uFEFF" + content], {
    type: "text/plain;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}