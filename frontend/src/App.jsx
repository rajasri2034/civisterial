import React, { useEffect, useRef, useState } from "react";
import { fetchSupportedLanguages } from "./config/languages";
import { LandingPage } from "./pages/LandingPage";
import { ResultsPage } from "./pages/ResultsPage";
import { UploadPage } from "./pages/UploadPage";

export function App() {
  const [route, setRoute] = useState("landing");
  const [languages, setLanguages] = useState([]);
  const [langLoadError, setLangLoadError] = useState(null);
  const [documentLanguage, setDocumentLanguage] = useState("auto");
  const [explanationLanguage, setExplanationLanguage] = useState("en");

  // Strictly in-memory React state only (never persisted to browser storage)
  const [analysisResult, setAnalysisResult] = useState(null);
  const [checkedTasks, setCheckedTasks] = useState({});

  const mainHeadingContainerRef = useRef(null);

  useEffect(() => {
    let active = true;
    fetchSupportedLanguages()
      .then((list) => {
        if (active) setLanguages(list);
      })
      .catch((err) => {
        if (active) setLangLoadError(err.message);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const clearOnUnload = () => {
      setAnalysisResult(null);
      setCheckedTasks({});
    };
    window.addEventListener("beforeunload", clearOnUnload);
    return () => window.removeEventListener("beforeunload", clearOnUnload);
  }, []);

  const navigateTo = (nextRoute) => {
    setRoute(nextRoute);
    requestAnimationFrame(() => {
      mainHeadingContainerRef.current?.focus();
    });
  };

  const clearAllWorkflowState = (targetRoute) => {
    setAnalysisResult(null);
    setCheckedTasks({});
    navigateTo(targetRoute);
  };

  const handleAnalysisComplete = (result) => {
    setAnalysisResult(result);
    setCheckedTasks({});
    navigateTo("results");
  };

  const handleToggleTask = (index) => {
    setCheckedTasks((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  };

  return (
    <>
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      <header className="gov-header">
        <div className="gov-header__inner">
          <a
            href="#top"
            className="gov-header__brand"
            onClick={(e) => {
              e.preventDefault();
              clearAllWorkflowState("landing");
            }}
          >
            Civisterial
          </a>
          <nav className="gov-header__nav" aria-label="Primary navigation">
            <a
              href="#home"
              className="gov-header__link"
              onClick={(e) => {
                e.preventDefault();
                clearAllWorkflowState("landing");
              }}
            >
              Home
            </a>
            <a
              href="#upload"
              className="gov-header__link"
              onClick={(e) => {
                e.preventDefault();
                clearAllWorkflowState("upload");
              }}
            >
              Upload document
            </a>
          </nav>
        </div>
      </header>

      <div className="gov-phase-banner">
        <span className="gov-tag gov-tag--blue">BETA</span>
        <span>
          Plain-language administrative guidance only — not legal advice. Nothing is stored by Civisterial.
        </span>
      </div>

      <main
        id="main-content"
        ref={mainHeadingContainerRef}
        className="gov-main"
        tabIndex={-1}
      >
        {langLoadError && (
          <div className="gov-error-summary" role="alert">
            <h2 className="gov-error-summary__title">Service configuration issue</h2>
            <p>{langLoadError}</p>
          </div>
        )}

        {route === "landing" && (
          <LandingPage onStart={() => clearAllWorkflowState("upload")} />
        )}

        {route === "upload" && (
          <UploadPage
            languages={languages}
            documentLanguage={documentLanguage}
            explanationLanguage={explanationLanguage}
            onDocumentLanguageChange={setDocumentLanguage}
            onExplanationLanguageChange={setExplanationLanguage}
            onAnalysisComplete={handleAnalysisComplete}
            onCancelWorkflow={() => clearAllWorkflowState("landing")}
          />
        )}

        {route === "results" && analysisResult && (
          <ResultsPage
            result={analysisResult}
            checkedTasks={checkedTasks}
            onToggleTask={handleToggleTask}
            onDeleteResults={() => clearAllWorkflowState("landing")}
            onStartNewAnalysis={() => clearAllWorkflowState("upload")}
          />
        )}
      </main>

      <footer className="gov-footer">
        <div className="gov-footer__inner">
          <p style={{ marginBottom: 0 }}>
            Civisterial provides plain-language administrative guidance, not legal advice. All results remain in browser memory only and are cleared when you leave.
          </p>
        </div>
      </footer>
    </>
  );
}

export default App;