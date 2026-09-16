import React, { useState, useEffect, useCallback } from 'react';
import {
  Clock,
  FileText,
  ExternalLink,
  Calendar,
  RefreshCw,
  AlertTriangle,
  User,
  Activity,
  Syringe,
  Pill,
  Stethoscope,
  Microscope,
  ShieldAlert,
  MessageCircleQuestion,
  CheckCircle2,
  ClipboardList,
} from 'lucide-react';
import { 
  fetchTimeline, 
  getDocumentFileUrl, 
  fetchPatient,
  fetchPatientRecords,
  fetchContextPanel,
} from '../api';
import ClinicalContextPanel from '../components/ClinicalContextPanel';
import AddNote from '../components/AddNote';
import { useParams, useNavigate } from 'react-router-dom';

import { getEventConfig } from '../utils/timelineEventConfig';
import PatientHeaderBanner from '../components/PatientHeaderBanner';

export default function TimelinePage() {
  const { patientId } = useParams();
  const navigate = useNavigate();
  
  const [patient, setPatient] = useState(null);
  const [allergies, setAllergies] = useState([]);
  const [events, setEvents] = useState([]);
  const [totalEvents, setTotalEvents] = useState(0);
  
  const [diagnoses, setDiagnoses] = useState([]);
  const [medications, setMedications] = useState([]);
  const [labResults, setLabResults] = useState([]);
  const [documents, setDocuments] = useState([]);
  
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [authError, setAuthError] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  const [contextPanel, setContextPanel] = useState(null);
  const [contextPanelLoading, setContextPanelLoading] = useState(true);
  const [contextPanelError, setContextPanelError] = useState(null);
  const [noteText, setNoteText] = useState('');
  const [showNoteEntry, setShowNoteEntry] = useState(false);

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
      // 1. Fetch Patient Info & Timeline in parallel
      const [patientRes, timelineRes] = await Promise.all([
        fetchPatient(patientId),
        fetchTimeline(patientId)
      ]);
      
      setPatient(patientRes);
      setEvents(timelineRes.events || []);
      setTotalEvents(timelineRes.total_events || 0);
      setLastRefreshed(new Date());

      // 2. Fetch canonical records for clinical summary
      try {
        const recordsRes = await fetchPatientRecords(patientId);
        if (recordsRes) {
          setDiagnoses(recordsRes.diagnoses || []);
          setMedications(recordsRes.medications || []);
          setLabResults(recordsRes.lab_results || []);
          setDocuments(recordsRes.documents || []);
          setAllergies(recordsRes.allergies || []);
        }
      } catch (err) {
        console.warn("Could not load canonical records", err);
      }

      // Story 10.1 — load proactive context panel
      try {
        setContextPanelLoading(true);
        const cpRes = await fetchContextPanel(patientId);
        setContextPanel(cpRes);
        setContextPanelError(null);
      } catch (cpErr) {
        console.warn('Could not load context panel', cpErr);
        setContextPanelError('Could not load context panel.');
      } finally {
        setContextPanelLoading(false);
      }

    } catch (err) {
      console.error('Failed to load patient data:', err);
      if (err.response && err.response.status === 403) {
         setAuthError(true);
         setError("You do not have access to this patient's records.");
      } else {
         setError(err.response?.data?.detail || 'Failed to load timeline events. Please check the backend connection.');
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
      <div className="flex flex-col items-center justify-center min-h-[50vh] text-slate">
        <RefreshCw size={32} className="animate-spin mb-4 text-teal" />
        <p>Loading patient timeline…</p>
      </div>
    );
  }

  if (authError) {
    return (
      <div className="p-6 md:p-8 max-w-[1200px] mx-auto">
        <div className="flex flex-col items-center justify-center min-h-[40vh] bg-danger/10 border border-danger/20 rounded-2xl p-8 text-center">
          <ShieldAlert size={64} className="text-danger mb-4" />
          <h2 className="text-2xl font-bold text-danger mb-2">Access Denied</h2>
          <p className="text-slate">You do not have authorization to view the records for Patient ID: <strong>{patientId}</strong></p>
          <button className="mt-6 px-6 py-2 bg-surface text-ink border border-line rounded-lg font-semibold hover:bg-paper transition-colors" onClick={() => navigate('/patients')}>
            Return to Patients List
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container flex flex-col gap-6">
      
      {/* ── Patient Header Banner ── */}
      <PatientHeaderBanner patient={patient} allergies={allergies} />

      {error && (
        <div className="p-4 bg-danger/10 text-danger border border-danger/20 rounded-xl flex items-center gap-3">
          <AlertTriangle size={20} />
          <span className="font-medium text-sm">{error}</span>
        </div>
      )}

      {/* ── Clinical Summary Grid (Dense Data Tables) ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-2">
        <div className="bg-surface rounded-xl border border-line shadow-sm flex flex-col h-72 overflow-hidden">
          <div className="bg-paper sticky top-0 px-4 py-3 border-b border-line flex items-center gap-2">
            <Activity size={16} className="text-teal" />
            <h3 className="text-ink font-bold text-sm tracking-wide">Diagnoses</h3>
          </div>
          <div className="overflow-y-auto flex-1 custom-scrollbar">
            {diagnoses.length > 0 ? (
              <table className="w-full text-left border-collapse text-sm whitespace-nowrap">
                <tbody>
                  {diagnoses.map(d => (
                    <tr key={d.id} className="border-b border-line last:border-0 hover:bg-paper">
                      <td className="px-4 py-2">
                        <div className="text-ink font-medium truncate" title={d.raw_text}>{d.raw_text}</div>
                        {(d.icd10_code || d.snomed_code) && (
                          <div className="mt-0.5 font-mono text-[10px] text-slate">
                            {d.icd10_code ? `ICD: ${d.icd10_code} ` : ''}
                            {d.snomed_code ? `SNOMED: ${d.snomed_code}` : ''}
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : <p className="text-sm text-slate italic text-center mt-6">No diagnoses recorded.</p>}
          </div>
        </div>

        <div className="bg-surface rounded-xl border border-line shadow-sm flex flex-col h-72 overflow-hidden">
          <div className="bg-paper sticky top-0 px-4 py-3 border-b border-line flex items-center gap-2">
            <Pill size={16} className="text-teal" />
            <h3 className="text-ink font-bold text-sm tracking-wide">Medications</h3>
          </div>
          <div className="overflow-y-auto flex-1 custom-scrollbar">
            {medications.length > 0 ? (
              <table className="w-full text-left border-collapse text-sm whitespace-nowrap">
                <tbody>
                  {medications.map(m => (
                    <tr key={m.id} className="border-b border-line last:border-0 hover:bg-paper">
                      <td className="px-4 py-2">
                        <div className="text-ink font-medium truncate" title={m.raw_text}>{m.raw_text}</div>
                        {m.rxnorm_code && <div className="mt-0.5 font-mono text-[10px] text-slate">RxNorm: {m.rxnorm_code}</div>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : <p className="text-sm text-slate italic text-center mt-6">No medications recorded.</p>}
          </div>
        </div>

        <div className="bg-surface rounded-xl border border-line shadow-sm flex flex-col h-72 overflow-hidden">
          <div className="bg-paper sticky top-0 px-4 py-3 border-b border-line flex items-center gap-2">
            <Microscope size={16} className="text-teal" />
            <h3 className="text-ink font-bold text-sm tracking-wide">Lab Results</h3>
          </div>
          <div className="overflow-y-auto flex-1 custom-scrollbar">
            {labResults.length > 0 ? (
              <table className="w-full text-left border-collapse text-sm whitespace-nowrap">
                <tbody>
                  {labResults.map(l => (
                    <tr key={l.id} className="border-b border-line last:border-0 hover:bg-paper">
                      <td className="px-4 py-2">
                        <div className="text-ink font-medium truncate" title={l.raw_text}>{l.raw_text}</div>
                        {l.loinc_code && <div className="mt-0.5 font-mono text-[10px] text-slate">LOINC: {l.loinc_code}</div>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : <p className="text-sm text-slate italic text-center mt-6">No lab results recorded.</p>}
          </div>
        </div>

        <div className="bg-surface rounded-xl border border-line shadow-sm flex flex-col h-72 overflow-hidden">
          <div className="bg-paper sticky top-0 px-4 py-3 border-b border-line flex items-center gap-2">
            <FileText size={16} className="text-teal" />
            <h3 className="text-ink font-bold text-sm tracking-wide">Documents</h3>
          </div>
          <div className="overflow-y-auto flex-1 custom-scrollbar">
            {documents.length > 0 ? (
              <table className="w-full text-left border-collapse text-sm whitespace-nowrap">
                <tbody>
                  {documents.map(d => (
                    <tr key={d.document_id} className="border-b border-line last:border-0 hover:bg-paper">
                      <td className="px-4 py-2">
                        <div className="text-ink font-medium truncate max-w-[200px]" title={d.filename}>{d.filename}</div>
                        <div className="mt-0.5 text-[10px] text-slate uppercase">{d.document_type || 'Unknown Type'}</div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : <p className="text-sm text-slate italic text-center mt-6">No documents recorded.</p>}
          </div>
        </div>
      </div>

      {/* ── Header Controls ── */}
      <header className="flex justify-between items-center pb-4 border-b border-line">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-teal flex items-center justify-center text-white">
            <Clock size={26} color="#ffffff" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-ink">Longitudinal Timeline</h2>
            <p className="text-sm text-slate">Chronological sequence of verified clinical events</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {lastRefreshed && (
            <span className="text-xs font-medium text-slate hidden sm:inline-block">
              Updated {lastRefreshed.toLocaleTimeString()}
            </span>
          )}
          
          <button
            className="flex items-center gap-2 px-3 py-1.5 bg-success/10 text-success border border-success/20 rounded-lg font-semibold hover:bg-success/20 transition-colors text-sm"
            onClick={() => setShowNoteEntry(true)}
            data-testid="open-note-entry-btn"
          >
            <ClipboardList size={14} />
            Add Note
          </button>

          <button
            className="flex items-center gap-2 px-3 py-1.5 bg-teal/10 text-teal border border-teal/20 rounded-lg font-semibold hover:bg-teal/20 transition-colors text-sm"
            onClick={() => navigate(`/patients/${patientId}/ask`)}
          >
            <MessageCircleQuestion size={14} />
            Ask QA
          </button>

          <button
            className="flex items-center gap-2 px-3 py-1.5 bg-surface border border-line text-ink rounded-lg font-semibold hover:bg-paper transition-colors text-sm disabled:opacity-50"
            onClick={() => loadData(false)}
            disabled={refreshing}
          >
            <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </header>

      {/* ── Timeline Track ── */}
      <div className="relative pt-4 pb-8 pl-4 sm:pl-8">
        
        {/* The Stem */}
        <div className="absolute top-4 bottom-8 left-[23px] sm:left-[39px] w-[2px] bg-line"></div>

        {events.length === 0 ? (
          <div className="ml-8 sm:ml-12 p-8 bg-surface rounded-2xl border border-line text-center flex flex-col items-center justify-center min-h-[250px]">
            <Clock size={40} className="text-slate opacity-50 mb-3" />
            <h3 className="text-lg font-semibold text-ink mb-1">No events recorded</h3>
            <p className="text-slate text-sm">Once documents for this patient pass review and are committed, they will appear here chronologically.</p>
          </div>
        ) : (
          <div className="flex flex-col gap-6">
            {events.map((event, index) => {
              const cfg = getEventConfig(event.event_type || event.field_name);
              const fileUrl = getDocumentFileUrl(event.document_id);
              
              // Simplify the icon/badge colors to fit Phase 3 tokens.
              // We can just rely on standard teal/paper unless we explicitly map cfg to new tokens.
              
              return (
                <div key={event.event_id || index} className="relative ml-8 sm:ml-12 group">
                  
                  {/* Node Dot */}
                  <div className={`absolute -left-[37px] sm:-left-[53px] top-5 w-4 h-4 rounded-full bg-teal border-[3px] border-paper shadow-sm z-10 transition-transform duration-300 group-hover:scale-125`}></div>
                  
                  {/* Event Card */}
                  <div className={`bg-surface rounded-2xl border border-line p-5 hover:bg-paper transition-colors shadow-sm`}>
                    
                    {/* Card Header */}
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-3">
                      
                      <div className="flex flex-wrap items-center gap-3">
                        <div className={`flex items-center gap-1.5 px-3 py-1.5 bg-paper text-ink border border-line rounded-lg text-sm font-bold shadow-sm`}>
                          {cfg.icon}
                          <span className="capitalize">{cfg.label}</span>
                        </div>
                        
                        <div className="flex items-center gap-1.5 text-sm font-semibold text-slate bg-paper px-3 py-1.5 rounded-lg border border-line">
                          <Calendar size={14} />
                          {event.event_date || 'Unknown Date'}
                        </div>
                      </div>

                      {fileUrl && (
                        <a
                          href={fileUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-teal/10 hover:bg-teal/20 text-teal rounded-lg font-semibold text-sm transition-colors shrink-0 border border-teal/20"
                        >
                          <ExternalLink size={14} /> View Source
                        </a>
                      )}
                    </div>

                    {/* Summary / Value */}
                    <div className="text-base font-semibold text-ink mb-4 pl-1">
                      {event.summary || event.value || event.raw_text || 'Event recorded'}
                    </div>

                    {/* Footer Metadata */}
                    <div className="flex flex-wrap items-center gap-x-6 gap-y-2 pt-3 border-t border-line text-xs font-medium text-slate pl-1">
                      {event.filename && (
                        <div className="flex items-center gap-1.5">
                          <FileText size={14} className="opacity-70" />
                          <span>Extracted from: <strong className="text-ink">{event.filename}</strong></span>
                        </div>
                      )}
                      
                      {event.verification_status && (
                        <div className="flex items-center gap-1.5 px-2 py-0.5 bg-success/10 text-success border border-success/20 rounded-full font-bold uppercase tracking-wide text-[10px]">
                          <CheckCircle2 size={12} />
                          <span className="capitalize">{event.verification_status.replace('_', ' ')}</span>
                        </div>
                      )}
                      
                      {event.confidence_score !== undefined && (
                        <div className="flex items-center gap-1.5">
                          <span className="opacity-70">Confidence:</span>
                          {event.confidence_score >= 0.8 ? (
                            <span className="px-2 py-0.5 bg-success/10 text-success border border-success/20 rounded-full font-bold text-[10px]">
                              {Math.round(event.confidence_score * 100)}%
                            </span>
                          ) : event.confidence_score >= 0.5 ? (
                            <span className="px-2 py-0.5 bg-warning/10 text-warning border border-warning/20 rounded-full font-bold text-[10px]">
                              {Math.round(event.confidence_score * 100)}%
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 bg-danger/10 text-danger border border-danger/20 rounded-full font-bold text-[10px]">
                              {Math.round(event.confidence_score * 100)}%
                            </span>
                          )}
                        </div>
                      )}
                    </div>

                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Story 10.1: Note-Entry Screen with Clinical Context Panel ── */}
      {showNoteEntry && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-ink/80 p-4"
          data-testid="note-entry-overlay"
        >
          <div className="w-full max-w-5xl max-h-[90vh] overflow-y-auto bg-surface rounded-2xl border border-line shadow-[var(--shadow-float)] flex flex-col">

            {/* Overlay Header */}
            <div className="flex items-center justify-between p-5 border-b border-line bg-paper">
              <div className="flex items-center gap-3">
                <ClipboardList size={20} className="text-teal" />
                <div>
                  <h2 className="text-base font-bold text-ink">New Clinical Note</h2>
                  <p className="text-xs text-slate font-mono mt-1">
                    {patient?.name ?? 'Patient'} — {patient?.mrn ?? patientId}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowNoteEntry(false)}
                className="p-2 rounded-lg hover:bg-line transition-colors text-slate hover:text-ink"
                aria-label="Close note entry"
                data-testid="close-note-entry-btn"
              >
                ✕
              </button>
            </div>

            {/* Two-column body: note area (left) + context panel (right) */}
            <div className="flex flex-col md:flex-row gap-0 flex-1 overflow-hidden">

              {/* Note Text Area */}
              <div className="flex-1 p-5 overflow-y-auto">
                <AddNote patientId={patientId} />
              </div>


              {/* Context Panel */}
              <div
                className="md:w-80 shrink-0 border-t md:border-t-0 md:border-l border-line p-5 overflow-y-auto bg-paper"
                data-testid="context-panel-column"
              >
                <ClinicalContextPanel
                  panel={contextPanel}
                  loading={contextPanelLoading}
                  error={contextPanelError}
                />
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
