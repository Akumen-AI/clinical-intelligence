import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
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
  Code,
  Filter,
  Loader2
} from 'lucide-react';
import FileUploader from '../components/FileUploader';
import ExtractedFieldsModal from '../components/ExtractedFieldsModal';
import { fetchDocuments, fetchDocumentStatus, deleteDocument, deleteAllDocuments, fetchUploadLogs } from '../services/api';

export default function UploadPage() {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState([]);
  const [uploadLogs, setUploadLogs] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('documents'); // 'documents' or 'logs'
  const [searchQuery, setSearchQuery] = useState('');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [selectedDocForFields, setSelectedDocForFields] = useState(null);
  
  // Filters
  const [filterNeedsReview, setFilterNeedsReview] = useState(false);
  const [filterDocType, setFilterDocType] = useState('');

  const refreshInFlight = useRef(false);

  const loadData = async () => {
    if (refreshInFlight.current) return;
    refreshInFlight.current = true;
    setIsRefreshing(true);
    try {
      const needsReviewParam = filterNeedsReview ? true : null;
      const docTypeParam = filterDocType || null;
      
      const [docsData, logsData] = await Promise.all([
        fetchDocuments(needsReviewParam, docTypeParam),
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
  }, [filterNeedsReview, filterDocType]); // Re-fetch when filters change

  const pollingRef = useRef({});

  useEffect(() => {
    const TERMINAL = new Set(['extracted', 'failed']);
    const MIN_DELAY = 2000;
    const MAX_DELAY = 15000;
    const BACKOFF_FACTOR = 1.5;

    const activeDocs = documents.filter(
      (doc) => !TERMINAL.has((doc.status || '').toLowerCase())
    );

    const activeIds = new Set(activeDocs.map((d) => d.document_id));
    for (const [docId, entry] of Object.entries(pollingRef.current)) {
      if (!activeIds.has(docId)) {
        clearTimeout(entry.timeoutId);
        delete pollingRef.current[docId];
      }
    }

    for (const doc of activeDocs) {
      if (pollingRef.current[doc.document_id]) continue;

      const scheduleNext = (docId, delay) => {
        const timeoutId = setTimeout(async () => {
          if (document.visibilityState !== 'visible') {
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
            if (TERMINAL.has((statusData.status || '').toLowerCase())) {
              delete pollingRef.current[docId];
              return;
            }
          } catch (err) {
            console.error(`Failed to poll status for ${docId}:`, err);
          }
          const nextDelay = Math.min(delay * BACKOFF_FACTOR, MAX_DELAY);
          pollingRef.current[docId] = { timeoutId: null, delay: nextDelay };
          scheduleNext(docId, nextDelay);
        }, delay);
        pollingRef.current[docId] = { timeoutId, delay };
      };

      scheduleNext(doc.document_id, MIN_DELAY);
    }

    return () => {
      for (const entry of Object.values(pollingRef.current)) {
        clearTimeout(entry.timeoutId);
      }
      pollingRef.current = {};
    };
  }, [documents.length]);

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

  const getStatusBadgeClass = (status) => {
    const s = (status || '').toUpperCase();
    if (s === 'QUEUED') return 'bg-amber-500/15 text-amber-500 border-amber-500/30';
    if (s === 'FAILED') return 'bg-error-container/15 text-error border-error/30';
    if (s === 'EXTRACTED' || s === 'VERIFIED') return 'bg-emerald-500/15 text-emerald-500 border-emerald-500/30';
    return 'bg-primary/15 text-primary border-primary/30';
  };

  const handleUploadSuccess = () => {
    loadData();
  };

  const handleDeleteDocument = async (e, documentId, filename) => {
    e.stopPropagation(); // Prevent row click
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

  const handleRowClick = (doc) => {
    navigate(`/review?documentId=${doc.document_id}`);
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
      {/* Header Section */}
      <header className="app-header">
        <div className="brand-wrapper">
          <div className="brand-logo" style={{ background: 'linear-gradient(135deg, var(--accent-emerald), var(--primary-cyan))' }}>
            <FileCheck size={26} color="#ffffff" />
          </div>
          <div className="brand-title">
            <h1>Document Intake Queue</h1>
            <p>Monitor and manage the document processing pipeline</p>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20">
            <div className="w-2 h-2 rounded-full bg-primary animate-pulse shadow-[0_0_8px_rgba(6,182,212,0.6)]"></div>
            <span className="text-sm font-semibold text-primary">Pipeline Active</span>
          </div>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-secondary" style={{ padding: '0.5rem 1rem' }}
          >
            API Docs <ExternalLink size={16} />
          </a>
        </div>
      </header>

      {/* Overview Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="p-6 rounded-2xl bg-surface-container border border-outline-variant/20 hover:border-outline-variant/40 transition-colors">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-body-md font-body-md text-on-surface-variant">Total Documents</h3>
            <div className="p-2 rounded-lg bg-secondary-container/20 text-secondary">
              <Layers size={20} />
            </div>
          </div>
          <div className="text-headline-display font-headline-display text-on-surface">{documents.length}</div>
        </div>

        <div className="p-6 rounded-2xl bg-surface-container border border-outline-variant/20 hover:border-outline-variant/40 transition-colors">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-body-md font-body-md text-on-surface-variant">Status: QUEUED</h3>
            <div className="p-2 rounded-lg bg-amber-500/10 text-amber-500">
              <Clock size={20} />
            </div>
          </div>
          <div className="text-headline-display font-headline-display text-on-surface">{queuedCount}</div>
        </div>

        <div className="p-6 rounded-2xl bg-surface-container border border-outline-variant/20 hover:border-outline-variant/40 transition-colors">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-body-md font-body-md text-on-surface-variant">Rejected Uploads</h3>
            <div className="p-2 rounded-lg bg-error-container/10 text-error">
              <AlertOctagon size={20} />
            </div>
          </div>
          <div className="text-headline-display font-headline-display text-error">{rejectedLogsCount}</div>
        </div>

        <div className="p-6 rounded-2xl bg-surface-container border border-outline-variant/20 hover:border-outline-variant/40 transition-colors">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-body-md font-body-md text-on-surface-variant">Validated Initial</h3>
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-500">
              <ShieldCheck size={20} />
            </div>
          </div>
          <div className="text-headline-display font-headline-display text-on-surface">100%</div>
        </div>
      </div>

      {/* File Uploader Section */}
      <FileUploader onUploadSuccess={handleUploadSuccess} />

      {/* Filters and Search */}
      <div className="flex flex-col md:flex-row justify-between gap-4 mb-6">
        <div className="flex items-center gap-4">
          <button
            onClick={() => setActiveTab('documents')}
            className={`px-4 py-2 rounded-lg font-semibold text-sm transition-colors ${
              activeTab === 'documents' ? 'bg-primary text-on-primary' : 'text-on-surface-variant hover:bg-surface-variant'
            }`}
          >
            Queued Documents ({documents.length})
          </button>
          <button
            onClick={() => setActiveTab('logs')}
            className={`px-4 py-2 rounded-lg font-semibold text-sm transition-colors ${
              activeTab === 'logs' ? 'bg-primary text-on-primary' : 'text-on-surface-variant hover:bg-surface-variant'
            }`}
          >
            Upload Audit Logs ({uploadLogs.length})
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-4">
          {activeTab === 'documents' && (
            <>
              {/* Needs Review Filter */}
              <label className="flex items-center gap-2 cursor-pointer">
                <div className="relative">
                  <input type="checkbox" className="sr-only" checked={filterNeedsReview} onChange={(e) => setFilterNeedsReview(e.target.checked)} />
                  <div className={`block w-10 h-6 rounded-full transition-colors ${filterNeedsReview ? 'bg-primary' : 'bg-surface-variant'}`}></div>
                  <div className={`dot absolute left-1 top-1 bg-white w-4 h-4 rounded-full transition-transform ${filterNeedsReview ? 'transform translate-x-4' : ''}`}></div>
                </div>
                <span className="text-sm font-semibold text-on-surface-variant">Needs Review</span>
              </label>

              {/* Doc Type Dropdown */}
              <div className="relative">
                <select
                  className="appearance-none bg-surface-container border border-outline-variant/30 text-on-surface text-sm rounded-lg pl-3 pr-8 py-2 focus:outline-none focus:border-primary"
                  value={filterDocType}
                  onChange={(e) => setFilterDocType(e.target.value)}
                >
                  <option value="">All Document Types</option>
                  <option value="Prescription">Prescription</option>
                  <option value="Lab Report">Lab Report</option>
                  <option value="Discharge Summary">Discharge Summary</option>
                  <option value="Referral">Referral</option>
                  <option value="Admission Form">Admission Form</option>
                  <option value="Unknown">Unknown</option>
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-on-surface-variant">
                  <Filter size={14} />
                </div>
              </div>
            </>
          )}

          <div className="relative w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant w-4 h-4" />
            <input
              type="text"
              placeholder="Search..."
              className="w-full bg-surface-container border border-outline-variant/30 text-on-surface text-sm rounded-lg pl-9 pr-3 py-2 focus:outline-none focus:border-primary placeholder-on-surface-variant/50"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <button
            onClick={loadData}
            disabled={isRefreshing}
            className="p-2 rounded-lg bg-surface-variant border border-outline-variant/30 text-on-surface hover:bg-surface-variant/80 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={18} className={isRefreshing ? 'animate-spin' : ''} />
          </button>
          
          {documents.length > 0 && (
            <button
              onClick={handleDeleteAll}
              className="p-2 rounded-lg bg-error-container/10 border border-error/30 text-error hover:bg-error-container/20 transition-colors"
              title="Delete All Documents"
            >
              <Trash2 size={18} />
            </button>
          )}
        </div>
      </div>

      {/* Table Area */}
      <div className="bg-surface-container rounded-xl border border-outline-variant/20 overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-on-surface-variant">
            <Loader2 size={32} className="animate-spin mx-auto mb-4 text-primary" />
            <p>Loading database repository...</p>
          </div>
        ) : activeTab === 'documents' ? (
          filteredDocuments.length === 0 ? (
            <div className="p-16 text-center text-on-surface-variant">
              <Database size={48} className="mx-auto mb-4 opacity-50" />
              <p className="text-lg font-semibold text-on-surface mb-2">No documents found.</p>
              <p className="text-sm">Upload files above or adjust your search/filters.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead className="bg-surface-container-high border-b border-outline-variant/20 text-on-surface-variant font-label-caps text-xs uppercase tracking-wider">
                  <tr>
                    <th className="px-6 py-4 font-semibold">Filename</th>
                    <th className="px-6 py-4 font-semibold">Format</th>
                    <th className="px-6 py-4 font-semibold">Ingestion Date</th>
                    <th className="px-6 py-4 font-semibold">Status</th>
                    <th className="px-6 py-4 font-semibold">Document Type</th>
                    <th className="px-6 py-4 font-semibold">Confidence</th>
                    <th className="px-6 py-4 font-semibold">Review</th>
                    <th className="px-6 py-4 font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/10">
                  {filteredDocuments.map((doc) => (
                    <tr 
                      key={doc.document_id} 
                      className="hover:bg-surface-variant/30 transition-colors cursor-pointer"
                      onClick={() => handleRowClick(doc)}
                    >
                      <td className="px-6 py-4 font-semibold text-on-surface">
                        <div className="max-w-[200px] truncate" title={doc.filename}>{doc.filename}</div>
                        <div className="text-[10px] text-primary font-data-tabular mt-1">{doc.document_id.substring(0, 13)}...</div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="px-2 py-1 rounded bg-surface-variant text-[10px] font-bold text-on-surface-variant uppercase border border-outline-variant/20">
                          {doc.filetype}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-on-surface-variant text-xs">
                        {formatDate(doc.uploaded_at)}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase border ${getStatusBadgeClass(doc.status)}`}>
                          <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse"></span>
                          {statusLabel(doc.status)}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-on-surface-variant">
                        {doc.document_type || '-'}
                      </td>
                      <td className="px-6 py-4 font-data-tabular">
                        {doc.extraction_confidence != null ? (
                          <div className="flex items-center gap-1.5 cursor-help" title="Overall Extraction Confidence">
                            <span className="text-primary font-medium">{doc.extraction_confidence.toFixed(2)}</span>
                            <Database size={12} className="text-primary/70" />
                          </div>
                        ) : doc.classification_confidence != null ? (
                          <div className="flex items-center gap-1.5 cursor-help text-on-surface-variant/70" title="Classification Confidence">
                            <span>{doc.classification_confidence.toFixed(2)}</span>
                            <Layers size={12} />
                          </div>
                        ) : (
                          <span className="text-on-surface-variant">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        {doc.needs_manual_review === true || (doc.status || '').toUpperCase() === 'UNLINKED' ? (
                          <span className="px-2 py-1 rounded bg-error-container/20 text-error text-xs font-bold border border-error/30">Needs Review</span>
                        ) : doc.needs_manual_review === false && ['EXTRACTED', 'VERIFIED', 'COMMITTED'].includes((doc.status || '').toUpperCase()) ? (
                          <span className="text-emerald-500 text-xs font-bold">Verified</span>
                        ) : <span className="text-on-surface-variant">-</span>}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <button
                            className="p-1.5 rounded-md text-on-surface-variant hover:text-primary hover:bg-primary/10 transition-colors disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-on-surface-variant"
                            onClick={(e) => { e.stopPropagation(); setSelectedDocForFields(doc); }}
                            disabled={!['EXTRACTED', 'PENDING_REVIEW', 'COMMITTED', 'VERIFIED', 'UNLINKED'].includes((doc.status || '').toUpperCase())}
                            title="View extracted JSON"
                          >
                            <Code size={18} />
                          </button>
                          <button
                            className="p-1.5 rounded-md text-on-surface-variant hover:text-error hover:bg-error-container/10 transition-colors"
                            title="Delete document"
                            onClick={(e) => handleDeleteDocument(e, doc.document_id, doc.filename)}
                          >
                            <Trash2 size={18} />
                          </button>
                        </div>
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
            <div className="p-16 text-center text-on-surface-variant">
              <ListFilter size={48} className="mx-auto mb-4 opacity-50" />
              <p className="text-lg font-semibold text-on-surface mb-2">No upload log entries recorded yet.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead className="bg-surface-container-high border-b border-outline-variant/20 text-on-surface-variant font-label-caps text-xs uppercase tracking-wider">
                  <tr>
                    <th className="px-6 py-4 font-semibold">Timestamp</th>
                    <th className="px-6 py-4 font-semibold">Filename</th>
                    <th className="px-6 py-4 font-semibold">Validation Status</th>
                    <th className="px-6 py-4 font-semibold">Rejection Reason</th>
                    <th className="px-6 py-4 font-semibold">Client IP</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/10">
                  {filteredLogs.map((log) => (
                    <tr key={log.id} className="hover:bg-surface-variant/30 transition-colors">
                      <td className="px-6 py-4 text-on-surface-variant text-xs">
                        {formatDate(log.timestamp)}
                      </td>
                      <td className="px-6 py-4 font-semibold text-on-surface max-w-[250px] truncate" title={log.filename}>
                        {log.filename}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded text-[10px] font-bold uppercase border ${
                          log.status === 'REJECTED' 
                            ? 'bg-error-container/20 text-error border-error/30' 
                            : 'bg-emerald-500/15 text-emerald-500 border-emerald-500/30'
                        }`}>
                          {log.status === 'REJECTED' ? '❌ REJECTED' : '✓ ACCEPTED'}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`text-xs ${log.status === 'REJECTED' ? 'text-error/80 font-medium' : 'text-on-surface-variant'}`}>
                          {log.reason || 'None (Validated & Queued)'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-on-surface-variant text-xs font-data-tabular">
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
