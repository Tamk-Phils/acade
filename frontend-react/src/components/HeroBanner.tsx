import React from 'react';

interface HeroBannerProps {
  institution: 'uba' | 'catuc';
  onOpenPrivacy: () => void;
}

export const HeroBanner: React.FC<HeroBannerProps> = ({
  institution,
  onOpenPrivacy
}) => {
  const isUBa = institution === 'uba';

  return (
    <section className="hero-header">
      <div className="hero-content">
        <div className="hero-text">
          <h1>
            {isUBa
              ? 'The University of Bamenda Formatting System'
              : 'Catholic University of Cameroon (CATUC) Formatting Engine'}
          </h1>
          <p>
            {isUBa
              ? 'Senate-standard manuscript audit, preliminaries sequencing, and 4.0 cm binding margin restructuring for COLTECH, FS, FEMS, FA, FED, HTTTC, HTTC, HITL, and HICM.'
              : 'Official formatting protocol across all 7 faculties (FBMS, SENG, FST, SHMS, FHSS, STANR, and STHEO) with Fides et Scientia guidelines.'}
          </p>
        </div>

        <div className="official-badges">
          <span className="compliance-pill">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="2.5">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
              <polyline points="22 4 12 14.01 9 11.01"></polyline>
            </svg>
            Official Template
          </span>

          <span className="compliance-pill">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#2563EB" strokeWidth="2.5">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
              <line x1="9" y1="3" x2="9" y2="21"></line>
            </svg>
            4.0 cm Gutter
          </span>

          <span
            className="compliance-pill law"
            onClick={onOpenPrivacy}
            title="View statutory compliance under Cameroonian Law No. 2010/012"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#64748B" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
            </svg>
            Law No. 2010/012
          </span>
        </div>
      </div>
    </section>
  );
};

