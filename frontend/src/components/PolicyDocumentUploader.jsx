import React, { useRef, useState } from 'react';
import { CheckCircle2, FileUp, Loader2, X } from 'lucide-react';
import apiClient from '../services/api';

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
    <div className="policy-document-uploader">
      <input ref={inputRef} type="file" accept=".md,.txt,text/markdown,text/plain" multiple hidden onChange={handleFiles} />
      <button
        type="button"
        className="policy-upload-button"
        onClick={() => inputRef.current?.click()}
        disabled={isUploading}
        title="Upload hospital policy documents"
      >
        {isUploading ? <Loader2 size={15} className="policy-upload-spinner" /> : <FileUp size={15} />}
        {isUploading ? 'Indexing…' : 'Upload policies'}
      </button>
      {message && (
        <div className={`policy-upload-message ${message.type}`} role={message.type === 'error' ? 'alert' : 'status'}>
          {message.type === 'success' && <CheckCircle2 size={14} />}
          <span>{message.text}</span>
          <button type="button" aria-label="Dismiss upload message" onClick={() => setMessage(null)}><X size={13} /></button>
        </div>
      )}
    </div>
  );
}
