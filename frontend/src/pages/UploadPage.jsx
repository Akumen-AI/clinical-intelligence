import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  FileCheck, 
  Clock, 
  Layers, 
  RefreshCw, 
  Search, 
  Database,
  ExternalLink,
  ShieldCheck,
  Trash2
} from 'lucide-react';
import FileUploader from '../components/FileUploader';
import { fetchDocuments, deleteDocument, deleteAllDocuments } from '../services/api';

export default function UploadPage() {
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isRefreshing, setIsRefreshing] = useState(false);

  const loadDocumentsList = async () => {
    setIsRefreshing(true);
    try {
      const data = await fetchDocuments();
      setDocuments(data);
    } catch (err) {
      console.error('Failed to load document list:', err);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadDocumentsList();
  }, []);

  const handleUploadSuccess = () => {
    loadDocumentsList();
  };

  const handleDeleteDocument = async (documentId, filename) => {
    if (!window.confirm(`Delete document "${filename}"?`)) return;
    try {
      await deleteDocument(documentId);
      loadDocumentsList();
    } catch (err) {
      console.error('Failed to delete document:', err);
    }
  };

  const handleDeleteAll = async () => {
    if (!window.confirm(`Delete ALL ${documents.length} document(s)? This cannot be undone.`)) return;
    try {
      await deleteAllDocuments();
      loadDocumentsList();
    } catch (err) {
      console.error('Failed to delete all documents:', err);
    }
  };

  const filteredDocuments = documents.filter((doc) => {
    const q = searchQuery.toLowerCase();
    return (
      doc.filename.toLowerCase().includes(q) ||
      doc.document_id.toLowerCase().includes(q) ||
      doc.filetype.toLowerCase().includes(q)
    );
  });

  const queuedCount = documents.filter((d) => d.status === 'QUEUED').length;
  const verifiedCount = documents.filter((d) => d.status === 'VERIFIED').length;

  const formatDate = (isoString) => {
    if (!isoString) return 'N/A';
    const dt = new Date(isoString);
    return dt.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  return (
    <div className="app-container">
      {/* Platform Header */}
      <header className="app-header">
        <div className="brand-wrapper">
          <div className="brand-logo">
            <Activity size={28} />
          </div>
          <div className="brand-title">
            <h1>AI Clinical Intelligence Platform</h1>
            <p>Epic 1.1 Document Intake & Ingestion Engine (FR-01)</p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-secondary"
            style={{ textDecoration: 'none', fontSize: '0.85rem' }}
          >
            FastAPI Swagger Docs <ExternalLink size={14} />
          </a>
          <div className="pipeline-badge">
            <div className="pulse-dot"></div>
            <span>Pipeline Entry Point</span>
          </div>
        </div>
      </header>

      {/* Overview Stat Cards */}
      <div className="stats-grid">
        <div className="glass-card stat-card">
          <div className="stat-icon total">
            <Layers size={24} />
          </div>
          <div className="stat-info">
            <h3>{documents.length}</h3>
            <p>Total Documents Ingested</p>
          </div>
        </div>

        <div className="glass-card stat-card">
          <div className="stat-icon queued">
            <Clock size={24} />
          </div>
          <div className="stat-info">
            <h3>{queuedCount}</h3>
            <p>Status: QUEUED (Epic 1.1)</p>
          </div>
        </div>

        <div className="glass-card stat-card">
          <div className="stat-icon processed">
            <FileCheck size={24} />
          </div>
          <div className="stat-info">
            <h3>{verifiedCount}</h3>
            <p>Verified Records</p>
          </div>
        </div>

        <div className="glass-card stat-card">
          <div className="stat-icon pipeline">
            <ShieldCheck size={24} />
          </div>
          <div className="stat-info">
            <h3>Ready</h3>
            <p>Epic 1.2 Hand-off Hook</p>
          </div>
        </div>
      </div>

      {/* File Uploader Section */}
      <FileUploader onUploadSuccess={handleUploadSuccess} />

      {/* Document Records Table Section */}
      <div className="glass-card">
        <div className="section-header">
          <h2 className="section-title">Ingested Document Repository</h2>
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            <div style={{ position: 'relative', width: '260px' }}>
              <Search
                size={16}
                color="var(--text-muted)"
                style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }}
              />
              <input
                type="text"
                placeholder="Search by filename or ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.5rem 0.75rem 0.5rem 2.25rem',
                  background: 'rgba(15, 23, 42, 0.6)',
                  border: '1px solid var(--border-light)',
                  borderRadius: 'var(--radius-sm)',
                  color: 'var(--text-main)',
                  fontSize: '0.85rem',
                  outline: 'none'
                }}
              />
            </div>

            <button
              className="btn btn-secondary"
              onClick={loadDocumentsList}
              disabled={isRefreshing}
              style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
            >
              <RefreshCw size={14} className={isRefreshing ? 'spin' : ''} />
              Refresh Table
            </button>
            {documents.length > 0 && (
              <button
                className="btn btn-secondary"
                onClick={handleDeleteAll}
                style={{
                  padding: '0.5rem 1rem',
                  fontSize: '0.85rem',
                  color: 'var(--accent-rose)',
                  borderColor: 'rgba(239, 68, 68, 0.3)'
                }}
              >
                <Trash2 size={14} />
                Delete All
              </button>
            )}
          </div>
        </div>

        {isLoading ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            Loading document repository...
          </div>
        ) : filteredDocuments.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            <Database size={36} style={{ marginBottom: '0.75rem', opacity: 0.5 }} />
            <p>No clinical documents found in the database repository.</p>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>
              Upload files above to generate UUID document IDs and queue them for processing.
            </p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Filename</th>
                  <th>Document ID (UUID)</th>
                  <th>Format</th>
                  <th>Ingestion Date</th>
                  <th>Status</th>
                  <th>Document Type</th>
                  <th>Confidence</th>
                  <th>Review Required</th>
                  <th style={{ width: '60px' }}></th>
                </tr>
              </thead>
              <tbody>
                {filteredDocuments.map((doc) => (
                  <tr key={doc.document_id}>
                    <td style={{ fontWeight: '600' }}>{doc.filename}</td>
                    <td>
                      <span className="uuid-text">{doc.document_id}</span>
                    </td>
                    <td>
                      <span className="tag" style={{ textTransform: 'uppercase' }}>
                        {doc.filetype}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                      {formatDate(doc.uploaded_at)}
                    </td>
                    <td>
                      <span className={`badge-status badge-${doc.status}`}>
                        <span className="pulse-dot" style={{ width: '6px', height: '6px' }}></span>
                        {doc.status}
                      </span>
                    </td>
                    <td>{doc.document_type || '-'}</td>
                    <td>{doc.classification_confidence !== null && doc.classification_confidence !== undefined ? doc.classification_confidence.toFixed(2) : '-'}</td>
                    <td>
                      {doc.needs_manual_review === true ? (
                        <span style={{ color: 'var(--accent-rose)', fontWeight: 'bold' }}>Yes</span>
                      ) : doc.needs_manual_review === false ? (
                        <span style={{ color: '#10b981' }}>No</span>
                      ) : '-'}
                    </td>
                    <td>
                      <button
                        className="btn-icon"
                        title="Delete document"
                        onClick={() => handleDeleteDocument(doc.document_id, doc.filename)}
                        style={{ color: 'var(--text-dim)', cursor: 'pointer' }}
                        onMouseOver={(e) => e.currentTarget.style.color = 'var(--accent-rose)'}
                        onMouseOut={(e) => e.currentTarget.style.color = 'var(--text-dim)'}
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
