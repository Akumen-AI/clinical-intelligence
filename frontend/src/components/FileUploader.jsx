import React, { useState, useRef } from 'react';
import { 
  UploadCloud, 
  FileText, 
  X, 
  AlertTriangle, 
  CheckCircle, 
  Loader2,
  XCircle,
  FileCheck
} from 'lucide-react';
import { uploadDocuments } from '../services/api';

const ALLOWED_TYPES = ['pdf', 'png', 'jpg', 'jpeg', 'tiff'];

export default function FileUploader({ onUploadSuccess }) {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [uploadSummary, setUploadSummary] = useState(null);
  const fileInputRef = useRef(null);

  const getExtension = (filename) => {
    if (!filename || !filename.includes('.')) return '';
    return filename.split('.').pop().toLowerCase();
  };

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    if (!files.length) return;
    setSelectedFiles((prev) => [...prev, ...files]);
    setErrorMessage(null);
    setUploadSummary(null);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    if (!files.length) return;

    setSelectedFiles((prev) => [...prev, ...files]);
    setErrorMessage(null);
    setUploadSummary(null);
  };

  const removeFile = (indexToRemove) => {
    setSelectedFiles((prev) => prev.filter((_, idx) => idx !== indexToRemove));
  };

  const handleUploadSubmit = async () => {
    if (selectedFiles.length === 0) return;

    setIsUploading(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    setUploadSummary(null);
    setUploadProgress(30);

    try {
      setUploadProgress(70);
      const result = await uploadDocuments(selectedFiles);
      setUploadProgress(100);

      if (result && typeof result === 'object') {
        setUploadSummary(result);
        if (result.rejected_count > 0 && result.accepted_count > 0) {
          setErrorMessage(`Upload Warning: ${result.accepted_count} file(s) accepted & queued, ${result.rejected_count} file(s) rejected.`);
        } else if (result.accepted_count > 0) {
          setSuccessMessage(`Successfully validated and queued ${result.accepted_count} file(s)!`);
        } else if (result.rejected_count > 0) {
          setErrorMessage(`All ${result.rejected_count} file(s) were rejected.`);
        }
      }
      
      setSelectedFiles([]);
      if (fileInputRef.current) fileInputRef.current.value = '';
      
      if (onUploadSuccess) {
        onUploadSuccess(result);
      }
    } catch (err) {
      console.error('Upload Error:', err);
      let detail;
      if (err.response?.data?.detail) {
        // Server responded with a structured error (validation failure, etc.)
        detail = err.response.data.detail;
      } else if (err.code === 'ERR_NETWORK' || err.code === 'ERR_CONNECTION_REFUSED' || !err.response) {
        // Network error — backend is not reachable
        detail = 'Cannot reach the server. Please ensure the backend is running on http://localhost:8000 and try again.';
      } else {
        detail = `Upload failed (HTTP ${err.response?.status ?? 'unknown'}). Please verify file integrity and server state.`;
      }
      setErrorMessage(detail);
    } finally {
      setIsUploading(false);
      setTimeout(() => setUploadProgress(0), 800);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(2) + ' MB';
  };

  return (
    <div className="glass-card" style={{ marginBottom: '2rem' }}>
      <div className="section-header">
        <div>
          <h2 className="section-title">Upload Clinical Documents</h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
            Validation Service checks extension, MIME type, file size (&lt;20MB), and PDF/Image readability before queueing.
          </p>
        </div>
        <span className="tag" style={{ background: 'rgba(56, 189, 248, 0.15)', color: 'var(--primary-cyan)' }}>
          Epic 1.3 Validation Engine
        </span>
      </div>

      {errorMessage && (
        <div className="alert-banner error" style={{ margin: '1rem 0' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <AlertTriangle size={20} color="#ef4444" />
            <span>{errorMessage}</span>
          </div>
          <button className="btn-icon" onClick={() => setErrorMessage(null)}><X size={16} /></button>
        </div>
      )}

      {successMessage && (
        <div className="alert-banner success" style={{ margin: '1rem 0' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <CheckCircle size={20} color="#10b981" />
            <span>{successMessage}</span>
          </div>
          <button className="btn-icon" onClick={() => setSuccessMessage(null)}><X size={16} /></button>
        </div>
      )}

      {/* Batch Summary Box */}
      {uploadSummary && (
        <div className="glass-card" style={{ 
          margin: '1rem 0', 
          padding: '1.25rem', 
          background: 'rgba(15, 23, 42, 0.8)', 
          border: '1px solid var(--border-light)' 
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h4 style={{ margin: 0, fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <FileCheck size={18} color="var(--primary-cyan)" />
              Batch Upload Results ({uploadSummary.total_uploaded} Files Processed)
            </h4>
            <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.85rem' }}>
              <span className="badge-status badge-QUEUED">
                {uploadSummary.accepted_count} Accepted
              </span>
              {uploadSummary.rejected_count > 0 && (
                <span className="badge-status badge-FAILED">
                  {uploadSummary.rejected_count} Rejected
                </span>
              )}
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {/* Accepted items list */}
            {uploadSummary.accepted && uploadSummary.accepted.map((item, i) => (
              <div key={`acc-${i}`} style={{
                display: 'flex',
                justify: 'space-between',
                alignItems: 'center',
                padding: '0.5rem 0.75rem',
                background: 'rgba(16, 185, 129, 0.1)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                borderRadius: '6px',
                fontSize: '0.85rem'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <CheckCircle size={16} color="#10b981" />
                  <span style={{ fontWeight: '600', color: 'var(--text-main)' }}>{item.filename}</span>
                </div>
                <span className="tag" style={{ background: '#10b981', color: '#fff' }}>QUEUED</span>
              </div>
            ))}

            {/* Rejected items list */}
            {uploadSummary.rejected && uploadSummary.rejected.map((item, i) => (
              <div key={`rej-${i}`} style={{
                display: 'flex',
                justify: 'space-between',
                alignItems: 'center',
                padding: '0.5rem 0.75rem',
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: '6px',
                fontSize: '0.85rem'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <XCircle size={16} color="#ef4444" />
                  <span style={{ fontWeight: '600', color: '#fca5a5' }}>{item.filename}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ color: '#ef4444', fontSize: '0.8rem', fontWeight: '500' }}>
                    ❌ {item.reason}
                  </span>
                  <span className="tag" style={{ background: '#ef4444', color: '#fff' }}>REJECTED</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Drag & Drop Zone */}
      <div
        className={`dropzone-container ${isDragging ? 'active' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileSelect}
          multiple
          accept=".pdf,.png,.jpg,.jpeg,.tiff,.docx,.doc,.xls,.xlsx,.zip,.rar,.exe,.mp4,.mov"
          style={{ display: 'none' }}
        />
        
        <div className="upload-icon-wrapper">
          <UploadCloud size={32} />
        </div>
        
        <h3 className="dropzone-title">Drag & drop patient records here</h3>
        <p className="dropzone-subtitle">or click to browse your filesystem (bulk & mixed uploads supported)</p>
        
        <div className="allowed-tags">
          <span className="tag">PDF</span>
          <span className="tag">PNG</span>
          <span className="tag">JPG</span>
          <span className="tag">JPEG</span>
          <span className="tag">TIFF</span>
        </div>
      </div>

      {/* Upload Progress Bar */}
      {isUploading && (
        <div className="progress-bar-container">
          <div className="progress-bar-fill" style={{ width: `${uploadProgress}%` }} />
        </div>
      )}

      {/* Selected File List */}
      {selectedFiles.length > 0 && (
        <div className="file-preview-list">
          <div style={{ fontSize: '0.85rem', fontWeight: '600', color: 'var(--text-muted)', margin: '0.5rem 0' }}>
            Files Ready for Validation & Upload ({selectedFiles.length})
          </div>
          {selectedFiles.map((file, idx) => {
            const ext = getExtension(file.name);
            const isSupported = ALLOWED_TYPES.includes(ext);
            return (
              <div key={idx} className="file-preview-item" style={{
                borderColor: !isSupported ? 'rgba(239, 68, 68, 0.4)' : undefined,
                background: !isSupported ? 'rgba(239, 68, 68, 0.05)' : undefined
              }}>
                <div className="file-info">
                  <FileText size={20} color={isSupported ? 'var(--primary-cyan)' : '#ef4444'} />
                  <div>
                    <div className="file-name" style={{ color: isSupported ? 'var(--text-main)' : '#fca5a5' }}>
                      {file.name} {!isSupported && <span style={{ color: '#ef4444', fontSize: '0.75rem' }}>(Will be rejected)</span>}
                    </div>
                    <div className="file-size">
                      {formatFileSize(file.size)} • {ext.toUpperCase() || 'UNKNOWN'}
                    </div>
                  </div>
                </div>
                <button
                  type="button"
                  className="btn-icon"
                  onClick={() => removeFile(idx)}
                  title="Remove file"
                  disabled={isUploading}
                >
                  <X size={18} />
                </button>
              </div>
            );
          })}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1.25rem' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => { setSelectedFiles([]); setUploadSummary(null); if (fileInputRef.current) fileInputRef.current.value = ''; }}
              disabled={isUploading}
            >
              Clear All
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleUploadSubmit}
              disabled={isUploading}
            >
              {isUploading ? (
                <>
                  <Loader2 size={18} className="spin" style={{ animation: 'spin 1s linear infinite' }} />
                  Validating & Ingesting...
                </>
              ) : (
                `Validate & Upload ${selectedFiles.length} File${selectedFiles.length > 1 ? 's' : ''}`
              )}
            </button>
          </div>
        </div>
      )}

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
