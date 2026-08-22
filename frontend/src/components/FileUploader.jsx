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
      const result = await uploadDocuments(selectedFiles);
      setUploadProgress(100);

      if (result && typeof result === 'object') {
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
    <div className="bg-surface-container rounded-2xl border border-outline-variant/20 overflow-hidden mb-8">
      <div className="p-6 border-b border-outline-variant/10 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-headline-lg font-headline-lg text-on-surface mb-1">Upload Clinical Documents</h3>
          <p className="text-body-md font-body-md text-on-surface-variant">
            Validation Service checks extension, MIME type, file size (&lt;20MB), and PDF/Image readability before queueing.
          </p>
        </div>
        <div className="px-3 py-1.5 rounded-md bg-surface-variant border border-outline-variant/30 text-label-caps font-label-caps text-secondary shrink-0">
          Validation Engine
        </div>
      </div>

      {errorMessage && (
        <div className="mx-6 mt-6 px-4 py-3 rounded-lg bg-error-container/10 border border-error/30 text-error flex justify-between items-center text-sm">
          <div className="flex items-center gap-2">
            <AlertTriangle size={18} />
            <span>{errorMessage}</span>
          </div>
          <button className="text-error/80 hover:text-error" onClick={() => setErrorMessage(null)}><X size={16} /></button>
        </div>
      )}

      {successMessage && (
        <div className="mx-6 mt-6 px-4 py-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-500 flex justify-between items-center text-sm">
          <div className="flex items-center gap-2">
            <CheckCircle size={18} />
            <span>{successMessage}</span>
          </div>
          <button className="text-emerald-500/80 hover:text-emerald-500" onClick={() => setSuccessMessage(null)}><X size={16} /></button>
        </div>
      )}
      {/* Drag & Drop Zone */}
      <div className="p-6 md:p-10">
        <div
          className={`border-2 border-dashed rounded-2xl bg-surface-container-highest/30 transition-colors duration-300 group cursor-pointer flex flex-col items-center justify-center py-16 px-6 text-center ${
            isDragging ? 'border-primary/80 bg-primary/5' : 'border-outline-variant/50 hover:border-secondary/60'
          }`}
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
          
          <div className="w-20 h-20 rounded-full bg-secondary-container/20 border border-secondary/30 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300 shadow-[0_0_20px_rgba(37,99,235,0.2)]">
            <UploadCloud className="text-4xl text-secondary w-10 h-10" />
          </div>
          
          <h4 className="text-headline-md font-headline-md text-on-surface mb-2">Drag & drop patient records here</h4>
          <p className="text-body-lg font-body-lg text-on-surface-variant mb-8">or click to browse your filesystem (bulk & mixed uploads supported)</p>
          
          <div className="flex flex-wrap justify-center gap-3">
            <span className="px-3 py-1 rounded bg-surface-variant text-label-caps font-label-caps text-on-surface-variant border border-outline-variant/20">PDF</span>
            <span className="px-3 py-1 rounded bg-surface-variant text-label-caps font-label-caps text-on-surface-variant border border-outline-variant/20">PNG</span>
            <span className="px-3 py-1 rounded bg-surface-variant text-label-caps font-label-caps text-on-surface-variant border border-outline-variant/20">JPG</span>
            <span className="px-3 py-1 rounded bg-surface-variant text-label-caps font-label-caps text-on-surface-variant border border-outline-variant/20">JPEG</span>
            <span className="px-3 py-1 rounded bg-surface-variant text-label-caps font-label-caps text-on-surface-variant border border-outline-variant/20">TIFF</span>
          </div>
        </div>
      </div>

      {/* Upload Progress Bar */}
      {isUploading && (
        <div className="h-1.5 w-full bg-outline-variant/30 overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-primary to-secondary transition-all duration-300" 
            style={{ width: `${uploadProgress}%` }} 
          />
        </div>
      )}

      {/* Selected File List */}
      {selectedFiles.length > 0 && (
        <div className="px-6 md:px-10 pb-10">
          <div className="text-sm font-semibold text-on-surface-variant mb-3">
            Files Ready for Validation & Upload ({selectedFiles.length})
          </div>
          <div className="flex flex-col gap-3">
            {selectedFiles.map((file, idx) => {
              const ext = getExtension(file.name);
              const isSupported = ALLOWED_TYPES.includes(ext);
              return (
                <div key={idx} className={`flex items-center justify-between p-3 rounded-xl border ${
                  isSupported ? 'bg-surface-variant/40 border-outline-variant/40' : 'bg-error-container/5 border-error/30'
                }`}>
                  <div className="flex items-center gap-3">
                    <FileText size={20} className={isSupported ? 'text-primary' : 'text-error'} />
                    <div>
                      <div className={`text-sm font-medium ${isSupported ? 'text-on-surface' : 'text-error/90'}`}>
                        {file.name} {!isSupported && <span className="text-error text-xs ml-2">(Will be rejected)</span>}
                      </div>
                      <div className="text-xs text-on-surface-variant/70">
                        {formatFileSize(file.size)} • {ext.toUpperCase() || 'UNKNOWN'}
                      </div>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="p-1.5 rounded-md text-on-surface-variant hover:text-error hover:bg-error-container/10 transition-colors"
                    onClick={(e) => { e.stopPropagation(); removeFile(idx); }}
                    disabled={isUploading}
                  >
                    <X size={18} />
                  </button>
                </div>
              );
            })}
          </div>

          <div className="flex justify-end gap-4 mt-6">
            <button
              type="button"
              className="px-5 py-2.5 rounded-lg font-semibold text-sm bg-surface-variant border border-outline-variant/30 text-on-surface hover:bg-surface-variant/80 transition-colors"
              onClick={() => { setSelectedFiles([]); if (fileInputRef.current) fileInputRef.current.value = ''; }}
              disabled={isUploading}
            >
              Clear All
            </button>
            <button
              type="button"
              className="px-5 py-2.5 rounded-lg font-semibold text-sm bg-gradient-to-r from-primary to-secondary text-white shadow-lg shadow-primary/20 hover:opacity-90 transition-all flex items-center gap-2 disabled:opacity-50"
              onClick={handleUploadSubmit}
              disabled={isUploading}
            >
              {isUploading ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  Validating & Ingesting...
                </>
              ) : (
                `Validate & Upload ${selectedFiles.length} File${selectedFiles.length > 1 ? 's' : ''}`
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
