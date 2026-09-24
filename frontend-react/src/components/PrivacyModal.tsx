import React from 'react';

interface PrivacyModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const PrivacyModal: React.FC<PrivacyModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">
            Statutory Privacy & Data Protection Notice
          </span>
          <button
            type="button"
            onClick={onClose}
            style={{ background: 'none', border: 'none', fontSize: '1.2rem', cursor: 'pointer', color: '#64748B' }}
          >
            ✕
          </button>
        </div>

        <div className="modal-body" style={{ fontSize: '0.85rem', lineHeight: '1.6', color: 'var(--color-text-main)' }}>
          <div style={{ padding: '0.75rem', background: '#F1F5F9', borderRadius: 'var(--radius-sm)', marginBottom: '1rem', borderLeft: '4px solid var(--color-primary)' }}>
            <strong>Governing Law:</strong> Law No. 2010/012 of 21 December 2010 on Cybersecurity and Cybercrime in the Republic of Cameroon.
          </div>

          <h4 style={{ fontWeight: 700, margin: '1rem 0 0.35rem' }}>1. Scope of Manuscript Processing</h4>
          <p>
            AcadFormat is an academic standardization utility engineered strictly to enforce institutional formatting guidelines mandated by the Senate of The University of Bamenda and the Governing Council of the Catholic University of Cameroon (CATUC).
          </p>

          <h4 style={{ fontWeight: 700, margin: '1rem 0 0.35rem' }}>2. Intellectual Property & Confidentiality</h4>
          <p>
            All submitted research proposals, capstone projects, dissertations, theses, internship reports, and coursework remain the exclusive intellectual property of the author and respective university departments. Uploaded documents are securely processed in isolated memory workspaces and are never indexed, shared, or redistributed to third parties.
          </p>

          <h4 style={{ fontWeight: 700, margin: '1rem 0 0.35rem' }}>3. Digital Identity & Device Binding</h4>
          <p>
            In compliance with Section 32 of Law No. 2010/012 regarding digital transaction integrity and fraud prevention, user accounts are bound to an authenticated hardware fingerprint. Sharing credentials across unauthorized external devices requires re-verification to safeguard academic authenticity.
          </p>

          <h4 style={{ fontWeight: 700, margin: '1rem 0 0.35rem' }}>4. Payment Security & Data Minimization</h4>
          <p>
            Mobile Money transactions (MTN MoMo and Orange Money) are authorized via end-to-end encrypted USSD push notifications. AcadFormat does not store personal financial credentials or PIN codes.
          </p>
        </div>

        <div className="modal-footer">
          <button
            type="button"
            className="btn-submit-format"
            onClick={onClose}
            style={{ width: 'auto', padding: '0.5rem 1.25rem' }}
          >
            I Understand & Agree
          </button>
        </div>
      </div>
    </div>
  );
};

