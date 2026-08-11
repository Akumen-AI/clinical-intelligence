import React, { useState, useEffect, useCallback } from 'react';
import {
  Database,
  Search,
  Filter,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  FileText,
  User,
  ShieldCheck,
  ExternalLink,
  Clock,
  Hash,
  Layers,
  CheckCircle2,
  XCircle,
  AlertTriangle,
} from 'lucide-react';
import { fetchCanonicalRecords, getDocumentFileUrl } from '../services/api';

/**
 * Format a JSON value for display in the table row.
 * Returns a short, readable string.
 */
function formatValueShort(value) {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (typeof value === 'object') {
    const json = JSON.stringify(value);
    return json.length > 60 ? json.slice(0, 57) + '…' : json;
  }
  return String(value);
}

/**
 * Pretty-print a JSON value for the expanded detail panel.
 */
function formatValueFull(value) {
  if (value === null || value === undefined) return 'null';
  if (typeof value === 'string') return value;
  return JSON.stringify(value, null, 2);
}

/**
 * Format an ISO date string to a human-friendly format.
 */
function formatDate(isoStr) {
  if (!isoStr) return '—';
  try {
    const d = new Date(isoStr);
    return d.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoStr;
  }
}

/**
 * Confidence badge with color coding.
 */
function ConfidenceBadge({ score }) {
  if (score === null || score === undefined) return <span className="cr-badge cr-badge-dim">N/A</span>;
  const pct = Math.round(score * 100);
  const cls = pct >= 90 ? 'cr-badge-high' : pct >= 70 ? 'cr-badge-mid' : 'cr-badge-low';
  return <span className={`cr-badge ${cls}`}>{pct}%</span>;
}

/**
 * Verification status pill.
 */
function StatusPill({ status }) {
  if (!status) return null;
  const label = status.replace(/_/g, ' ');
  const isVerified = status === 'human_verified' || status === 'auto_passed';
  return (
    <span className={`cr-status-pill ${isVerified ? 'cr-status-verified' : 'cr-status-pending'}`}>
      {isVerified ? <CheckCircle2 size={12} /> : <Clock size={12} />}
      {label}
    </span>
  );
}

export default function CanonicalRecordPage() {
  // Data state
  const [records, setRecords] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);

  // Loading / error
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  // Filters
  const [patientIdInput, setPatientIdInput] = useState('');
  const [fieldNameInput, setFieldNameInput] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [activeFilters, setActiveFilters] = useState({});

  // Expanded row
  const [expandedId, setExpandedId] = useState(null);

  // ── Load data ──────────────────────────────────────────────────────────
  const loadRecords = useCallback(
    async (isPolling = false) => {
      if (!isPolling) setLoading(true);
      else setRefreshing(true);
      setError(null);

      try {
        const data = await fetchCanonicalRecords({
          ...activeFilters,
          page,
          page_size: pageSize,
        });
        setRecords(data.items || []);
        setTotal(data.total || 0);
        setLastRefreshed(new Date());
      } catch (err) {
        const raw = err.response?.data?.detail;
        let msg;
        if (typeof raw === 'string') msg = raw;
        else if (Array.isArray(raw)) msg = raw.map((e) => e.msg || JSON.stringify(e)).join('; ');
        else if (raw) msg = JSON.stringify(raw);
        else msg = err.message || 'Failed to load canonical records';
        setError(msg);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [activeFilters, page, pageSize]
  );

  useEffect(() => {
    loadRecords(false);
  }, [loadRecords]);

  // Auto-refresh every 15 seconds
  useEffect(() => {
    const interval = setInterval(() => loadRecords(true), 15000);
    return () => clearInterval(interval);
  }, [loadRecords]);

  // ── Filter handlers ────────────────────────────────────────────────────
  const handleApplyFilters = (e) => {
    e.preventDefault();
    setPage(1);
    setActiveFilters({
      patient_id: patientIdInput.trim() || null,
      field_name: fieldNameInput.trim() || null,
      search: searchInput.trim() || null,
    });
  };

  const handleClearFilters = () => {
    setPatientIdInput('');
    setFieldNameInput('');
    setSearchInput('');
    setActiveFilters({});
    setPage(1);
  };

  const hasActiveFilters = !!(activeFilters.patient_id || activeFilters.field_name || activeFilters.search);

  // ── Stats ──────────────────────────────────────────────────────────────
  const uniquePatients = new Set(records.filter((r) => r.patient_id).map((r) => r.patient_id)).size;
  const uniqueDocs = new Set(records.map((r) => r.document_id)).size;

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  // ── Row toggle ─────────────────────────────────────────────────────────
  const toggleRow = (recordId) => {
    setExpandedId((prev) => (prev === recordId ? null : recordId));
  };

  // ── Render ─────────────────────────────────────────────────────────────
  return (
    <div className="app-container" style={{ paddingBottom: '3rem' }}>
      {/* Header */}
      <header className="app-header">
        <div className="brand-wrapper">
          <div className="brand-logo" style={{ background: 'linear-gradient(135deg, #8B5CF6, var(--primary-cyan))' }}>
            <Database size={26} color="#ffffff" />
          </div>
          <div className="brand-title">
            <h1>Canonical Patient Records</h1>
            <p>Verified field values admitted to the patient record</p>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {lastRefreshed && (
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Updated {lastRefreshed.toLocaleTimeString()}
            </span>
          )}
          <button
            className="btn btn-secondary"
            onClick={() => loadRecords(false)}
            disabled={loading || refreshing}
            style={{ padding: '0.5rem 0.9rem', fontSize: '0.82rem' }}
          >
            <RefreshCw size={14} className={refreshing ? 'spin' : ''} />
            Refresh
          </button>
        </div>
      </header>

      {/* Stats Strip */}
      <div className="cr-stats-strip">
        <div className="cr-stat">
          <Database size={15} color="var(--primary-violet)" />
          <span>
            <strong>{total}</strong> record{total !== 1 ? 's' : ''}
          </span>
        </div>
        <div className="cr-stat">
          <User size={15} color="var(--primary-cyan)" />
          <span>
            <strong>{uniquePatients}</strong> patient{uniquePatients !== 1 ? 's' : ''}
          </span>
        </div>
        <div className="cr-stat">
          <FileText size={15} color="var(--accent-emerald)" />
          <span>
            <strong>{uniqueDocs}</strong> document{uniqueDocs !== 1 ? 's' : ''}
          </span>
        </div>
        <span className="pipeline-badge" style={{ fontSize: '0.75rem', padding: '0.3rem 0.75rem', marginLeft: 'auto' }}>
          <span className="pulse-dot"></span> Live Sync
        </span>
      </div>

      {/* Filter Toolbar */}
      <div className="glass-card" style={{ marginBottom: '1.5rem', padding: '1.25rem 1.5rem' }}>
        <form onSubmit={handleApplyFilters} style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--primary-cyan)', fontWeight: '600', fontSize: '0.9rem' }}>
            <Filter size={16} />
            <span>Filter:</span>
          </div>

          <div className="cr-filter-input-wrap">
            <User size={14} className="cr-filter-icon" />
            <input
              id="cr-filter-patient"
              type="text"
              placeholder="Patient ID"
              value={patientIdInput}
              onChange={(e) => setPatientIdInput(e.target.value)}
              className="cr-filter-input"
            />
          </div>

          <div className="cr-filter-input-wrap">
            <Hash size={14} className="cr-filter-icon" />
            <input
              id="cr-filter-field"
              type="text"
              placeholder="Field name"
              value={fieldNameInput}
              onChange={(e) => setFieldNameInput(e.target.value)}
              className="cr-filter-input"
            />
          </div>

          <div className="cr-filter-input-wrap" style={{ flex: 1, minWidth: '180px' }}>
            <Search size={14} className="cr-filter-icon" />
            <input
              id="cr-filter-search"
              type="text"
              placeholder="Search..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="cr-filter-input"
            />
          </div>

          <button type="submit" className="btn btn-primary" style={{ padding: '0.55rem 1.1rem', fontSize: '0.85rem' }}>
            <Search size={14} /> Apply
          </button>

          {hasActiveFilters && (
            <button type="button" className="btn btn-secondary" onClick={handleClearFilters} style={{ padding: '0.55rem 1rem', fontSize: '0.85rem' }}>
              <XCircle size={14} /> Clear
            </button>
          )}
        </form>

        {hasActiveFilters && (
          <div style={{ marginTop: '0.6rem', fontSize: '0.78rem', color: 'var(--primary-cyan)', display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            {activeFilters.patient_id && <span>Patient: <strong>{activeFilters.patient_id}</strong></span>}
            {activeFilters.field_name && <span>Field: <strong>{activeFilters.field_name}</strong></span>}
            {activeFilters.search && <span>Search: <strong>"{activeFilters.search}"</strong></span>}
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="alert-banner error" style={{ marginBottom: '1.5rem' }}>
          <AlertTriangle size={16} />
          <span>{error}</span>
          <button onClick={() => loadRecords(false)} className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
            Retry
          </button>
        </div>
      )}

      {/* Loading */}
      {loading ? (
        <div className="glass-card" style={{ textAlign: 'center', padding: '3.5rem 1.5rem', color: 'var(--text-muted)' }}>
          <RefreshCw size={28} className="spin" style={{ margin: '0 auto 1rem', color: 'var(--primary-cyan)' }} />
          <p style={{ fontSize: '0.95rem' }}>Loading canonical records…</p>
        </div>
      ) : records.length === 0 ? (
        /* Empty state */
        <div className="glass-card" style={{ textAlign: 'center', padding: '4rem 1.5rem' }}>
          <Database size={48} color="var(--text-muted)" style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
          <h3 style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-main)' }}>
            No canonical records found
          </h3>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', maxWidth: '460px', margin: '0 auto' }}>
            {hasActiveFilters
              ? 'No records match the current filters. Try clearing or adjusting them.'
              : 'Once documents are processed and fields pass confidence routing or human review, their verified values will appear here.'}
          </p>
        </div>
      ) : (
        /* Records Table */
        <div>
          {/* Table container */}
          <div className="cr-table-container glass-card" style={{ padding: 0, overflow: 'hidden' }}>
            <table className="cr-table">
              <thead>
                <tr>
                  <th style={{ width: '36px' }}></th>
                  <th>Field Name</th>
                  <th>Value</th>
                  <th>Patient</th>
                  <th>Source Document</th>
                  <th>Confidence</th>
                  <th>Status</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {records.map((rec) => {
                  const isExpanded = expandedId === rec.record_id;
                  const fileUrl = getDocumentFileUrl(rec.document_id);

                  return (
                    <React.Fragment key={rec.record_id}>
                      {/* Main row */}
                      <tr
                        className={`cr-row ${isExpanded ? 'cr-row-expanded' : ''}`}
                        onClick={() => toggleRow(rec.record_id)}
                      >
                        <td className="cr-expand-cell">
                          {isExpanded ? (
                            <ChevronDown size={16} color="var(--primary-cyan)" />
                          ) : (
                            <ChevronRight size={16} color="var(--text-dim)" />
                          )}
                        </td>
                        <td>
                          <span className="cr-field-name">{rec.field_name}</span>
                        </td>
                        <td>
                          <span className="cr-value-preview">{formatValueShort(rec.value)}</span>
                        </td>
                        <td>
                          {rec.patient_id ? (
                            <span className="cr-patient-id">{rec.patient_id}</span>
                          ) : (
                            <span className="cr-dim">—</span>
                          )}
                        </td>
                        <td>
                          <span className="cr-doc-name" title={rec.document_id}>
                            {rec.filename || rec.document_id.slice(0, 8) + '…'}
                          </span>
                        </td>
                        <td>
                          <ConfidenceBadge score={rec.confidence_score} />
                        </td>
                        <td>
                          <StatusPill status={rec.verification_status} />
                        </td>
                        <td>
                          <span className="cr-date">{formatDate(rec.created_at)}</span>
                        </td>
                      </tr>

                      {/* Expanded detail panel */}
                      {isExpanded && (
                        <tr className="cr-detail-row">
                          <td colSpan={8}>
                            <div className="cr-detail-panel">
                              <div className="cr-detail-grid">
                                {/* Full value */}
                                <div className="cr-detail-section cr-detail-value-section">
                                  <h4><Layers size={14} /> Full Value</h4>
                                  <pre className="cr-detail-pre">{formatValueFull(rec.value)}</pre>
                                </div>

                                {/* Metadata */}
                                <div className="cr-detail-section">
                                  <h4><FileText size={14} /> Record Metadata</h4>
                                  <div className="cr-detail-meta">
                                    <div className="cr-meta-row">
                                      <span className="cr-meta-label">Record ID</span>
                                      <span className="cr-meta-value cr-mono">{rec.record_id}</span>
                                    </div>
                                    <div className="cr-meta-row">
                                      <span className="cr-meta-label">Document ID</span>
                                      <span className="cr-meta-value cr-mono">{rec.document_id}</span>
                                    </div>
                                    <div className="cr-meta-row">
                                      <span className="cr-meta-label">Source Field ID</span>
                                      <span className="cr-meta-value cr-mono">{rec.source_field_id}</span>
                                    </div>
                                    <div className="cr-meta-row">
                                      <span className="cr-meta-label">Document Type</span>
                                      <span className="cr-meta-value">{rec.document_type || '—'}</span>
                                    </div>
                                    <div className="cr-meta-row">
                                      <span className="cr-meta-label">Created</span>
                                      <span className="cr-meta-value">{formatDate(rec.created_at)}</span>
                                    </div>
                                    <div className="cr-meta-row">
                                      <span className="cr-meta-label">Updated</span>
                                      <span className="cr-meta-value">{formatDate(rec.updated_at)}</span>
                                    </div>
                                  </div>

                                  {fileUrl && (
                                    <a
                                      href={fileUrl}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="btn btn-secondary cr-detail-doc-link"
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      <ExternalLink size={13} /> View Source Document
                                    </a>
                                  )}
                                </div>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="cr-pagination">
              <button
                className="btn btn-secondary cr-page-btn"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                ← Previous
              </button>
              <span className="cr-page-info">
                Page <strong>{page}</strong> of <strong>{totalPages}</strong>
                <span className="cr-page-total">({total} records)</span>
              </span>
              <button
                className="btn btn-secondary cr-page-btn"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                Next →
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
