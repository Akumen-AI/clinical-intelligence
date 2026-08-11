import React, { useState, useEffect, useCallback } from 'react';
import {
  Clock,
  Search,
  FileText,
  ExternalLink,
  Calendar,
  Filter,
  CheckCircle2,
  RefreshCw,
  User,
  ShieldCheck,
} from 'lucide-react';
import { fetchTimeline, getDocumentFileUrl } from '../services/api';

export default function TimelinePage() {
  const [patientIdFilter, setPatientIdFilter] = useState('');
  const [activePatientId, setActivePatientId] = useState('');
  const [events, setEvents] = useState([]);
  const [totalEvents, setTotalEvents] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  const loadTimeline = useCallback(async (isPolling = false) => {
    if (!isPolling) setLoading(true);
    else setRefreshing(true);

    setError(null);
    try {
      const data = await fetchTimeline(activePatientId.trim() || null);
      setEvents(data.events || []);
      setTotalEvents(data.total_events || 0);
      setLastRefreshed(new Date());
    } catch (err) {
      console.error('Failed to load patient timeline:', err);
      setError('Failed to load timeline events. Please check the backend connection.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [activePatientId]);

  // Initial load and whenever activePatientId changes
  useEffect(() => {
    loadTimeline(false);
  }, [loadTimeline]);

  // Auto-refresh every 15 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      loadTimeline(true);
    }, 15000);
    return () => clearInterval(interval);
  }, [loadTimeline]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setActivePatientId(patientIdFilter);
  };

  const handleClearFilter = () => {
    setPatientIdFilter('');
    setActivePatientId('');
  };

  return (
    <div className="app-container" style={{ paddingBottom: '3rem' }}>
      {/* Header Section */}
      <header className="app-header">
        <div className="brand-wrapper">
          <div className="brand-logo" style={{ background: 'linear-gradient(135deg, var(--primary-cyan), #3b82f6)' }}>
            <Clock size={26} color="#ffffff" />
          </div>
          <div className="brand-title">
            <h1>Patient Event Timeline</h1>
            <p>Chronological sequence of verified canonical clinical events</p>
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
            onClick={() => loadTimeline(false)}
            disabled={loading || refreshing}
            style={{ padding: '0.5rem 0.9rem', fontSize: '0.82rem' }}
          >
            <RefreshCw size={14} className={refreshing ? 'spin' : ''} />
            Refresh
          </button>
        </div>
      </header>

      {/* Filter Toolbar */}
      <div className="glass-card" style={{ marginBottom: '2rem', padding: '1.25rem 1.5rem' }}>
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--primary-cyan)', fontWeight: '600', fontSize: '0.9rem' }}>
            <Filter size={16} />
            <span>Filter Timeline:</span>
          </div>

          <div style={{ position: 'relative', flex: 1, minWidth: '220px' }}>
            <User size={16} style={{ position: 'absolute', left: '0.85rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Search by Patient ID (e.g. P001)..."
              value={patientIdFilter}
              onChange={(e) => setPatientIdFilter(e.target.value)}
              style={{
                width: '100%',
                padding: '0.6rem 0.85rem 0.6rem 2.5rem',
                background: 'rgba(15, 23, 42, 0.7)',
                border: '1px solid var(--border-light)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--text-main)',
                fontSize: '0.875rem',
                outline: 'none',
              }}
            />
          </div>

          <button type="submit" className="btn btn-primary" style={{ padding: '0.6rem 1.25rem', fontSize: '0.85rem' }}>
            <Search size={15} />
            Apply Filter
          </button>

          {activePatientId && (
            <button type="button" className="btn btn-secondary" onClick={handleClearFilter} style={{ padding: '0.6rem 1rem', fontSize: '0.85rem' }}>
              Clear Filter
            </button>
          )}
        </form>

        {activePatientId && (
          <div style={{ marginTop: '0.75rem', fontSize: '0.8rem', color: 'var(--primary-cyan)' }}>
            Showing events for patient ID: <strong>{activePatientId}</strong>
          </div>
        )}
      </div>

      {/* Error state */}
      {error && (
        <div className="alert-banner error" style={{ marginBottom: '1.5rem' }}>
          <span>{error}</span>
          <button onClick={() => loadTimeline(false)} className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
            Retry
          </button>
        </div>
      )}

      {/* Main Content Area */}
      {loading ? (
        <div className="glass-card" style={{ textAlign: 'center', padding: '3.5rem 1.5rem', color: 'var(--text-muted)' }}>
          <RefreshCw size={28} className="spin" style={{ margin: '0 auto 1rem', color: 'var(--primary-cyan)' }} />
          <p style={{ fontSize: '0.95rem' }}>Loading patient timeline events...</p>
        </div>
      ) : events.length === 0 ? (
        <div className="glass-card" style={{ textAlign: 'center', padding: '4rem 1.5rem' }}>
          <Clock size={48} color="var(--text-muted)" style={{ margin: '0 auto 1rem', opacity: 0.6 }} />
          <h3 style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-main)' }}>
            No verified documents in timeline yet
          </h3>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', maxWidth: '460px', margin: '0 auto' }}>
            {activePatientId
              ? `No committed documents found for patient "${activePatientId}". Try clearing the filter or committing documents in the Review Queue.`
              : 'Once documents complete review and are committed to canonical records, their chronological events will appear here.'}
          </p>
        </div>
      ) : (
        <div>
          {/* Summary bar */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', padding: '0 0.25rem' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Showing <strong>{totalEvents}</strong> chronological event{totalEvents === 1 ? '' : 's'} (oldest first)
            </span>
            <span className="pipeline-badge" style={{ fontSize: '0.75rem', padding: '0.3rem 0.75rem' }}>
              <span className="pulse-dot"></span> Live Sync Enabled
            </span>
          </div>

          {/* Timeline Vertical Track */}
          <div style={{ position: 'relative', paddingLeft: '2rem' }}>
            {/* Vertical spine line */}
            <div
              style={{
                position: 'absolute',
                left: '11px',
                top: '12px',
                bottom: '12px',
                width: '2px',
                background: 'linear-gradient(180deg, var(--primary-cyan), rgba(139, 92, 246, 0.4))',
              }}
            />

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {events.map((event, index) => {
                const fileUrl = getDocumentFileUrl(event.document_id);
                const confidencePct = Math.round((event.confidence_score || 1.0) * 100);

                return (
                  <div
                    key={event.event_id || index}
                    className="glass-card"
                    style={{
                      position: 'relative',
                      margin: 0,
                      padding: '1.25rem 1.5rem',
                      borderLeft: '3px solid var(--primary-cyan)',
                      transition: 'transform 0.15s ease, border-color 0.15s ease',
                    }}
                  >
                    {/* Node Dot on Vertical Line */}
                    <div
                      style={{
                        position: 'absolute',
                        left: '-2.35rem',
                        top: '1.4rem',
                        width: '14px',
                        height: '14px',
                        borderRadius: '50%',
                        background: 'var(--primary-cyan)',
                        border: '3px solid var(--bg-dark)',
                        boxShadow: '0 0 10px rgba(6, 182, 212, 0.6)',
                      }}
                    />

                    {/* Card Content Header */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                        {/* Event Date Badge */}
                        <div
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.4rem',
                            padding: '0.3rem 0.75rem',
                            background: 'rgba(6, 182, 212, 0.12)',
                            border: '1px solid rgba(6, 182, 212, 0.3)',
                            borderRadius: 'var(--radius-sm)',
                            color: 'var(--primary-cyan)',
                            fontSize: '0.85rem',
                            fontWeight: '700',
                          }}
                        >
                          <Calendar size={14} />
                          <span>{event.event_date}</span>
                        </div>

                        {/* Document Type Pill */}
                        <span
                          className="badge-status badge-CLASSIFIED"
                          style={{ fontSize: '0.75rem', textTransform: 'capitalize' }}
                        >
                          {event.event_type || 'Clinical Document'}
                        </span>

                        {/* Patient ID Pill if present */}
                        {event.patient_id && (
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', background: 'rgba(255, 255, 255, 0.05)', padding: '0.2rem 0.5rem', borderRadius: '4px' }}>
                            Patient: <strong>{event.patient_id}</strong>
                          </span>
                        )}
                      </div>

                      {/* View Document Button */}
                      {fileUrl && (
                        <a
                          href={fileUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn btn-secondary"
                          style={{
                            padding: '0.4rem 0.85rem',
                            fontSize: '0.78rem',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.35rem',
                            textDecoration: 'none',
                          }}
                        >
                          <ExternalLink size={13} />
                          <span>View Document</span>
                        </a>
                      )}
                    </div>

                    {/* Summary One-liner */}
                    <div style={{ fontSize: '1rem', fontWeight: '600', color: 'var(--text-main)', marginBottom: '0.6rem' }}>
                      {event.summary}
                    </div>

                    {/* Meta info bar: filename, confidence score */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border-light)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        <FileText size={14} color="var(--text-dim)" />
                        <span>Source: <strong style={{ color: 'var(--text-main)' }}>{event.filename}</strong></span>
                        <span style={{ color: 'var(--text-dim)', marginLeft: '0.4rem' }}>(ID: {event.document_id.slice(0, 8)}...)</span>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: 'var(--accent-emerald)' }}>
                          <ShieldCheck size={14} />
                          <span>{event.verification_status}</span>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          <span>Confidence:</span>
                          <strong style={{ color: confidencePct >= 80 ? 'var(--accent-emerald)' : 'var(--accent-amber)' }}>
                            {confidencePct}%
                          </strong>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
