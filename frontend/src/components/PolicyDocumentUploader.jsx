import React, { useRef, useState } from 'react';
import { CheckCircle2, FileUp, Loader2, X } from 'lucide-react';
import apiClient from '../api';

export default function PolicyDocumentUploader() {
  const inputRef = useRef(null);
  const [isUploading, setIsUploading] = useState(false);
  const [message, setMessage] = useState(null);

  const handleFiles = async (event) => {
    const files = Array.from(event.target.files || []);
    event.target.value = '';
    if (!files.length) return;

    const invalidFile = files.find((file) => !/\.(md|txt)$/i.test(file.name));
    if (invalidFile) {
      setMessage({ type: 'error', text: `${invalidFile.name} is not a Markdown or text policy file.` });
      return;
    }

    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    setMessage(null);
    setIsUploading(true);
    try {
      const response = await apiClient.post('/policy-chat/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setMessage({
        type: 'success',
        text: `${response.data.uploaded_documents.length} policy document(s) indexed (${response.data.chunks_ingested} sections).`,
      });
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Policy upload failed. Please try again.',
      });
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="flex items-center gap-3 relative">
      <input ref={inputRef} type="file" accept=".md,.txt,text/markdown,text/plain" multiple hidden onChange={handleFiles} />
      <button
        type="button"
        className="flex items-center gap-1.5 px-3 py-1.5 bg-surface border border-line hover:border-teal hover:bg-teal/5 text-teal text-sm font-bold rounded-lg transition-colors shadow-sm disabled:opacity-50"
        onClick={() => inputRef.current?.click()}
        disabled={isUploading}
        title="Upload hospital policy documents"
      >
        {isUploading ? <Loader2 size={15} className="animate-spin" /> : <FileUp size={15} />}
        {isUploading ? 'Indexing…' : 'Upload policies'}
      </button>
      
      {message && (
        <div 
          className={`absolute right-0 top-[calc(100%+0.5rem)] z-50 flex items-center gap-2 px-3 py-2 rounded-lg border shadow-[var(--shadow-float)] text-xs font-semibold whitespace-nowrap ${
            message.type === 'success' 
              ? 'bg-surface border-success/20 text-success' 
              : 'bg-surface border-danger/20 text-danger'
          }`} 
          role={message.type === 'error' ? 'alert' : 'status'}
        >
          {message.type === 'success' && <CheckCircle2 size={14} />}
          <span>{message.text}</span>
          <button type="button" className="opacity-70 hover:opacity-100 ml-2" aria-label="Dismiss upload message" onClick={() => setMessage(null)}><X size={13} /></button>
        </div>
      )}
    </div>
  );
}
