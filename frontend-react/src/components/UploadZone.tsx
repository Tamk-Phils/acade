import React, { useRef, useState } from 'react';

interface UploadZoneProps {
  onFileUpload: (file: File) => void;
  onLoadSample: (sampleType: string) => void;
  loading: boolean;
  currentFilename?: string;
}

export const UploadZone: React.FC<UploadZoneProps> = ({
  onFileUpload,
  onLoadSample,
  loading,
  currentFilename
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      if (file.name.endsWith('.docx') || file.name.endsWith('.pdf')) {
        onFileUpload(file);
      } else {
        alert('Please upload a Microsoft Word (.docx) or PDF (.pdf) file.');
      }
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onFileUpload(e.target.files[0]);
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="12" y1="18" x2="12" y2="12"></line>
            <line x1="9" y1="15" x2="15" y2="15"></line>
          </svg>
          1. Upload Academic Document
        </span>
        {currentFilename && (
          <span style={{ fontSize: '0.75rem', color: '#059669', fontWeight: 600, maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            ✓ {currentFilename}
          </span>
        )}
      </div>

      <div className="card-body">
        <div
          className={`dropzone ${isDragOver ? 'dragover' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileInput}
            accept=".docx,.pdf"
            style={{ display: 'none' }}
          />

          <div className="dropzone-icon">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="17 8 12 3 7 8"></polyline>
              <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
          </div>

          <div className="dropzone-title">
            {loading ? 'Analyzing document...' : 'Click to select or drag and drop manuscript'}
          </div>
          <div className="dropzone-hint">
            Supports Microsoft Word (.docx) and Adobe PDF (.pdf) up to 50MB
          </div>
        </div>

        {/* Instant Test Samples */}
        <div style={{ marginTop: '0.85rem' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: '0.35rem' }}>
            Quick Verification Samples:
          </div>
          <div className="sample-buttons">
            <button
              type="button"
              className="btn-sample"
              disabled={loading}
              onClick={() => onLoadSample('coltech_dissertation')}
            >
              COLTECH Dissertation (.docx)
            </button>
            <button
              type="button"
              className="btn-sample"
              disabled={loading}
              onClick={() => onLoadSample('internship_report')}
            >
              Internship Report (.pdf)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

