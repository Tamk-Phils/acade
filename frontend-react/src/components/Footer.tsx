import React from 'react';

interface FooterProps {
  onOpenPrivacy: () => void;
}

export const Footer: React.FC<FooterProps> = ({ onOpenPrivacy }) => {
  return (
    <footer className="footer">
      <div className="footer-content">
        <div>
          <div style={{ fontWeight: 700, color: '#FFFFFF', marginBottom: '0.25rem' }}>
            AcadFormat — Academic Standardization & Document Integrity System
          </div>
          <div>
            Built for The University of Bamenda (UBa) and Catholic University of Cameroon (CATUC) Bamenda.
          </div>
        </div>

        <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center' }}>
          <button
            type="button"
            onClick={onOpenPrivacy}
            style={{ background: 'none', border: 'none', color: '#94A3B8', cursor: 'pointer', fontSize: '0.8rem', textDecoration: 'underline' }}
          >
            Statutory Privacy Notice (Law No. 2010/012)
          </button>
          <span>v2.3.0 Production Build</span>
        </div>
      </div>
    </footer>
  );
};

