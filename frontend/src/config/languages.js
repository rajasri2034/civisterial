import { apiUrl } from "./api.js";

export async function fetchSupportedLanguages() {
  const res = await fetch(apiUrl("/api/languages"));
  if (!res.ok) {
    throw new Error("Unable to load supported languages from the server.");
  }
  const data = await res.json();
  return data.languages;
}

const UI_COPY_BY_LANG = {
  en: {
    tabs: {
      overview: "Overview",
      simplified: "Simplified text",
      actionPlan: "Action plan",
      deadlinesRequirements: "Deadlines and requirements",
      evidence: "Evidence",
    },
    checklistNotSavedWarning:
      "Your progress is not saved. Download or print before leaving this page.",
    ambiguousDateWarning: "Please confirm this date",
    evidenceDisclaimer:
      "This shows the quotation exists in your document. It does not confirm our explanation is correct.",
    interpretationForUserNote:
      "Interpretation of this item is left for you to review against your original document.",
    deleteMyResults: "Delete my results",
    downloadTxt: "Download .txt summary",
    printA4: "Print / Save A4",
  },
  ta: {
    tabs: {
      overview: "மேலோட்டம்",
      simplified: "எளிய உரை",
      actionPlan: "செயல் திட்டம்",
      deadlinesRequirements: "காலக்கெடு மற்றும் தேவைகள்",
      evidence: "சான்றுகள்",
    },
    checklistNotSavedWarning:
      "உங்கள் முன்னேற்றம் சேமிக்கப்படவில்லை. இந்தப் பக்கத்தை விட்டு வெளியேறும் முன் பதிவிறக்கவும் அல்லது அச்சிடவும்.",
    ambiguousDateWarning: "Please confirm this date — இந்தத் தேதியை உறுதிப்படுத்தவும்",
    evidenceDisclaimer:
      "This shows the quotation exists in your document. It does not confirm our explanation is correct.",
    interpretationForUserNote:
      "இந்தக் கூறின் பொருளை உங்கள் மூல ஆவணத்துடன் ஒப்பிட்டு நீங்களே சரிபார்க்கவும்.",
    deleteMyResults: "எனது முடிவுகளை நீக்கு",
    downloadTxt: ".txt கோப்பாகப் பதிவிறக்கு",
    printA4: "A4 அச்சிடு",
  },
  hi: {
    tabs: {
      overview: "सारांश",
      simplified: "सरल पाठ",
      actionPlan: "कार्य योजना",
      deadlinesRequirements: "अंतिम तिथि और आवश्यकताएँ",
      evidence: "प्रमाण",
    },
    checklistNotSavedWarning:
      "आपकी प्रगति सहेजी नहीं गई है। इस पृष्ठ को छोड़ने से पहले डाउनलोड या प्रिंट करें।",
    ambiguousDateWarning: "Please confirm this date — कृपया इस तिथि की पुष्टि करें",
    evidenceDisclaimer:
      "This shows the quotation exists in your document. It does not confirm our explanation is correct.",
    interpretationForUserNote:
      "इस बिंदु की व्याख्या की समीक्षा अपने मूल दस्तावेज़ से स्वयं करें।",
    deleteMyResults: "मेरे परिणाम हटाएँ",
    downloadTxt: ".txt डाउनलोड करें",
    printA4: "A4 प्रिंट करें",
  },
  ar: {
    tabs: {
      overview: "نظرة عامة",
      simplified: "النص المبسط",
      actionPlan: "خطة العمل",
      deadlinesRequirements: "المواعيد النهائية والمتطلبات",
      evidence: "الأدلة والاقتباسات",
    },
    checklistNotSavedWarning:
      "لا يتم حفظ تقدمك. يرجى التنزيل أو الطباعة قبل مغادرة هذه الصفحة.",
    ambiguousDateWarning: "Please confirm this date — يرجى تأكيد هذا التاريخ",
    evidenceDisclaimer:
      "This shows the quotation exists in your document. It does not confirm our explanation is correct.",
    interpretationForUserNote:
      "يُترك تفسير هذا البند لمراجعتك الشخصية مقابل المستند الأصلي.",
    deleteMyResults: "حذف نتائجي",
    downloadTxt: "تنزيل ملف .txt",
    printA4: "طباعة A4",
  },
};

export function getUiCopyForLanguage(code) {
  const norm = (code || "en").trim().toLowerCase();
  return UI_COPY_BY_LANG[norm] ?? UI_COPY_BY_LANG.en;
}