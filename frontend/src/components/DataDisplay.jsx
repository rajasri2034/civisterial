import React, { useState } from 'react';

const TAG_STYLES = {
  exact: {
    bg: 'bg-[#cce2d8]',
    text: 'text-[#005a30]',
    border: 'border-[#00703c]',
    symbol: '[✓]',
  },
  possible: {
    bg: 'bg-[#fff7bf]',
    text: 'text-[#594d00]',
    border: 'border-[#b58900]',
    symbol: '[!]',
  },
  not_found: {
    bg: 'bg-[#f6d7d2]',
    text: 'text-[#942514]',
    border: 'border-[#d4351c]',
    symbol: '[✕]',
  },
  needs_verification: {
    bg: 'bg-[#f3f2f1]',
    text: 'text-[#0b0c0c]',
    border: 'border-[#505a5f]',
    symbol: '[?]',
  },
  mandatory: {
    bg: 'bg-[#d2e2f1]',
    text: 'text-[#144e81]',
    border: 'border-[#1d70b8]',
    symbol: '[*]',
  },
};

export function Tag({ variant = 'needs_verification', children }) {
  const style = TAG_STYLES[variant] || TAG_STYLES.needs_verification;
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 text-xs font-bold uppercase tracking-wide border rounded-none ${style.bg} ${style.text} ${style.border}`}
    >
      <span aria-hidden="true" className="font-mono">
        {style.symbol}
      </span>
      <span>{children}</span>
    </span>
  );
}

export function SummaryList({ rows = [] }) {
  return (
    <dl className="divide-y divide-gov-border border-t border-b border-gov-border">
      {rows.map((row, idx) => (
        <div
          key={idx}
          className="py-3 sm:grid sm:grid-cols-3 sm:gap-4 items-baseline"
        >
          <dt className="font-bold text-gov-text">{row.key}</dt>
          <dd className="mt-1 sm:mt-0 sm:col-span-2 text-gov-text break-words">
            {row.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function Table({ caption, headers = [], rows = [] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left">
        {caption && (
          <caption className="text-left font-bold text-lg mb-2 text-gov-text">
            {caption}
          </caption>
        )}
        <thead>
          <tr className="border-b-2 border-gov-text">
            {headers.map((header, idx) => (
              <th key={idx} scope="col" className="py-2.5 pr-4 font-bold">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gov-border">
          {rows.map((cells, rIdx) => (
            <tr key={rIdx} className="align-top">
              {cells.map((cell, cIdx) => (
                <td key={cIdx} className="py-3 pr-4">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Details({ summary, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <details
      open={open}
      onToggle={(e) => setOpen(e.currentTarget.open)}
      className="my-4"
    >
      <summary className="cursor-pointer text-gov-link hover:text-gov-linkHover underline inline-flex items-center gap-2 py-1">
        <span aria-hidden="true" className="text-xs font-mono">
          {open ? '▼' : '▶'}
        </span>
        <span>{summary}</span>
      </summary>
      <div className="mt-2 pl-4 border-l-4 border-gov-border py-1">
        {children}
      </div>
    </details>
  );
}

export function InsetText({ children }) {
  return (
    <div className="border-l-4 border-gov-border pl-4 py-2 my-4 text-gov-text">
      {children}
    </div>
  );
}

export function WarningText({ children }) {
  return (
    <div className="flex items-start gap-3 my-4 py-2" role="note">
      <span
        aria-hidden="true"
        className="flex-shrink-0 w-7 h-7 bg-gov-text text-white font-bold flex items-center justify-center rounded-full text-base mt-0.5"
      >
        !
      </span>
      <strong className="font-bold text-gov-text">{children}</strong>
    </div>
  );
}

export function NotificationBanner({
  title = 'Important',
  variant = 'info',
  children,
}) {
  const borderColor =
    variant === 'success' ? 'border-gov-green' : 'border-gov-link';
  const headerBg = variant === 'success' ? 'bg-gov-green' : 'bg-gov-link';

  return (
    <div
      role="region"
      aria-labelledby="notification-banner-title"
      className={`border-4 ${borderColor} my-6 bg-white rounded-none`}
    >
      <div className={`${headerBg} text-white px-4 py-1.5`}>
        <h2 id="notification-banner-title" className="text-base font-bold">
          {title}
        </h2>
      </div>
      <div className="p-4 text-gov-text">{children}</div>
    </div>
  );
}
