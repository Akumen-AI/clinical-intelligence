import React, { useState, useEffect, useCallback } from 'react';
import {
  Clock,
  ExternalLink,
  Calendar,
  RefreshCw,
  AlertTriangle,
  Pill,
  ShieldAlert,
  MessageCircleQuestion,
  CheckCircle2,
  FileText
} from 'lucide-react';
import { useParams, useNavigate, Link } from 'react-router-dom';

import { fetchPatientDashboard, getDocumentFileUrl } from '../services/api';
import PatientHeaderBanner from '../components/PatientHeaderBanner';
import LabTrendChart from '../components/LabTrendChart';
import { getEventConfig } from '../utils/timelineEventConfig';

export default function PatientDashboardPage() {
  const { patientId } = useParams();
  const navigate = useNavigate();

  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [authError, setAuthError] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  const loadData = useCallback(async (isPolling = false) => {
    if (!patientId) {
      setError("No Patient ID provided in route.");
      setLoading(false);
      return;
    }

    if (!isPolling) setLoading(true);
    else setRefreshing(true);

    setError(null);
    setAuthError(false);

    try {
      const data = await fetchPatientDashboard(patientId);
      setDashboard(data);
      setLastRefreshed(new Date());
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
      if (err.response && err.response.status === 403) {
         setAuthError(true);
         setError("You do not have access to this patient's records.");
      } else {
         setError(err.response?.data?.detail || 'Failed to load dashboard. Please check the backend connection.');
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [patientId]);

  useEffect(() => {
    loadData(false);
  }, [loadData]);

  // Auto-refresh every 15 seconds
  useEffect(() => {
    if (authError || !patientId) return;
    const interval = setInterval(() => {
      loadData(true);
    }, 15000);
    return () => clearInterval(interval);
  }, [loadData, authError, patientId]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] text-on-surface-variant">
        <RefreshCw size={32} className="animate-spin mb-4 text-primary" />
        <p>Loading patient timeline…</p>
      </div>
    );
  }

  if (authError) {
    return (
      <div className="p-6 md:p-8 max-w-[1200px] mx-auto">
        <div className="flex flex-col items-center justify-center min-h-[40vh] bg-error-container/20 border border-error/30 rounded-2xl p-8 text-center">
          <ShieldAlert size={64} className="text-error mb-4" />
          <h2 className="text-headline-sm font-headline-sm text-error mb-2">Access Denied</h2>
          <p className="text-on-surface-variant">You do not have authorization to view the records for Patient ID: <strong>{patientId}</strong></p>
          <button className="mt-6 px-6 py-2 bg-surface-variant text-on-surface rounded-lg font-semibold hover:bg-surface-variant/80 transition-colors" onClick={() => navigate('/patients')}>
            Return to Patients List
          </button>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 md:p-8 max-w-[1200px] mx-auto">
        <div className="p-4 bg-error-container/20 text-error border border-error/30 rounded-xl flex items-center gap-3">
          <AlertTriangle size={24} />
          <span className="font-medium text-sm">{error}</span>
        </div>
      </div>
    );
  }

  if (!dashboard || !dashboard.patient) {
    return null; // Should not reach here unless error was set
  }

  const { patient, allergies, current_medications, lab_trends, other_lab_results, recent_events, total_events } = dashboard;

  return (
    <div className="app-container flex flex-col gap-6">
      <PatientHeaderBanner patient={patient} allergies={allergies} />

      {error && (
        <div className="p-4 bg-error-container/20 text-error border border-error/30 rounded-xl flex items-center gap-3">
          <AlertTriangle size={20} />
          <span className="font-medium text-sm">{error}</span>
        </div>
      )}

      {/* ── Header Controls ── */}
      <header className="app-header">
        <div className="brand-wrapper">
          <div className="brand-logo" style={{ background: 'linear-gradient(135deg, var(--accent-emerald), var(--primary-cyan))' }}>
            <Clock size={26} color="#ffffff" />
          </div>
          <div className="brand-title">
            <h2>Patient Dashboard</h2>
            <p>Clinical overview for today's consult</p>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          {lastRefreshed && (
            <span className="text-xs font-medium text-on-surface-variant hidden sm:inline-block">
              Updated {lastRefreshed.toLocaleTimeString()}
            </span>
          )}
          
          <button
            className="flex items-center gap-2 px-3 py-1.5 bg-primary/10 text-primary border border-primary/20 rounded-lg font-semibold hover:bg-primary/20 transition-colors text-sm"
            onClick={() => navigate(`/patients/${patientId}/ask`)}
          >
            <MessageCircleQuestion size={14} />
            Ask QA
          </button>

          <button
            className="flex items-center gap-2 px-3 py-1.5 bg-secondary/10 text-secondary border border-secondary/20 rounded-lg font-semibold hover:bg-secondary/20 transition-colors text-sm"
            onClick={() => navigate(`/patients/${patientId}/timeline`)}
          >
            <Clock size={14} />
            Full Timeline
          </button>

          <button
            className="flex items-center gap-2 px-3 py-1.5 bg-surface-variant text-on-surface rounded-lg font-semibold hover:bg-surface-variant/80 transition-colors text-sm"
            onClick={() => loadData(false)}
            disabled={refreshing}
          >
            <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </header>

      {/* ── Dashboard Grid ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Left Column: Medications */}
        <div className="bg-surface-container rounded-xl border border-outline-variant/30 p-4 shadow-sm flex flex-col h-[350px]">
          <h3 className="flex items-center gap-2 text-on-surface font-semibold mb-3 border-b border-outline-variant/20 pb-2">
            <Pill size={16} className="text-emerald-500" /> Current Medications
          </h3>
          <div className="overflow-y-auto flex-1 pr-1 custom-scrollbar">
            {current_medications && current_medications.length > 0 ? (
              <ul className="flex flex-col gap-2">
                {current_medications.map(m => (
                  <li key={m.id} className="bg-surface-container-high rounded-lg p-2 text-sm">
                    <div className="text-on-surface font-medium">{m.raw_text}</div>
                    {m.rxnorm_code && <div className="text-xs text-on-surface-variant mt-1">RxNorm: {m.rxnorm_code}</div>}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-on-surface-variant/70 italic text-center mt-4">
                No active medications recorded.
              </p>
            )}
          </div>
        </div>

        {/* Right Column: Lab Trends */}
        <div className="h-[350px]">
          <LabTrendChart labTrends={lab_trends} otherLabResults={other_lab_results} />
        </div>
      </div>

      {/* ── Recent Activity ── */}
      <div className="bg-surface-container rounded-xl border border-outline-variant/30 p-4 shadow-sm flex flex-col mt-2">
        <div className="flex items-center justify-between mb-3 border-b border-outline-variant/20 pb-2">
          <h3 className="flex items-center gap-2 text-on-surface font-semibold">
            <Clock size={16} className="text-primary" /> Recent Activity
          </h3>
          <span className="text-xs font-medium text-on-surface-variant bg-surface-container-highest px-2 py-1 rounded">
            Showing {recent_events?.length || 0} of {total_events || 0} events
          </span>
        </div>

        <div className="flex flex-col gap-3 py-2">
          {!recent_events || recent_events.length === 0 ? (
            <div className="p-8 text-center flex flex-col items-center justify-center">
              <Clock size={40} className="text-on-surface-variant/50 mb-3" />
              <h3 className="text-lg font-semibold text-on-surface mb-1">No events recorded</h3>
              <p className="text-on-surface-variant text-sm">Once documents for this patient pass review and are committed, they will appear here chronologically.</p>
            </div>
          ) : (
            recent_events.map((event, index) => {
              const cfg = getEventConfig(event.event_type || event.field_name);
              const fileUrl = getDocumentFileUrl(event.document_id);
              
              return (
                <div key={event.event_id || index} className={`bg-surface-container-high rounded-lg border ${cfg.border} p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-surface-container-highest transition-colors shadow-sm`}>
                  <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                    <div className="flex items-center gap-3">
                      <div className={`flex items-center justify-center w-8 h-8 rounded-full ${cfg.containerBg} ${cfg.color} shrink-0`}>
                        {cfg.icon}
                      </div>
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-on-surface-variant bg-surface-variant px-2 py-1 rounded border border-outline-variant/20 whitespace-nowrap">
                        <Calendar size={12} />
                        {event.event_date || 'Unknown Date'}
                      </div>
                    </div>
                    
                    <div className="text-sm font-semibold text-on-surface line-clamp-1" title={event.summary || event.value || event.raw_text}>
                      {event.summary || event.value || event.raw_text || 'Event recorded'}
                    </div>
                  </div>

                  {fileUrl && (
                    <a
                      href={fileUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-primary/10 hover:bg-primary/20 text-primary rounded-lg font-semibold text-xs transition-colors shrink-0 border border-primary/20"
                    >
                      <ExternalLink size={12} /> View
                    </a>
                  )}
                </div>
              );
            })
          )}
        </div>

        {total_events > 0 && (
          <div className="mt-4 text-center">
            <Link to={`/patients/${patientId}/timeline`} className="inline-flex items-center gap-1 text-sm font-semibold text-primary hover:text-primary-container transition-colors">
              View full timeline &rarr;
            </Link>
          </div>
        )}
      </div>

    </div>
  );
}
