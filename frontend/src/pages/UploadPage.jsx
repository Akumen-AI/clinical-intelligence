import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
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
import { fetchDocuments, fetchDocumentStatus, deleteDocument, deleteAllDocuments, fetchUploadLogs, getWatchedFolderConfig, updateWatchedFolderConfig } from '../api';

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

  const { user } = useAuth();
  const [watchFolderPath, setWatchFolderPath] = useState('');
  const [isSavingConfig, setIsSavingConfig] = useState(false);
  const [toastMsg, setToastMsg] = useState(null);

  const refreshInFlight = useRef(false);

  const loadData = async () => {
    if (refreshInFlight.current) return;
    refreshInFlight.current = true;
    setIsRefreshing(true);
    try {
      const needsReviewParam = filterNeedsReview ? true : null;
      const docTypeParam = filterDocType || null;
      
      try {
        const docsData = await fetchDocuments(needsReviewParam, docTypeParam);
        setDocuments(docsData);
      } catch (err) {
        console.error('Failed to load documents:', err);
      }

      try {
        const logsData = await fetchUploadLogs();
        setUploadLogs(logsData);
      } catch (err) {
        console.error('Failed to load upload logs:', err);
      }
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
      refreshInFlight.current = false;
    }
  };

  const loadConfig = async () => {
    if (user && user.role && user.role.toLowerCase() === 'hospital_admin') {
      try {
        const config = await getWatchedFolderConfig();
        setWatchFolderPath(config.path);
      } catch (err) {
        console.error('Failed to load watched folder config', err);
      }
    }
  };

  useEffect(() => {
    loadData();
    loadConfig();
  }, [filterNeedsReview, filterDocType, user]); // Re-fetch when filters change

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
    if (s === 'QUEUED') return 'bg-warning/15 text-warning border-warning/30';
    if (s === 'FAILED') return 'bg-danger/15 text-danger border-danger/30';
    if (s === 'EXTRACTED' || s === 'VERIFIED') return 'bg-success/15 text-success border-success/30';
    return 'bg-teal/15 text-teal border-teal/30';
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

  const handleSaveConfig = async () => {
    setIsSavingConfig(true);
    setToastMsg(null);
    try {
      const result = await updateWatchedFolderConfig(watchFolderPath);
      setWatchFolderPath(result.path);
      setToastMsg({ type: 'success', msg: 'Watched folder path updated successfully.' });
      setTimeout(() => setToastMsg(null), 3000);
    } catch (err) {
      setToastMsg({ type: 'error', msg: err.response?.data?.detail || 'Failed to update watched folder path.' });
      setTimeout(() => setToastMsg(null), 5000);
    } finally {
      setIsSavingConfig(false);
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
      {/* Header Section */}
      <header className="app-header">
        <div className="brand-wrapper">
          <div className="w-12 h-12 rounded-xl bg-teal/10 flex items-center justify-center text-teal border border-teal/20">
            <FileCheck size={26} color="#ffffff" />
          </div>
          <div className="brand-title">
            <h1>Document Intake Queue</h1>
            <p>Monitor and manage the document processing pipeline</p>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-teal/10 border border-teal/20">
            <div className="w-2 h-2 rounded-full bg-teal animate-pulse shadow-[0_0_8px_rgba(6,182,212,0.6)]"></div>
            <span className="text-sm font-semibold text-teal">Pipeline Active</span>
          </div>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 bg-surface text-ink border border-line rounded-lg font-bold hover:bg-paper transition-colors" style={{ padding: '0.5rem 1rem' }}
          >
            API Docs <ExternalLink size={16} />
          </a>
        </div>
      </header>

      {/* Overview Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="p-6 rounded-2xl bg-surface border border-line/20 hover:border-line/40 transition-colors">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate">Total Documents</h3>
            <div className="p-2 rounded-lg bg-slate-container/20 text-slate">
              <Layers size={20} />
            </div>
          </div>
          <div className="text-4xl font-bold text-ink">{documents.length}</div>
        </div>

        <div className="p-6 rounded-2xl bg-surface border border-line/20 hover:border-line/40 transition-colors">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate">Status: QUEUED</h3>
            <div className="p-2 rounded-lg bg-warning/10 text-warning">
              <Clock size={20} />
            </div>
          </div>
          <div className="text-4xl font-bold text-ink">{queuedCount}</div>
        </div>

        <div className="p-6 rounded-2xl bg-surface border border-line/20 hover:border-line/40 transition-colors">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate">Rejected Uploads</h3>
            <div className="p-2 rounded-lg bg-danger/10 text-danger">
              <AlertOctagon size={20} />
            </div>
          </div>
          <div className="text-4xl font-bold text-danger">{rejectedLogsCount}</div>
        </div>

        <div className="p-6 rounded-2xl bg-surface border border-line/20 hover:border-line/40 transition-colors">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate">Validated Initial</h3>
            <div className="p-2 rounded-lg bg-success/10 text-success">
              <ShieldCheck size={20} />
            </div>
          </div>
          <div className="text-4xl font-bold text-ink">100%</div>
        </div>
      </div>

      {/* Settings Card for Hospital Admin */}
      {user && user.role && user.role.toLowerCase() === 'hospital_admin' && (
        <div className="bg-surface rounded-xl border border-line/20 p-6 mb-8">
          <div className="flex items-center gap-2 mb-2">
            <Database size={20} className="text-teal" />
            <h3 className="text-lg font-semibold text-ink">Scanner Watch Folder</h3>
          </div>
          <p className="text-sm text-slate mb-4">
            Specify an absolute folder path on the server where the backend is running.
            The system will automatically monitor this directory and ingest newly scanned files.
          </p>
          <div className="flex items-center gap-4">
            <input
              type="text"
              value={watchFolderPath}
              onChange={(e) => setWatchFolderPath(e.target.value)}
              placeholder="/var/lib/scanner_intake"
              className="flex-1 bg-paper border border-line/30 text-ink text-sm rounded-lg px-4 py-2 focus:outline-none focus:border-teal"
            />
            <button
              onClick={handleSaveConfig}
              disabled={isSavingConfig || !watchFolderPath.trim()}
              className="px-4 py-2 bg-teal text-white rounded-lg font-bold hover:bg-teal/90 transition-colors"
            >
              {isSavingConfig ? 'Saving...' : 'Save Path'}
            </button>
          </div>
        </div>
      )}

      {/* File Uploader Section */}
      <FileUploader onUploadSuccess={handleUploadSuccess} />

      {/* Filters and Search */}
      <div className="flex flex-col md:flex-row justify-between gap-4 mb-6">
        <div className="flex items-center gap-4">
          <button
            onClick={() => setActiveTab('documents')}
            className={`px-4 py-2 rounded-lg font-semibold text-sm transition-colors ${
              activeTab === 'documents' ? 'bg-teal text-white' : 'text-slate hover:bg-paper'
            }`}
          >
            Queued Documents ({documents.length})
          </button>
          <button
            onClick={() => setActiveTab('logs')}
            className={`px-4 py-2 rounded-lg font-semibold text-sm transition-colors ${
              activeTab === 'logs' ? 'bg-teal text-white' : 'text-slate hover:bg-paper'
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
                  <div className={`block w-10 h-6 rounded-full transition-colors ${filterNeedsReview ? 'bg-teal' : 'bg-paper'}`}></div>
                  <div className={`dot absolute left-1 top-1 bg-white w-4 h-4 rounded-full transition-transform ${filterNeedsReview ? 'transform translate-x-4' : ''}`}></div>
                </div>
                <span className="text-sm font-semibold text-slate">Needs Review</span>
              </label>

              {/* Doc Type Dropdown */}
              <div className="relative">
                <select
                  className="appearance-none bg-surface border border-line/30 text-ink text-sm rounded-lg pl-3 pr-8 py-2 focus:outline-none focus:border-teal"
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
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate">
                  <Filter size={14} />
                </div>
              </div>
            </>
          )}

          <div className="relative w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate w-4 h-4" />
            <input
              type="text"
              placeholder="Search..."
              className="w-full bg-surface border border-line/30 text-ink text-sm rounded-lg pl-9 pr-3 py-2 focus:outline-none focus:border-teal placeholder-on-surface-variant/50"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <button
            onClick={loadData}
            disabled={isRefreshing}
            className="p-2 rounded-lg bg-paper border border-line/30 text-ink hover:bg-paper/80 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={18} className={isRefreshing ? 'animate-spin' : ''} />
          </button>
          
          {documents.length > 0 && (
            <button
              onClick={handleDeleteAll}
              className="p-2 rounded-lg bg-danger/10 border border-danger/30 text-danger hover:bg-danger/20 transition-colors"
              title="Delete All Documents"
            >
              <Trash2 size={18} />
            </button>
          )}
        </div>
      </div>

      {/* Table Area */}
      <div className="bg-surface rounded-xl border border-line/20 overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-slate">
            <Loader2 size={32} className="animate-spin mx-auto mb-4 text-teal" />
            <p>Loading database repository...</p>
          </div>
        ) : activeTab === 'documents' ? (
          filteredDocuments.length === 0 ? (
            <div className="p-16 text-center text-slate">
              <Database size={48} className="mx-auto mb-4 opacity-50" />
              <p className="text-lg font-semibold text-ink mb-2">No documents found.</p>
              <p className="text-sm">Upload files above or adjust your search/filters.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead className="bg-paper border-b border-line/20 text-slate font-bold text-xs uppercase tracking-wider">
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
                      className="hover:bg-paper/30 transition-colors cursor-pointer"
                      onClick={() => handleRowClick(doc)}
                    >
                      <td className="px-6 py-4 font-semibold text-ink">
                        <div className="max-w-[200px] truncate" title={doc.filename}>{doc.filename}</div>
                        <div className="text-[10px] text-teal font-mono mt-1">{doc.document_id.substring(0, 13)}...</div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="px-2 py-1 rounded bg-paper text-[10px] font-bold text-slate uppercase border border-line/20">
                          {doc.filetype}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate text-xs">
                        {formatDate(doc.uploaded_at)}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase border ${getStatusBadgeClass(doc.status)}`}>
                          <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse"></span>
                          {statusLabel(doc.status)}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate">
                        {doc.document_type || '-'}
                      </td>
                      <td className="px-6 py-4 font-mono">
                        {doc.extraction_confidence != null ? (
                          <div className="flex items-center gap-1.5 cursor-help" title="Overall Extraction Confidence">
                            <span className="text-teal font-medium">{doc.extraction_confidence.toFixed(2)}</span>
                            <Database size={12} className="text-teal/70" />
                          </div>
                        ) : doc.classification_confidence != null ? (
                          <div className="flex items-center gap-1.5 cursor-help text-slate/70" title="Classification Confidence">
                            <span>{doc.classification_confidence.toFixed(2)}</span>
                            <Layers size={12} />
                          </div>
                        ) : (
                          <span className="text-slate">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        {doc.needs_manual_review === true || (doc.status || '').toUpperCase() === 'UNLINKED' ? (
                          <span className="px-2 py-1 rounded bg-danger/20 text-danger text-xs font-bold border border-danger/30">Needs Review</span>
                        ) : doc.needs_manual_review === false && ['EXTRACTED', 'VERIFIED', 'COMMITTED'].includes((doc.status || '').toUpperCase()) ? (
                          <span className="text-success text-xs font-bold">Verified</span>
                        ) : <span className="text-slate">-</span>}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <button
                            className="p-1.5 rounded-md text-slate hover:text-teal hover:bg-teal/10 transition-colors disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-slate"
                            onClick={(e) => { e.stopPropagation(); setSelectedDocForFields(doc); }}
                            disabled={!['EXTRACTED', 'PENDING_REVIEW', 'COMMITTED', 'VERIFIED', 'UNLINKED'].includes((doc.status || '').toUpperCase())}
                            title="View extracted JSON"
                          >
                            <Code size={18} />
                          </button>
                          <button
                            className="p-1.5 rounded-md text-slate hover:text-danger hover:bg-danger/10 transition-colors"
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
            <div className="p-16 text-center text-slate">
              <ListFilter size={48} className="mx-auto mb-4 opacity-50" />
              <p className="text-lg font-semibold text-ink mb-2">No upload log entries recorded yet.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead className="bg-paper border-b border-line/20 text-slate font-bold text-xs uppercase tracking-wider">
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
                    <tr key={log.id} className="hover:bg-paper/30 transition-colors">
                      <td className="px-6 py-4 text-slate text-xs">
                        {formatDate(log.timestamp)}
                      </td>
                      <td className="px-6 py-4 font-semibold text-ink max-w-[250px] truncate" title={log.filename}>
                        {log.filename}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded text-[10px] font-bold uppercase border ${
                          log.status === 'REJECTED' 
                            ? 'bg-danger/20 text-danger border-danger/30' 
                            : 'bg-success/15 text-success border-success/30'
                        }`}>
                          {log.status === 'REJECTED' ? '❌ REJECTED' : '✓ ACCEPTED'}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`text-xs ${log.status === 'REJECTED' ? 'text-danger/80 font-medium' : 'text-slate'}`}>
                          {log.reason || 'None (Validated & Queued)'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate text-xs font-mono">
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
      {/* Toast Notification */}
      {toastMsg && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center shadow-lg">
          <div className={`px-4 py-3 rounded-lg border flex items-center gap-3 ${
            toastMsg.type === 'error' ? 'bg-danger text-danger border-danger/30' : 
            toastMsg.type === 'warn' ? 'bg-warning/20 text-warning border-warning/30' : 
            'bg-success/15 text-success border-success/30'
          }`}>
            <span className="text-sm font-semibold">{toastMsg.msg}</span>
          </div>
        </div>
      )}
    </div>
  );
}
