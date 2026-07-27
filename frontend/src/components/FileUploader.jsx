import React, { useState, useRef } from 'react';
import { UploadCloud, FileText, X, AlertTriangle, CheckCircle, Loader2 } from 'lucide-react';
import { uploadDocuments } from '../services/api';

const ALLOWED_TYPES = ['pdf', 'png', 'jpg', 'jpeg', 'tiff'];

export default function FileUploader({ onUploadSuccess }) {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const fileInputRef = useRef(null);

  const getExtension = (filename) => {
    if (!filename || !filename.includes('.')) return '';
    return filename.split('.').pop().toLowerCase();
  };

  const validateFiles = (filesArray) => {
    const valid = [];
    const invalid = [];

    filesArray.forEach((file) => {
      const ext = getExtension(file.name);
      if (ALLOWED_TYPES.includes(ext)) {
        valid.push(file);
      } else {
        invalid.push(file.name);
      }
    });

    if (invalid.length > 0) {
      setErrorMessage(
        `Unsupported file type(s): ${invalid.join(', ')}. Only PDF, PNG, JPG, JPEG, and TIFF files are permitted.`
      );
    } else {
      setErrorMessage(null);
    }

    return valid;
  };

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    if (!files.length) return;
    
    const validFiles = validateFiles(files);
    setSelectedFiles((prev) => [...prev, ...validFiles]);
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

    const validFiles = validateFiles(files);
    setSelectedFiles((prev) => [...prev, ...validFiles]);
  };

  const removeFile = (indexToRemove) => {
    setSelectedFiles((prev) => prev.filter((_, idx) => idx !== indexToRemove));
  };

  const handleUploadSubmit = async () => {
    if (selectedFiles.length === 0) return;

    setIsUploading(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    setUploadProgress(30);

    try {
      setUploadProgress(70);
      const results = await uploadDocuments(selectedFiles);
      setUploadProgress(100);
      
      setSuccessMessage(
        `Successfully uploaded and queued ${results.length} clinical document(s)!`
      );
      setSelectedFiles([]);
      if (fileInputRef.current) fileInputRef.current.value = '';
      
      if (onUploadSuccess) {
        onUploadSuccess(results);
      }
    } catch (err) {
      console.error('Upload Error:', err);
      const detail = err.response?.data?.detail || 'Document upload failed. Please verify network and backend connection.';
      setErrorMessage(detail);
    } finally {
      setIsUploading(false);
      setTimeout(() => setUploadProgress(0), 1000);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(2) + ' MB';
  };

  return (
    <div className="glass-card" style={{ marginBottom: '2rem' }}>
      <div className="section-header">
        <h2 className="section-title">Upload Clinical Documents</h2>
        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Epic 1.1 Intake</span>
      </div>

      {errorMessage && (
        <div className="alert-banner error">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <AlertTriangle size={18} />
            <span>{errorMessage}</span>
          </div>
          <button className="btn-icon" onClick={() => setErrorMessage(null)}><X size={16} /></button>
        </div>
      )}

      {successMessage && (
        <div className="alert-banner success">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <CheckCircle size={18} />
            <span>{successMessage}</span>
          </div>
          <button className="btn-icon" onClick={() => setSuccessMessage(null)}><X size={16} /></button>
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
          accept=".pdf,.png,.jpg,.jpeg,.tiff"
          style={{ display: 'none' }}
        />
        
        <div className="upload-icon-wrapper">
          <UploadCloud size={32} />
        </div>
        
        <h3 className="dropzone-title">Drag & drop patient records here</h3>
        <p className="dropzone-subtitle">or click to browse your filesystem (bulk upload supported)</p>
        
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
            Selected Files ({selectedFiles.length})
          </div>
          {selectedFiles.map((file, idx) => (
            <div key={idx} className="file-preview-item">
              <div className="file-info">
                <FileText size={20} color="var(--primary-cyan)" />
                <div>
                  <div className="file-name">{file.name}</div>
                  <div className="file-size">{formatFileSize(file.size)} • {file.type || getExtension(file.name).toUpperCase()}</div>
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
          ))}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1.25rem' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => { setSelectedFiles([]); if (fileInputRef.current) fileInputRef.current.value = ''; }}
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
                  Processing Upload...
                </>
              ) : (
                `Upload ${selectedFiles.length} File${selectedFiles.length > 1 ? 's' : ''}`
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
