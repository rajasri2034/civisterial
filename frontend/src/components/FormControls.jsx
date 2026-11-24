import React from 'react';

export function Button({
  variant = 'primary',
  type = 'button',
  onClick,
  disabled = false,
  children,
  className = '',
}) {
  const base =
    'inline-block font-bold px-4 py-2.5 text-center border-2 border-transparent rounded-none cursor-pointer transition-none disabled:opacity-50 disabled:cursor-not-allowed';

  const variants = {
    primary:
      'bg-gov-green text-white border-b-4 border-b-gov-greenShadow hover:bg-gov-greenHover',
    secondary:
      'bg-gov-greyBtn text-gov-text border-b-4 border-b-gov-greyShadow hover:bg-gov-greyBtnHover',
    warning:
      'bg-gov-error text-white border-b-4 border-b-[#6b1407] hover:bg-[#aa2a16]',
  };

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${base} ${variants[variant] || variants.primary} ${className}`}
    >
      {children}
    </button>
  );
}

export function ErrorSummary({ title = 'There is a problem', errors = [] }) {
  if (!errors.length) return null;
  return (
    <div
      role="alert"
      tabIndex={-1}
      className="border-4 border-gov-error p-4 my-6 bg-white rounded-none"
    >
      <h2 className="text-xl font-bold text-gov-text mb-3">{title}</h2>
      <ul className="list-disc pl-5 space-y-1.5">
        {errors.map((err, idx) => (
          <li key={idx}>
            {err.href ? (
              <a
                href={err.href}
                className="font-bold text-gov-error underline hover:text-gov-text"
              >
                {err.message}
              </a>
            ) : (
              <span className="font-bold text-gov-error">{err.message}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function Checkboxes({ legend, hint, items = [], onChange }) {
  return (
    <fieldset className="my-4">
      {legend && <legend className="font-bold text-lg mb-1">{legend}</legend>}
      {hint && <p className="text-gov-secondary text-base mb-3">{hint}</p>}
      <div className="space-y-3">
        {items.map((item) => (
          <label
            key={item.id}
            htmlFor={item.id}
            className="flex items-start gap-3 cursor-pointer select-none"
          >
            <input
              id={item.id}
              type="checkbox"
              checked={!!item.checked}
              onChange={(e) => onChange && onChange(item.id, e.target.checked)}
              className="w-6 h-6 mt-0.5 border-2 border-gov-text rounded-none accent-gov-text flex-shrink-0"
            />
            <div>
              <span className="block text-gov-text">{item.label}</span>
              {item.hint && (
                <span className="block text-sm text-gov-secondary">
                  {item.hint}
                </span>
              )}
            </div>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export function FileUpload({
  id = 'document-upload',
  label = 'Upload a document',
  hint = 'PDF, PNG, or JPEG up to 10 MB.',
  accept = '.pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg',
  error,
  onFileSelect,
}) {
  return (
    <div
      className={`my-6 ${
        error ? 'border-l-4 border-gov-error pl-4' : ''
      }`}
    >
      <label htmlFor={id} className="block font-bold text-lg mb-1">
        {label}
      </label>
      {hint && <p className="text-gov-secondary text-base mb-2">{hint}</p>}
      {error && (
        <p id={`${id}-error`} className="font-bold text-gov-error mb-2">
          Error: {error}
        </p>
      )}
      <input
        id={id}
        type="file"
        accept={accept}
        aria-describedby={error ? `${id}-error` : undefined}
        onChange={(e) =>
          onFileSelect && onFileSelect(e.target.files?.[0] || null)
        }
        className="block w-full text-base text-gov-text border-2 border-gov-text p-2 bg-gov-panel rounded-none file:mr-4 file:py-2 file:px-3 file:border-2 file:border-gov-text file:bg-white file:text-gov-text file:font-bold file:rounded-none file:cursor-pointer"
      />
    </div>
  );
}
