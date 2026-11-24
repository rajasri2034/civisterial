import React from 'react';

export function ProgressBar({
  stages = ['Reading', 'Analysing', 'Checking quotations'],
  currentStageIndex = 0,
}) {
  const percent = Math.round(((currentStageIndex + 1) / stages.length) * 100);
  const currentLabel = stages[currentStageIndex] || stages[0];

  return (
    <div className="my-6 p-4 bg-gov-panel border border-gov-border">
      <div className="flex justify-between items-center mb-2">
        <span aria-live="polite" className="font-bold text-gov-text">
          Step {currentStageIndex + 1} of {stages.length}: {currentLabel}
        </span>
        <span className="text-sm font-mono text-gov-secondary">{percent}%</span>
      </div>
      <div
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={currentLabel}
        className="w-full h-4 bg-white border-2 border-gov-text"
      >
        <div
          className="h-full bg-gov-green transition-all duration-200"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

export function TabNav({ tabs = [], activeTab, onSelectTab }) {
  return (
    <div className="my-6">
      <div
        role="tablist"
        aria-label="Document analysis sections"
        className="flex flex-wrap border-b border-gov-border gap-1"
      >
        {tabs.map((tab) => {
          const isActive = tab.id === activeTab;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => onSelectTab(tab.id)}
              className={`px-4 py-2.5 text-base border border-b-0 rounded-none cursor-pointer ${
                isActive
                  ? 'bg-white border-gov-border font-bold text-gov-text -mb-px border-b-white'
                  : 'bg-gov-panel border-transparent text-gov-link underline hover:text-gov-linkHover'
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
