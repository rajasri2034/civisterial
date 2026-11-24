import React, { useState } from 'react';
import {
  Button,
  Tag,
  SummaryList,
  Table,
  Details,
  InsetText,
  WarningText,
  NotificationBanner,
  ErrorSummary,
  Checkboxes,
  FileUpload,
  ProgressBar,
  TabNav,
} from '../components';

export default function DesignSystemPage() {
  const [activeTab, setActiveTab] = useState('overview');
  const [checks, setChecks] = useState([
    {
      id: 'chk-1',
      label: 'Identity proof (with personal numbers masked)',
      hint: 'Mandatory requirement — Page 1',
      checked: true,
    },
    {
      id: 'chk-2',
      label: 'Income certificate issued within 6 months',
      hint: 'Mandatory requirement — Page 2',
      checked: false,
    },
  ]);

  const handleToggle = (id, nextVal) => {
    setChecks((prev) =>
      prev.map((item) => (item.id === id ? { ...item, checked: nextVal } : item))
    );
  };

  return (
    <div className="space-y-8">
      <div>
        <span className="text-gov-secondary text-base block mb-1">
          Design System Review
        </span>
        <h1 className="text-3xl md:text-4xl font-bold text-gov-text">
          Civisterial UI Components
        </h1>
        <p className="mt-3 text-gov-secondary">
          Calm, high-contrast public-service components inspired by GOV.UK and
          USWDS. Verify at 320px, 768px, and 1280px viewports.
        </p>
      </div>

      <NotificationBanner title="System notice" variant="info">
        Civisterial explains documents. It is not a government authority or
        legal advice. Always confirm with the issuing office.
      </NotificationBanner>

      <ErrorSummary
        errors={[
          {
            href: '#sample-upload',
            message: 'Select a PDF, PNG, or JPEG file under 10 MB',
          },
        ]}
      />

      <section className="space-y-4">
        <h2 className="text-2xl font-bold border-b border-gov-border pb-2">
          1. Buttons &amp; Verification Tags
        </h2>
        <div className="flex flex-wrap gap-3">
          <Button variant="primary">Start now</Button>
          <Button variant="secondary">Delete my results</Button>
          <Button variant="warning">Cancel analysis</Button>
        </div>

        <div className="flex flex-wrap gap-2 pt-2">
          <Tag variant="exact">Exact quotation found</Tag>
          <Tag variant="possible">Possible match: review required</Tag>
          <Tag variant="not_found">Not found</Tag>
          <Tag variant="needs_verification">Needs user verification</Tag>
          <Tag variant="mandatory">Mandatory</Tag>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-2xl font-bold border-b border-gov-border pb-2">
          2. Progress &amp; Navigation Tabs
        </h2>
        <ProgressBar currentStageIndex={1} />
        <TabNav
          activeTab={activeTab}
          onSelectTab={setActiveTab}
          tabs={[
            { id: 'overview', label: 'Overview' },
            { id: 'simplified', label: 'Simplified text' },
            { id: 'action', label: 'Action plan' },
            { id: 'evidence', label: 'Evidence' },
          ]}
        />
        <p className="text-sm text-gov-secondary">
          Active tab state: <strong>{activeTab}</strong>
        </p>
      </section>

      <section className="space-y-4">
        <h2 className="text-2xl font-bold border-b border-gov-border pb-2">
          3. Summary List &amp; Table
        </h2>
        <SummaryList
          rows={[
            { key: 'Document title', value: 'Public Scholarship Notice 2026' },
            { key: 'Issuing authority', value: 'Directorate of Technical Education' },
            {
              key: 'Deadline',
              value: 'No deadline was explicitly identified in this document.',
            },
          ]}
        />

        <Table
          caption="Extracted Fees & Evidence"
          headers={['Purpose', 'Amount', 'Status']}
          rows={[
            [
              'Application processing fee',
              'Rs. 500',
              <Tag key="t1" variant="exact">
                Exact quotation found
              </Tag>,
            ],
            [
              'Late submission surcharge',
              'Not stated in the document.',
              <Tag key="t2" variant="needs_verification">
                Needs user verification
              </Tag>,
            ],
          ]}
        />
      </section>

      <section className="space-y-4">
        <h2 className="text-2xl font-bold border-b border-gov-border pb-2">
          4. Callouts &amp; Expandable Details
        </h2>
        <InsetText>
          This shows the quotation exists in your document. It does not confirm
          our explanation is correct.
        </InsetText>
        <WarningText>
          Personal details in images are not hidden before analysis. Only
          continue with a public or sample document.
        </WarningText>
        <Details summary="Could not verify (1 item)">
          <p className="text-sm text-gov-secondary">
            Items below the similarity threshold are hidden here for manual
            inspection against your original notice.
          </p>
        </Details>
      </section>

      <section className="space-y-4">
        <h2 className="text-2xl font-bold border-b border-gov-border pb-2">
          5. Form Controls
        </h2>
        <Checkboxes
          legend="Required documents checklist"
          hint="Your progress is not saved. Download or print before leaving this page."
          items={checks}
          onChange={handleToggle}
        />
        <FileUpload
          id="sample-upload"
          error="The selected file must be a PDF, PNG, or JPEG"
        />
      </section>
    </div>
  );
}
