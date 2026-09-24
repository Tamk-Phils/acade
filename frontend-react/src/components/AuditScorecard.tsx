import React from 'react';
import { AuditResult } from '../types';

interface AuditScorecardProps {
  audit: AuditResult | null;
}

export const AuditScorecard: React.FC<AuditScorecardProps> = ({ audit }) => {
  if (!audit) return null;

  const score = audit.compliance_score || 0;
  const scoreClass = score >= 85 ? 'high' : score >= 60 ? 'mid' : 'low';

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 11l3 3L22 4"></path>
            <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
          </svg>
          Audit Scorecard & Compliance
        </span>
        <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
          {audit.total_issues} issues identified
        </span>
      </div>

      <div className="card-body">
        {/* Score Indicator & Summary */}
        <div className="score-overview">
          <div className={`score-circle ${scoreClass}`}>
            <span>{score}%</span>
            <span className="score-circle-label">Standard</span>
          </div>

          <div className="score-details">
            <h4 className="score-title">
              {score >= 85
                ? 'Senate Standard Compliant'
                : score >= 60
                ? 'Moderate Discrepancies'
                : 'Substantial Structural Violations'}
            </h4>
            <p className="score-subtitle">
              {score >= 85
                ? 'Your manuscript closely adheres to binding margins and preliminary ordering.'
                : 'Automated restructuring will resolve preliminary sequence, 4.0cm gutter, and TOC.'}
            </p>
          </div>
        </div>

        {/* Issues Checklist */}
        <div className="audit-checklist">
          {audit.issues.map((issue) => (
            <div key={issue.id} className={`audit-item ${issue.severity}`}>
              <div style={{ marginTop: '2px' }}>
                {issue.severity === 'error' ? (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="8" x2="12" y2="12"></line>
                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                  </svg>
                ) : (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <polygon points="12 2 2 22 22 22 12 2"></polygon>
                    <line x1="12" y1="9" x2="12" y2="13"></line>
                    <line x1="12" y1="17" x2="12.01" y2="17"></line>
                  </svg>
                )}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600 }}>{issue.message}</div>
                <div style={{ fontSize: '0.725rem', opacity: 0.85, marginTop: '2px' }}>
                  {issue.recommendation}
                </div>
              </div>
            </div>
          ))}

          {audit.issues.length === 0 && (
            <div className="audit-item success">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
              <div>All structural and margin tests passed! Ready for official printing.</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

