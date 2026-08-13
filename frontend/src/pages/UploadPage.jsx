import React, { useState, useEffect, useRef } from 'react';
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
  Trash2,
  AlertOctagon,
  ListFilter,
  Code
} from 'lucide-react';
import FileUploader from '../components/FileUploader';
import ExtractedFieldsModal from '../components/ExtractedFieldsModal';
import { fetchDocuments, fetchDocumentStatus, deleteDocument, deleteAllDocuments, fetchUploadLogs } from '../services/api';

export default function UploadPage() {
  const [documents, setDocuments] = useState([]);
  const [uploadLogs, setUploadLogs] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('documents'); // 'documents' or 'logs'
  const [searchQuery, setSearchQuery] = useState('');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [selectedDocForFields, setSelectedDocForFields] = useState(null);
  const refreshInFlight = useRef(false);

  const loadData = async () => {
    if (refreshInFlight.current) return;
    refreshInFlight.current = true;
    setIsRefreshing(true);
    try {
      const [docsData, logsData] = await Promise.all([
        fetchDocuments(),
        fetchUploadLogs()
      ]);
      setDocuments(docsData);
      setUploadLogs(logsData);
    } catch (err) {
      console.error('Failed to load document/log repository:', err);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
      refreshInFlight.current = false;
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // --- Stable polling with exponential backoff ---
  // The previous implementation used [documents] as a dependency, which caused
  // a feedback loop: every poll updated state → state change re-ran the effect
  // → new intervals created → immediate new polls. This generated hundreds of
  // redundant requests per document.
  //
  // Fix: use a ref to track which documents need polling, and a single
  // setTimeout chain (not setInterval) with increasing delays.
  const pollingRef = useRef({});  // { [docId]: { timeoutId, delay } }

  useEffect(() => {
    const TERMINAL = new Set(['extracted', 'failed']);
    const MIN_DELAY = 2000;
    const MAX_DELAY = 15000;
    const BACKOFF_FACTOR = 1.5;

    // Determine which non-terminal docs need polling
    const activeDocs = documents.filter(
      (doc) => !TERMINAL.has((doc.status || '').toLowerCase())
    );

    // Stop polling for docs that have reached a terminal status
    const activeIds = new Set(activeDocs.map((d) => d.document_id));
    for (const [docId, entry] of Object.entries(pollingRef.current)) {
      if (!activeIds.has(docId)) {
        clearTimeout(entry.timeoutId);
        delete pollingRef.current[docId];
      }
    }

    // Start polling for new non-terminal docs (skip already-polling ones)
    for (const doc of activeDocs) {
      if (pollingRef.current[doc.document_id]) continue;

      const scheduleNext = (docId, delay) => {
        const timeoutId = setTimeout(async () => {
          if (document.visibilityState !== 'visible') {
            // Tab hidden — reschedule at same delay, don't back off
            pollingRef.current[docId] = { timeoutId: null, delay };
            scheduleNext(docId, delay);
            return;
          }
          try {
            const statusData = await fetchDocumentStatus(docId);
            setDocuments((current) =>
              current.map((item) =>
                item.document_id === docId ? { ...item, ...statusData } : item
              )
            );
            // If terminal, stop polling
            if (TERMINAL.has((statusData.status || '').toLowerCase())) {
              delete pollingRef.current[docId];
              return;
            }
          } catch (err) {
            console.error(`Failed to poll status for ${docId}:`, err);
          }
          // Schedule next poll with backoff
          const nextDelay = Math.min(delay * BACKOFF_FACTOR, MAX_DELAY);
          pollingRef.current[docId] = { timeoutId: null, delay: nextDelay };
          scheduleNext(docId, nextDelay);
        }, delay);
        pollingRef.current[docId] = { timeoutId, delay };
      };

      scheduleNext(doc.document_id, MIN_DELAY);
    }

    return () => {
      // Cleanup all timeouts on unmount
      for (const entry of Object.values(pollingRef.current)) {
        clearTimeout(entry.timeoutId);
      }
      pollingRef.current = {};
    };
  }, [documents.length]);  // Only re-run when docs are added/removed, not on status changes

  const statusLabel = (status) => ({
    queued: 'Queued',
    new: 'Queued',
    preprocessing: 'Preprocessing...',
    preprocessed: 'Detecting layout...',
    detecting_layout: 'Detecting layout...',
    layout_detected: 'Classifying...',
    classifying: 'Classifying...',
    classified: 'Extracting text...',
    extracting: 'Extracting text...',
    extracted: 'Extracted',
    failed: 'failed'
  }[(status || '').toLowerCase()] || status || 'Queued');

  const handleUploadSuccess = () => {
    loadData();
  };

  const handleDeleteDocument = async (documentId, filename) => {
    if (!window.confirm(`Delete document "${filename}"?`)) return;
    try {
      await deleteDocument(documentId);
      await loadData();
    } catch (err) {
      console.error('Failed to delete document:', err);
    }
  };

  const handleDeleteAll = async () => {
    if (!window.confirm(`Delete ALL ${documents.length} document(s)? This cannot be undone.`)) return;
    try {
      await deleteAllDocuments();
      await loadData();
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

  const filteredLogs = uploadLogs.filter((log) => {
    const q = searchQuery.toLowerCase();
    return (
      log.filename.toLowerCase().includes(q) ||
      (log.reason && log.reason.toLowerCase().includes(q)) ||
      log.status.toLowerCase().includes(q)
    );
  });

  const queuedCount = documents.filter((d) => d.status === 'QUEUED' || d.status === 'new').length;
  const rejectedLogsCount = uploadLogs.filter((l) => l.status === 'REJECTED').length;
  const acceptedLogsCount = uploadLogs.filter((l) => l.status === 'ACCEPTED').length;

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
            <p>Epic 1.1 Document Intake & Epic 1.3 Validation Engine (FR-04)</p>
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
            <span>Validation & Intake Active</span>
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
            <p>Total Documents Saved</p>
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
          <div className="stat-icon processed" style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#ef4444' }}>
            <AlertOctagon size={24} color="#ef4444" />
          </div>
          <div className="stat-info">
            <h3 style={{ color: '#ef4444' }}>{rejectedLogsCount}</h3>
            <p>Rejected Upload Logs</p>
          </div>
        </div>

        <div className="glass-card stat-card">
          <div className="stat-icon pipeline">
            <ShieldCheck size={24} />
          </div>
          <div className="stat-info">
            <h3>100%</h3>
            <p>Validated Before Queueing</p>
          </div>
        </div>
      </div>

      {/* File Uploader Section */}
      <FileUploader onUploadSuccess={handleUploadSuccess} />

      {/* Tabs & Table Section */}
      <div className="glass-card">
        <div className="section-header" style={{ borderBottom: '1px solid var(--border-light)', paddingBottom: '1rem' }}>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <button
              onClick={() => setActiveTab('documents')}
              style={{
                background: activeTab === 'documents' ? 'var(--primary-cyan)' : 'transparent',
                color: activeTab === 'documents' ? '#0f172a' : 'var(--text-muted)',
                border: 'none',
                padding: '0.5rem 1rem',
                borderRadius: '6px',
                fontWeight: '600',
                fontSize: '0.9rem',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              Queued Documents ({documents.length})
            </button>
            <button
              onClick={() => setActiveTab('logs')}
              style={{
                background: activeTab === 'logs' ? 'var(--primary-cyan)' : 'transparent',
                color: activeTab === 'logs' ? '#0f172a' : 'var(--text-muted)',
                border: 'none',
                padding: '0.5rem 1rem',
                borderRadius: '6px',
                fontWeight: '600',
                fontSize: '0.9rem',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              Upload Audit Logs ({uploadLogs.length})
            </button>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            <div style={{ position: 'relative', width: '260px' }}>
              <Search
                size={16}
                color="var(--text-muted)"
                style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }}
              />
              <input
                type="text"
                placeholder={activeTab === 'documents' ? "Search filename or ID..." : "Search logs or reasons..."}
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
              onClick={loadData}
              disabled={isRefreshing}
              style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
            >
              <RefreshCw size={14} className={isRefreshing ? 'spin' : ''} />
              Refresh
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
            Loading database repository...
          </div>
        ) : activeTab === 'documents' ? (
          /* Documents Table */
          filteredDocuments.length === 0 ? (
            <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              <Database size={36} style={{ marginBottom: '0.75rem', opacity: 0.5 }} />
              <p>No valid clinical documents found in repository.</p>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>
                Upload valid PDF, PNG, JPG, or TIFF files above to populate the QUEUED queue.
              </p>
            </div>
          ) : (
            <div className="table-responsive" style={{ marginTop: '1rem' }}>
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Filename</th>
                    <th>Document ID (UUID)</th>
                    <th>Format</th>
                    <th>Ingestion Date</th>
                    <th>Pipeline Status</th>
                    <th>Document Type</th>
                    <th>Confidence</th>
                    <th>Review Required</th>
                    <th>Extracted Fields</th>
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
                        <span className={`badge-status badge-${(doc.status || "").toUpperCase()}`}>
                          <span className="pulse-dot" style={{ width: '6px', height: '6px' }}></span>
                          {statusLabel(doc.status)}
                        </span>
                      </td>
                      <td>{doc.document_type || '-'}</td>
                      <td>{doc.classification_confidence !== null && doc.classification_confidence !== undefined ? doc.classification_confidence.toFixed(2) : '-'}</td>
                      <td>
                        {doc.needs_manual_review === true || (doc.status || '').toUpperCase() === 'UNLINKED' ? (
                          <span style={{ color: 'var(--accent-rose)', fontWeight: 'bold' }}>Yes</span>
                        ) : doc.needs_manual_review === false ? (
                          <span style={{ color: '#10b981' }}>No</span>
                        ) : '-'}
                      </td>
                      <td>
                        {(() => {
                          const isExtracted = ['EXTRACTED', 'PENDING_REVIEW', 'COMMITTED', 'VERIFIED', 'UNLINKED'].includes((doc.status || '').toUpperCase());
                          return (
                            <button
                              className="btn-view-fields"
                              onClick={() => isExtracted && setSelectedDocForFields(doc)}
                              disabled={!isExtracted}
                              title={isExtracted ? "View extracted clinical fields in JSON" : `Extraction pending (Current status: ${statusLabel(doc.status)})`}
                            >
                              <Code size={13} />
                              <span>View JSON</span>
                            </button>
                          );
                        })()}
                      </td>
                      <td>
                        <button
                          className="btn-icon"
                          title="Delete document"
                          onClick={() => handleDeleteDocument(doc.document_id, doc.filename)}
                          style={{ color: 'var(--text-dim)', cursor: 'pointer', background: 'none', border: 'none' }}
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
          )
        ) : (
          /* Upload Logs Table */
          filteredLogs.length === 0 ? (
            <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              <ListFilter size={36} style={{ marginBottom: '0.75rem', opacity: 0.5 }} />
              <p>No upload log entries recorded yet.</p>
            </div>
          ) : (
            <div className="table-responsive" style={{ marginTop: '1rem' }}>
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Filename</th>
                    <th>Validation Status</th>
                    <th>Rejection Reason</th>
                    <th>Client IP</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredLogs.map((log) => (
                    <tr key={log.id}>
                      <td style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                        {formatDate(log.timestamp)}
                      </td>
                      <td style={{ fontWeight: '600' }}>{log.filename}</td>
                      <td>
                        <span 
                          className="tag" 
                          style={{
                            background: log.status === 'REJECTED' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                            color: log.status === 'REJECTED' ? '#ef4444' : '#10b981',
                            fontWeight: '700'
                          }}
                        >
                          {log.status === 'REJECTED' ? '❌ REJECTED' : '✓ ACCEPTED'}
                        </span>
                      </td>
                      <td style={{ color: log.status === 'REJECTED' ? '#fca5a5' : 'var(--text-muted)', fontSize: '0.85rem' }}>
                        {log.reason || 'None (Validated & Queued)'}
                      </td>
                      <td style={{ fontSize: '0.85rem', color: 'var(--text-dim)' }}>
                        {log.client_ip || '127.0.0.1'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}
      </div>

      {/* Extracted Fields Modal */}
      {selectedDocForFields && (
        <ExtractedFieldsModal
          document={selectedDocForFields}
          onClose={() => setSelectedDocForFields(null)}
          onRefreshRequired={loadData}
        />
      )}
    </div>
  );
}

