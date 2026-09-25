import React, { useState, useEffect, useRef } from 'react';
import { DocumentMetadata } from '../types';

interface LivePreviewProps {
  previewPages: string[];
  docType: string;
  token?: string;
  onDownload: (fmt: 'docx' | 'pdf') => void;
  downloading: boolean;
  metadata?: DocumentMetadata;
  onPromptAI?: (prompt: string) => void;
}

export const LivePreview: React.FC<LivePreviewProps> = ({
  previewPages,
  docType,
  token,
  onDownload,
  downloading,
  metadata,
  onPromptAI
}) => {
  const [currentPage, setCurrentPage] = useState(0);
  const [zoom, setZoom] = useState(100);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [activeTab, setActiveTab] = useState<'pages' | 'structure'>('pages');
  const [selectedSnippet, setSelectedSnippet] = useState<string>('');
  const [selectionPos, setSelectionPos] = useState<{ x: number; y: number } | null>(null);
  const viewportRef = useRef<HTMLDivElement>(null);

  // Reset page index if pages array updates
  useEffect(() => {
    setCurrentPage(0);
  }, [previewPages]);

  // Highlight / text selection listener
  useEffect(() => {
    const handleMouseUp = () => {
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed) {
        return;
      }
      const text = sel.toString().trim();
      if (text.length >= 3) {
        setSelectedSnippet(text);
        try {
          const range = sel.getRangeAt(0);
          const rect = range.getBoundingClientRect();
          setSelectionPos({
            x: Math.max(20, rect.left + rect.width / 2),
            y: Math.max(20, rect.top - 40)
          });
        } catch (_) {
          setSelectionPos(null);
        }
      }
    };

    document.addEventListener('mouseup', handleMouseUp);
    return () => {
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  // Fullscreen keyboard navigation & ESC listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsFullscreen(false);
      } else if (e.key === 'ArrowRight' || e.key === 'PageDown') {
        if (currentPage < previewPages.length - 1) {
          setCurrentPage((prev) => prev + 1);
        }
      } else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
        if (currentPage > 0) {
          setCurrentPage((prev) => prev - 1);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentPage, previewPages.length]);

  const hasPages = previewPages && previewPages.length > 0;
  const currentImageUrl = hasPages ? previewPages[currentPage] : null;

  const handleZoomIn = () => setZoom((z) => Math.min(z + 15, 200));
  const handleZoomOut = () => setZoom((z) => Math.max(z - 15, 50));
  const handleZoomReset = () => setZoom(100);

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  const handleEditDeptAI = () => {
    onPromptAI?.(
      `Please help me update the department and option for this manuscript.\nCurrently Department: "${metadata?.department || 'Computer Engineering'}"\nOption: "${metadata?.option || 'Information Technology and Cybersecurity'}"`
    );
  };

  const handleEditTitleAI = () => {
    onPromptAI?.(
      `Please refine and polish this dissertation title to ensure official Senate compliance:\n"${metadata?.title || ''}"`
    );
  };

  const handleEditSupervisorAI = () => {
    const sup = metadata?.supervisors?.[0] || '';
    const rank = metadata?.supervisor_ranks?.[0] || '';
    onPromptAI?.(
      `Please update the supervisor information for my manuscript. Currently: "${sup}" with rank "${rank}".`
    );
  };

  const handleEditSelectionAI = () => {
    if (!selectedSnippet) return;
    onPromptAI?.(
      `Please help me modify or rewrite this highlighted section from my manuscript:\n"${selectedSnippet}"`
    );
    setSelectedSnippet('');
  };

  return (
    <div className="preview-container">
      {/* Floating Action Button for Selected Text */}
      {selectedSnippet && (
        <div
          className="ai-selection-floating-pill"
          style={{
            position: 'fixed',
            zIndex: 9999,
            top: selectionPos ? `${selectionPos.y}px` : '100px',
            left: selectionPos ? `${selectionPos.x}px` : '50%',
            transform: selectionPos ? 'translate(-50%, 0)' : 'translateX(-50%)',
            background: 'linear-gradient(135deg, #1E3A8A, #0284C7)',
            color: '#FFFFFF',
            padding: '6px 14px',
            borderRadius: '9999px',
            boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            cursor: 'pointer',
            fontSize: '0.8rem',
            fontWeight: 600,
            whiteSpace: 'nowrap',
            animation: 'fadeIn 0.2s ease-out'
          }}
          onClick={handleEditSelectionAI}
          title="Click to prompt AI with highlighted text"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"></path>
          </svg>
          <span>
            Edit with AI: <em>"{selectedSnippet.slice(0, 22)}{selectedSnippet.length > 22 ? '...' : ''}"</em>
          </span>
          <span
            style={{
              marginLeft: '4px',
              opacity: 0.8,
              padding: '0 4px',
              cursor: 'pointer'
            }}
            onClick={(e) => {
              e.stopPropagation();
              setSelectedSnippet('');
            }}
          >
            ✕
          </span>
        </div>
      )}

      {/* Workspace Toolbar */}
      <div className="preview-toolbar">
        {/* Left: View Mode Tabs */}
        <div className="toolbar-group">
          <button
            type="button"
            className={`btn-tool ${activeTab === 'pages' ? 'active' : ''}`}
            onClick={() => setActiveTab('pages')}
            style={{
              fontWeight: 700,
              background: activeTab === 'pages' ? 'var(--color-primary)' : '#FFFFFF',
              color: activeTab === 'pages' ? '#FFFFFF' : 'var(--color-text-main)',
              borderColor: activeTab === 'pages' ? 'var(--color-primary)' : 'var(--color-border)'
            }}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
            </svg>
            Page Previews {hasPages ? `(${previewPages.length})` : ''}
          </button>

          <button
            type="button"
            className={`btn-tool ${activeTab === 'structure' ? 'active' : ''}`}
            onClick={() => setActiveTab('structure')}
            style={{
              fontWeight: 700,
              background: activeTab === 'structure' ? 'var(--color-primary)' : '#FFFFFF',
              color: activeTab === 'structure' ? '#FFFFFF' : 'var(--color-text-main)',
              borderColor: activeTab === 'structure' ? 'var(--color-primary)' : 'var(--color-border)'
            }}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
            </svg>
            Structure & AI Inspector
          </button>
        </div>

        {/* Center: Zoom Controls (Only when in page preview mode) */}
        {activeTab === 'pages' && (
          <div className="toolbar-group">
            <button
              type="button"
              className="btn-tool"
              onClick={handleZoomOut}
              disabled={!hasPages}
              title="Zoom Out"
            >
              -
            </button>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, minWidth: '40px', textAlign: 'center' }}>
              {zoom}%
            </span>
            <button
              type="button"
              className="btn-tool"
              onClick={handleZoomIn}
              disabled={!hasPages}
              title="Zoom In"
            >
              +
            </button>
            <button
              type="button"
              className="btn-tool"
              onClick={handleZoomReset}
              disabled={!hasPages}
              title="Reset Zoom"
            >
              100%
            </button>

            {/* Full Screen Preview Button */}
            <button
              type="button"
              className="btn-tool"
              onClick={toggleFullscreen}
              disabled={!hasPages}
              title="Enter Fullscreen Preview"
              style={{ fontWeight: 700, color: 'var(--color-primary)' }}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"></path>
              </svg>
              Full Screen
            </button>
          </div>
        )}

        {/* Right: Export Actions */}
        <div className="toolbar-group">
          <button
            type="button"
            className="btn-export docx"
            disabled={!hasPages || downloading}
            onClick={() => onDownload('docx')}
            title="Download official Microsoft Word document"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            Download DOCX
          </button>

          <button
            type="button"
            className="btn-export pdf"
            disabled={!hasPages || downloading}
            onClick={() => onDownload('pdf')}
            title="Download print-ready PDF"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
              <polyline points="10 9 9 9 8 9"></polyline>
            </svg>
            Download PDF
          </button>
        </div>
      </div>

      {/* AI Quick-Action Bar */}
      <div
        className="ai-quick-action-bar"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          flexWrap: 'wrap',
          background: '#F8FAFC',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-md)',
          padding: '0.5rem 0.75rem'
        }}
      >
        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-primary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
          </svg>
          AI Edit Shortcuts:
        </span>

        <button
          type="button"
          className="btn-tool"
          onClick={handleEditDeptAI}
          style={{ fontSize: '0.75rem', padding: '0.25rem 0.55rem' }}
          title="Ask AI to change department or option"
        >
          🪄 Edit Department & Option
        </button>

        <button
          type="button"
          className="btn-tool"
          onClick={handleEditTitleAI}
          style={{ fontSize: '0.75rem', padding: '0.25rem 0.55rem' }}
          title="Ask AI to polish dissertation title"
        >
          🪄 Edit Boxed Title
        </button>

        <button
          type="button"
          className="btn-tool"
          onClick={handleEditSupervisorAI}
          style={{ fontSize: '0.75rem', padding: '0.25rem 0.55rem' }}
          title="Ask AI to update supervisor & rank"
        >
          🪄 Edit Supervisor
        </button>

        {selectedSnippet && (
          <button
            type="button"
            className="btn-tool"
            onClick={handleEditSelectionAI}
            style={{
              fontSize: '0.75rem',
              padding: '0.25rem 0.55rem',
              background: '#FEF3C7',
              borderColor: '#F59E0B',
              color: '#92400E',
              fontWeight: 700
            }}
          >
            ✨ Edit Selection ("{selectedSnippet.slice(0, 18)}...") with AI
          </button>
        )}
      </div>

      {/* Main Viewport */}
      {activeTab === 'pages' ? (
        <div className="preview-viewport" ref={viewportRef}>
          {hasPages && currentImageUrl ? (
            <div
              className="preview-sheet"
              style={{
                width: `${Math.round(720 * (zoom / 100))}px`
              }}
            >
              <img
                src={currentImageUrl}
                alt={`Page ${currentPage + 1}`}
                loading="eager"
              />
            </div>
          ) : token ? (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#334155',
                height: '100%',
                minHeight: '400px',
                padding: '2rem',
                textAlign: 'center'
              }}
            >
              <div
                style={{
                  width: '48px',
                  height: '48px',
                  borderRadius: '50%',
                  background: '#EFF6FF',
                  border: '1px solid #BFDBFE',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '1rem',
                  color: 'var(--color-primary)'
                }}
              >
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                  <line x1="16" y1="13" x2="8" y2="13"></line>
                  <line x1="16" y1="17" x2="8" y2="17"></line>
                </svg>
              </div>
              <p style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--color-primary)' }}>
                Manuscript Uploaded & Audited
              </p>
              <p style={{ fontSize: '0.85rem', color: '#64748B', maxWidth: '380px', marginTop: '0.35rem', lineHeight: 1.5 }}>
                Your manuscript is active in the workspace. Click <strong>Reformat Document</strong> on the left, or switch to the <strong>Structure & AI Inspector</strong> tab above to view official Senate formatting cards.
              </p>
              <button
                type="button"
                className="btn-tool"
                style={{
                  marginTop: '1.25rem',
                  padding: '0.45rem 1rem',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  background: 'var(--color-primary)',
                  color: '#FFFFFF',
                  borderColor: 'var(--color-primary)'
                }}
                onClick={() => setActiveTab('structure')}
              >
                📋 View Structure & Senate Checklist
              </button>
            </div>
          ) : (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#94A3B8',
                height: '100%',
                minHeight: '400px'
              }}
            >
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" style={{ marginBottom: '1rem', opacity: 0.6 }}>
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
              </svg>
              <p style={{ fontSize: '0.95rem', fontWeight: 600 }}>No document loaded in workspace</p>
              <p style={{ fontSize: '0.8rem', opacity: 0.8, marginTop: '0.25rem' }}>
                Upload a manuscript or load one of the instant samples to inspect page layouts.
              </p>
            </div>
          )}
        </div>
      ) : (
        /* Document Structure & Live Highlight Inspector */
        <div
          className="structure-inspector"
          style={{
            background: '#FFFFFF',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-lg)',
            padding: '1.5rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '1.25rem',
            userSelect: 'text'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--color-border)', paddingBottom: '0.75rem' }}>
            <div>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--color-primary)' }}>
                Official Academic Manuscript Elements
              </h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                Highlight any text below with your mouse to prompt the AI Assistant to edit, rewrite, or update it.
              </p>
            </div>
            <button
              type="button"
              className="btn-tool"
              onClick={() => onPromptAI?.('Please review my manuscript structure and verify all preliminary pages and Senate formatting.')}
            >
              🪄 Prompt AI Assistant
            </button>
          </div>

          {/* 1. Header Banner & Department */}
          <div style={{ background: '#F8FAFC', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: '#64748B' }}>
                1. Institutional Header Banner (No Cameroon bilingual text / No motto)
              </span>
              <button
                type="button"
                className="btn-tool"
                style={{ fontSize: '0.7rem', padding: '0.2rem 0.5rem' }}
                onClick={handleEditDeptAI}
              >
                🪄 Edit Dept/Option
              </button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem' }}>
              <div>
                <strong style={{ fontSize: '0.8rem', color: '#334155' }}>Faculty / School:</strong>
                <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>{metadata?.faculty || 'COLLEGE OF TECHNOLOGY'}</div>
              </div>
              <div>
                <strong style={{ fontSize: '0.8rem', color: '#334155' }}>Department (Banner Right Cell):</strong>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--color-primary)' }}>
                  DEPARTMENT OF {(metadata?.department || 'Computer Engineering').toUpperCase()}
                </div>
              </div>
              <div>
                <strong style={{ fontSize: '0.8rem', color: '#334155' }}>Option / Specialization (Purpose Clause):</strong>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#0369A1' }}>
                  {metadata?.option || 'General / Not Specified'}
                </div>
              </div>
            </div>
          </div>

          {/* 2. Boxed Dissertation Title */}
          <div style={{ background: '#F8FAFC', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: '#64748B' }}>
                2. Dissertation / Project Title (Single-Line Rectangular Border Box)
              </span>
              <button
                type="button"
                className="btn-tool"
                style={{ fontSize: '0.7rem', padding: '0.2rem 0.5rem' }}
                onClick={handleEditTitleAI}
              >
                🪄 Polish Title
              </button>
            </div>
            <div
              style={{
                border: '1.5px solid #000000',
                padding: '0.85rem 1rem',
                textAlign: 'center',
                fontWeight: 700,
                fontSize: '0.95rem',
                letterSpacing: '0.02em',
                background: '#FFFFFF',
                borderRadius: '2px'
              }}
            >
              {metadata?.title || 'UNTITLED MANUSCRIPT'}
            </div>
          </div>

          {/* 3. Candidate & Supervision */}
          <div style={{ background: '#F8FAFC', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: '#64748B' }}>
                3. Candidate & Supervision Roster
              </span>
              <button
                type="button"
                className="btn-tool"
                style={{ fontSize: '0.7rem', padding: '0.2rem 0.5rem' }}
                onClick={handleEditSupervisorAI}
              >
                🪄 Edit Supervisor
              </button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem' }}>
              <div>
                <strong style={{ fontSize: '0.8rem', color: '#334155' }}>Author (Candidate):</strong>
                <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>{metadata?.author || 'N/A'}</div>
                <div style={{ fontSize: '0.75rem', color: '#64748B' }}>Matricule: {metadata?.reg_number || 'N/A'}</div>
              </div>
              <div>
                <strong style={{ fontSize: '0.8rem', color: '#334155' }}>Supervisor(s):</strong>
                <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>
                  {metadata?.supervisors?.[0] || 'N/A'}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#64748B' }}>
                  Rank: {metadata?.supervisor_ranks?.[0] || 'Associate Professor'}
                </div>
              </div>
              <div>
                <strong style={{ fontSize: '0.8rem', color: '#334155' }}>Submission Date (Bottom Page):</strong>
                <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>
                  {metadata?.submission_month || 'JUNE'} {metadata?.submission_year || '2026'}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#16A34A', fontWeight: 600 }}>
                  ✓ Anchored at bottom (56pt space)
                </div>
              </div>
            </div>
          </div>

          {/* 4. Formatting Standards Compliance Checklist */}
          <div style={{ background: '#F8FAFC', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: '#64748B', display: 'block', marginBottom: '0.5rem' }}>
              4. Senate Statutory Formatting Rules Verification
            </span>
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.8rem' }}>
              <li style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ color: '#16A34A', fontWeight: 700 }}>✓</span>
                <strong>Page Number Alignment:</strong> Centered at the bottom middle of pages.
              </li>
              <li style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ color: '#16A34A', fontWeight: 700 }}>✓</span>
                <strong>Cover & Title Pages:</strong> Unnumbered (no page numbers displayed).
              </li>
              <li style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ color: '#16A34A', fontWeight: 700 }}>✓</span>
                <strong>Preliminary Pages (Roman):</strong> Lowercase Roman numerals (<em>ii, iii, iv...</em>) starting at <em>ii</em> (Declaration of Originality).
              </li>
              <li style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ color: '#16A34A', fontWeight: 700 }}>✓</span>
                <strong>Table of Contents Width & Leaders:</strong> 15.0 cm tab stop with margin-flush dot leaders.
              </li>
              <li style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ color: '#16A34A', fontWeight: 700 }}>✓</span>
                <strong>Header Cleanliness:</strong> Bilingual Cameroon header and motto removed per statutory guidelines.
              </li>
              <li style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ color: '#16A34A', fontWeight: 700 }}>✓</span>
                <strong>Table & Figure Preservation:</strong> Tables and figures preserved in exact sequential document order.
              </li>
            </ul>
          </div>
        </div>
      )}

      {/* Page Gallery Thumbnail Ribbon */}
      {activeTab === 'pages' && hasPages && (
        <div className="page-gallery">
          {previewPages.map((url, idx) => (
            <div
              key={idx}
              className={`page-thumb ${currentPage === idx ? 'active' : ''}`}
              onClick={() => setCurrentPage(idx)}
              title={`Jump to Page ${idx + 1}`}
            >
              <img src={url} alt={`Thumb ${idx + 1}`} />
            </div>
          ))}
        </div>
      )}

      {/* True Fullscreen Modal */}
      {isFullscreen && hasPages && currentImageUrl && (
        <div className="fullscreen-modal">
          <div className="fullscreen-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <span style={{ fontWeight: 700, fontSize: '1rem' }}>
                Full Screen Manuscript Inspection
              </span>
              <span style={{ fontSize: '0.85rem', color: '#94A3B8' }}>
                Page {currentPage + 1} of {previewPages.length}
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <button
                type="button"
                className="btn-tool"
                disabled={currentPage === 0}
                onClick={() => setCurrentPage((p) => p - 1)}
              >
                ← Previous
              </button>
              <button
                type="button"
                className="btn-tool"
                disabled={currentPage === previewPages.length - 1}
                onClick={() => setCurrentPage((p) => p + 1)}
              >
                Next →
              </button>
              <button
                type="button"
                className="btn-tool"
                onClick={() => onDownload('docx')}
                style={{ background: '#1E3A8A', color: 'white', borderColor: 'transparent' }}
              >
                Export DOCX
              </button>
              <button
                type="button"
                className="btn-tool"
                onClick={() => onDownload('pdf')}
                style={{ background: '#DC2626', color: 'white', borderColor: 'transparent' }}
              >
                Export PDF
              </button>
              <button
                type="button"
                className="btn-tool"
                onClick={() => setIsFullscreen(false)}
                style={{ background: 'rgba(255,255,255,0.15)', color: 'white' }}
                title="Exit Fullscreen (or press Esc)"
              >
                ✕ Close
              </button>
            </div>
          </div>

          <div className="fullscreen-body" onClick={() => setIsFullscreen(false)}>
            <div
              className="preview-sheet"
              style={{ width: '850px', maxHeight: '90vh', overflowY: 'auto' }}
              onClick={(e) => e.stopPropagation()}
            >
              <img src={currentImageUrl} alt={`Fullscreen Page ${currentPage + 1}`} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
