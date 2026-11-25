import React from "react";

export default function PrivacyNotice({ isFreeTier = true }) {
  return (
    <section
      aria-labelledby="privacy-notice-heading"
      className="privacy-notice-box"
    >
      <h2 id="privacy-notice-heading">How Your Document Is Handled</h2>

      {isFreeTier && (
        <p role="note">
          <strong>Public or synthetic documents only:</strong> This deployment
          uses the Google Gemini API Free Tier. Under Google&apos;s Free Tier
          terms, Google may retain prompts and outputs and human reviewers may
          read them to improve Google products. Do not upload personal,
          confidential, or sensitive records.
        </p>
      )}

      <ul>
        <li>
          <strong>What is sent to Google Gemini:</strong> For text-based PDFs,
          Civisterial runs automated redaction first to mask emails, phone
          numbers, PAN-style IDs, and street addresses, then sends only the
          redacted text over HTTPS. For images and scanned PDF pages, nothing is
          sent until you check the explicit confirmation box.
        </li>
        <li>
          <strong>What is NOT redacted:</strong> Images (PNG, JPEG, WebP) and
          scanned/image-only PDF pages are sent as visual pixels without
          automated redaction. Names or non-standard identifiers in text may
          also remain unmasked.
        </li>
        <li>
          <strong>Identifiers are never restored:</strong> Any masked token
          (such as <code>[REDACTED_EMAIL]</code> or <code>[REDACTED_ID]</code>)
          stays masked in your summary, checklist, and evidence quotes.
        </li>
        <li>
          <strong>What Civisterial does not store:</strong> Civisterial uses no
          database, no user accounts, no browser cookies, no persistent web
          storage, and no analytics trackers. Temporary parse files are deleted
          when your request finishes.
        </li>
        <li>
          <strong>Hosting &amp; Google Gemini retention boundaries:</strong>{" "}
          Civisterial configures application logs to exclude document content
          and request bodies, but our hosting providers (Render/Railway and
          Vercel/Netlify) still record standard infrastructure metadata (such as
          timestamps, status codes, and crash diagnostics), and Google retains
          Gemini API requests for up to 55 days for abuse monitoring even on
          paid tiers. Civisterial cannot independently verify or guarantee
          immediate deletion on third-party infrastructure.
        </li>
      </ul>
    </section>
  );
}