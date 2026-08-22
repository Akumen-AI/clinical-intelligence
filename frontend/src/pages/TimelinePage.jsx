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
} from 'lucide-react';
import { 
  fetchTimeline, 
  getDocumentFileUrl, 
  fetchPatient,
  fetchPatientRecords
} from '../services/api';
import { useParams, useNavigate } from 'react-router-dom';

const getEventConfig = (eventType) => {
  const type = (eventType || '').toLowerCase();
  
  if (type.includes('medication') || type.includes('med-change') || type.includes('prescription')) {
    return {
      color: 'text-emerald-500',
      bg: 'bg-emerald-500',
      border: 'border-emerald-500/30',
      containerBg: 'bg-emerald-500/10',
      icon: <Pill size={16} />,
      label: 'Medication'
    };
  }
  
  if (type.includes('lab') || type.includes('test')) {
    return {
      color: 'text-violet-500',
      bg: 'bg-violet-500',
      border: 'border-violet-500/30',
      containerBg: 'bg-violet-500/10',
      icon: <Microscope size={16} />,
      label: 'Lab Result'
    };
  }
  
  if (type.includes('diagnos') || type.includes('condition')) {
    return {
      color: 'text-amber-500',
      bg: 'bg-amber-500',
      border: 'border-amber-500/30',
      containerBg: 'bg-amber-500/10',
      icon: <Activity size={16} />,
      label: 'Diagnosis'
    };
  }
  
  if (type.includes('vital')) {
    return {
      color: 'text-cyan-500',
      bg: 'bg-cyan-500',
      border: 'border-cyan-500/30',
      containerBg: 'bg-cyan-500/10',
      icon: <Activity size={16} />,
      label: 'Vitals'
    };
  }
  
  if (type.includes('procedure') || type.includes('surgery')) {
    return {
      color: 'text-rose-500',
      bg: 'bg-rose-500',
      border: 'border-rose-500/30',
      containerBg: 'bg-rose-500/10',
      icon: <Syringe size={16} />,
      label: 'Procedure'
    };
  }
  
  if (type.includes('visit') || type.includes('consult')) {
    return {
      color: 'text-indigo-500',
      bg: 'bg-indigo-500',
      border: 'border-indigo-500/30',
      containerBg: 'bg-indigo-500/10',
      icon: <Stethoscope size={16} />,
      label: 'Clinical Visit'
    };
  }

  return {
    color: 'text-primary',
    bg: 'bg-primary',
    border: 'border-primary/30',
    containerBg: 'bg-primary/10',
    icon: <FileText size={16} />,
    label: eventType || 'Clinical Document'
  };
};

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
          
          if (recordsRes.patient && recordsRes.patient.allergies) {
             setAllergies(recordsRes.patient.allergies);
          } else if (recordsRes.items) {
             const allergyRecords = recordsRes.items.filter(r => r.field_name === 'allergies');
             if (allergyRecords.length > 0) {
                const parsed = allergyRecords.map(a => typeof a.value === 'string' ? a.value : JSON.stringify(a.value));
                setAllergies(parsed);
             }
          }
        }
      } catch (err) {
        console.warn("Could not load canonical records", err);
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

  return (
    <div className="app-container flex flex-col gap-6">
      
      {/* ── Patient Header Banner ── */}
      {patient && (
        <div className="bg-surface-container-high rounded-2xl border border-outline-variant/30 p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center shrink-0 shadow-inner">
              <User size={28} className="text-on-primary" />
            </div>
            <div>
              <h1 className="text-headline-md font-headline-md text-on-surface leading-tight mb-1">
                {patient.name || 'Unknown Patient'}
              </h1>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm font-medium text-on-surface-variant">
                <div className="flex items-center gap-1.5">
                  <span className="opacity-70">MRN:</span>
                  <span className="text-on-surface">{patient.mrn || patientId}</span>
                </div>
                {patient.dob && (
                  <>
                    <div className="w-1 h-1 rounded-full bg-outline-variant"></div>
                    <div className="flex items-center gap-1.5">
                      <span className="opacity-70">DOB:</span>
                      <span className="text-on-surface">{patient.dob}</span>
                    </div>
                  </>
                )}
                {patient.sex && (
                  <>
                    <div className="w-1 h-1 rounded-full bg-outline-variant"></div>
                    <div className="flex items-center gap-1.5">
                      <span className="opacity-70">Sex:</span>
                      <span className="text-on-surface capitalize">{patient.sex}</span>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Allergies / Badges */}
          <div className="flex flex-col items-start md:items-end gap-2">
            <div className="text-xs font-bold uppercase tracking-wider text-on-surface-variant/70">Allergies</div>
            <div className="flex flex-wrap gap-2 justify-end">
              {allergies.length > 0 ? allergies.map((allergy, i) => (
                <span key={i} className="px-3 py-1 bg-error-container/20 text-error border border-error/30 rounded-full text-xs font-bold">
                  {allergy}
                </span>
              )) : (
                <span className="px-3 py-1 bg-surface-variant text-on-surface-variant border border-outline-variant/30 rounded-full text-xs font-semibold">
                  No Known Allergies
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="p-4 bg-error-container/20 text-error border border-error/30 rounded-xl flex items-center gap-3">
          <AlertTriangle size={20} />
          <span className="font-medium text-sm">{error}</span>
        </div>
      )}

      {/* ── Clinical Summary Grid ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-2">
        <div className="bg-surface-container rounded-xl border border-outline-variant/30 p-4 shadow-sm flex flex-col h-64">
          <h3 className="flex items-center gap-2 text-on-surface font-semibold mb-3 border-b border-outline-variant/20 pb-2">
            <Activity size={16} className="text-amber-500" /> Diagnoses
          </h3>
          <div className="overflow-y-auto flex-1 pr-1 custom-scrollbar">
            {diagnoses.length > 0 ? (
              <ul className="flex flex-col gap-2">
                {diagnoses.map(d => (
                  <li key={d.id} className="bg-surface-container-high rounded-lg p-2 text-sm">
                    <div className="text-on-surface font-medium">{d.raw_text}</div>
                    {d.icd10_code && <div className="text-xs text-on-surface-variant mt-1">ICD-10: {d.icd10_code}</div>}
                  </li>
                ))}
              </ul>
            ) : <p className="text-sm text-on-surface-variant/70 italic text-center mt-4">No diagnoses recorded.</p>}
          </div>
        </div>

        <div className="bg-surface-container rounded-xl border border-outline-variant/30 p-4 shadow-sm flex flex-col h-64">
          <h3 className="flex items-center gap-2 text-on-surface font-semibold mb-3 border-b border-outline-variant/20 pb-2">
            <Pill size={16} className="text-emerald-500" /> Medications
          </h3>
          <div className="overflow-y-auto flex-1 pr-1 custom-scrollbar">
            {medications.length > 0 ? (
              <ul className="flex flex-col gap-2">
                {medications.map(m => (
                  <li key={m.id} className="bg-surface-container-high rounded-lg p-2 text-sm">
                    <div className="text-on-surface font-medium">{m.raw_text}</div>
                    {m.rxnorm_code && <div className="text-xs text-on-surface-variant mt-1">RxNorm: {m.rxnorm_code}</div>}
                  </li>
                ))}
              </ul>
            ) : <p className="text-sm text-on-surface-variant/70 italic text-center mt-4">No medications recorded.</p>}
          </div>
        </div>

        <div className="bg-surface-container rounded-xl border border-outline-variant/30 p-4 shadow-sm flex flex-col h-64">
          <h3 className="flex items-center gap-2 text-on-surface font-semibold mb-3 border-b border-outline-variant/20 pb-2">
            <Microscope size={16} className="text-violet-500" /> Lab Results
          </h3>
          <div className="overflow-y-auto flex-1 pr-1 custom-scrollbar">
            {labResults.length > 0 ? (
              <ul className="flex flex-col gap-2">
                {labResults.map(l => (
                  <li key={l.id} className="bg-surface-container-high rounded-lg p-2 text-sm">
                    <div className="text-on-surface font-medium">{l.raw_text}</div>
                    {l.loinc_code && <div className="text-xs text-on-surface-variant mt-1">LOINC: {l.loinc_code}</div>}
                  </li>
                ))}
              </ul>
            ) : <p className="text-sm text-on-surface-variant/70 italic text-center mt-4">No lab results recorded.</p>}
          </div>
        </div>

        <div className="bg-surface-container rounded-xl border border-outline-variant/30 p-4 shadow-sm flex flex-col h-64">
          <h3 className="flex items-center gap-2 text-on-surface font-semibold mb-3 border-b border-outline-variant/20 pb-2">
            <FileText size={16} className="text-primary" /> Documents
          </h3>
          <div className="overflow-y-auto flex-1 pr-1 custom-scrollbar">
            {documents.length > 0 ? (
              <ul className="flex flex-col gap-2">
                {documents.map(d => (
                  <li key={d.document_id} className="bg-surface-container-high rounded-lg p-2 text-sm flex flex-col gap-1">
                    <div className="text-on-surface font-medium truncate" title={d.filename}>{d.filename}</div>
                    <div className="text-xs text-on-surface-variant">{d.document_type || 'Unknown Type'}</div>
                  </li>
                ))}
              </ul>
            ) : <p className="text-sm text-on-surface-variant/70 italic text-center mt-4">No documents recorded.</p>}
          </div>
        </div>
      </div>

      {/* ── Header Controls ── */}
      <header className="app-header">
        <div className="brand-wrapper">
          <div className="brand-logo" style={{ background: 'linear-gradient(135deg, var(--accent-emerald), var(--primary-cyan))' }}>
            <Clock size={26} color="#ffffff" />
          </div>
          <div className="brand-title">
            <h2>Longitudinal Timeline</h2>
            <p>Chronological sequence of verified clinical events</p>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
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
            className="flex items-center gap-2 px-3 py-1.5 bg-surface-variant text-on-surface rounded-lg font-semibold hover:bg-surface-variant/80 transition-colors text-sm"
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
        <div className="absolute top-4 bottom-8 left-[23px] sm:left-[39px] w-[2px] bg-gradient-to-b from-primary via-primary/50 to-transparent"></div>

        {events.length === 0 ? (
          <div className="ml-8 sm:ml-12 p-8 bg-surface-container rounded-2xl border border-outline-variant/20 text-center flex flex-col items-center justify-center min-h-[250px]">
            <Clock size={40} className="text-on-surface-variant/50 mb-3" />
            <h3 className="text-lg font-semibold text-on-surface mb-1">No events recorded</h3>
            <p className="text-on-surface-variant text-sm">Once documents for this patient pass review and are committed, they will appear here chronologically.</p>
          </div>
        ) : (
          <div className="flex flex-col gap-6">
            {events.map((event, index) => {
              const cfg = getEventConfig(event.event_type || event.field_name);
              const fileUrl = getDocumentFileUrl(event.document_id);
              
              return (
                <div key={event.event_id || index} className="relative ml-8 sm:ml-12 group">
                  
                  {/* Node Dot */}
                  <div className={`absolute -left-[37px] sm:-left-[53px] top-5 w-4 h-4 rounded-full ${cfg.bg} border-[3px] border-surface shadow-[0_0_10px_rgba(0,0,0,0.2)] z-10 transition-transform duration-300 group-hover:scale-125`} style={{ boxShadow: `0 0 12px var(--color-${cfg.bg.split('-')[1]})` }}></div>
                  
                  {/* Event Card */}
                  <div className={`bg-surface-container rounded-2xl border ${cfg.border} p-5 hover:bg-surface-container-high transition-colors shadow-sm`}>
                    
                    {/* Card Header */}
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-3">
                      
                      <div className="flex flex-wrap items-center gap-3">
                        <div className={`flex items-center gap-1.5 px-3 py-1.5 ${cfg.containerBg} ${cfg.color} ${cfg.border} border rounded-lg text-sm font-bold shadow-sm`}>
                          {cfg.icon}
                          <span className="capitalize">{cfg.label}</span>
                        </div>
                        
                        <div className="flex items-center gap-1.5 text-sm font-semibold text-on-surface-variant bg-surface-variant px-3 py-1.5 rounded-lg border border-outline-variant/20">
                          <Calendar size={14} />
                          {event.event_date || 'Unknown Date'}
                        </div>
                      </div>

                      {fileUrl && (
                        <a
                          href={fileUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-primary/10 hover:bg-primary/20 text-primary rounded-lg font-semibold text-sm transition-colors shrink-0 border border-primary/20"
                        >
                          <ExternalLink size={14} /> View Source
                        </a>
                      )}
                    </div>

                    {/* Summary / Value */}
                    <div className="text-base font-semibold text-on-surface mb-4 pl-1">
                      {event.summary || event.value || event.raw_text || 'Event recorded'}
                    </div>

                    {/* Footer Metadata */}
                    <div className="flex flex-wrap items-center gap-x-6 gap-y-2 pt-3 border-t border-outline-variant/10 text-xs font-medium text-on-surface-variant pl-1">
                      {event.filename && (
                        <div className="flex items-center gap-1.5">
                          <FileText size={14} className="opacity-70" />
                          <span>Extracted from: <strong className="text-on-surface">{event.filename}</strong></span>
                        </div>
                      )}
                      
                      {event.verification_status && (
                        <div className="flex items-center gap-1.5 text-emerald-500">
                          <CheckCircle2 size={14} />
                          <span className="capitalize">{event.verification_status.replace('_', ' ')}</span>
                        </div>
                      )}
                      
                      {event.confidence_score !== undefined && (
                        <div className="flex items-center gap-1.5">
                          <span className="opacity-70">Confidence:</span>
                          <strong className={event.confidence_score >= 0.8 ? 'text-emerald-500' : 'text-amber-500'}>
                            {Math.round(event.confidence_score * 100)}%
                          </strong>
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

    </div>
  );
}
