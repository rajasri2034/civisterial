import React from 'react';
import { Link } from 'react-router-dom';

export function SkipLink({ href = '#main-content' }) {
  return (
    <a
      href={href}
      className="sr-only focus:not-sr-only focus:block focus:w-full focus:bg-gov-focus focus:text-gov-text focus:px-4 focus:py-3 focus:font-bold focus:underline"
    >
      Skip to main content
    </a>
  );
}

export function Header() {
  return (
    <header className="bg-gov-navy text-white border-b-4 border-gov-link">
      <div className="max-w-gov mx-auto px-4 py-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-baseline gap-3">
          <Link
            to="/"
            className="text-2xl font-bold tracking-tight text-white no-underline hover:underline"
          >
            Civisterial
          </Link>
          <span className="text-sm text-gray-200">
            Official document explainer
          </span>
        </div>
        <nav aria-label="Primary navigation">
          <Link
            to="/design"
            className="text-sm text-white underline hover:text-gray-200"
          >
            Design system
          </Link>
        </nav>
      </div>
    </header>
  );
}

export function PhaseBanner({ phase = 'Beta', children }) {
  return (
    <div className="max-w-gov mx-auto px-4">
      <div className="py-2.5 border-b border-gov-border flex flex-wrap items-center gap-3 text-sm">
        <strong className="bg-gov-link text-white uppercase tracking-wider px-2 py-0.5 text-xs font-bold rounded-none">
          {phase}
        </strong>
        <span className="text-gov-text">
          {children ||
            'This is an independent service, not run by any government. Demo with public or synthetic documents only.'}
        </span>
      </div>
    </div>
  );
}

export function Footer() {
  return (
    <footer className="bg-gov-panel border-t border-gov-border mt-12 text-gov-text">
      <div className="max-w-gov mx-auto px-4 py-8 space-y-4 text-sm">
        <p className="font-bold">
          This is an independent service, not run by any government.
        </p>
        <p className="text-gov-secondary">
          Civisterial explains documents. It is not a government authority or
          legal advice. Always confirm with the issuing office.
        </p>
        <p className="text-gov-secondary">
          Privacy notice: Uploaded document text is redacted before being sent
          to Google Gemini for analysis. Civisterial stores no documents or
          results in a database or browser storage.
        </p>
      </div>
    </footer>
  );
}
