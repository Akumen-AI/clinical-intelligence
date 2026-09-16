import React, { useState, useEffect } from 'react';
import { 
  X, 
  Copy, 
  Check, 
  Code, 
  FileText, 
  RefreshCw, 
  AlertCircle, 
  User, 
  Calendar, 
  Stethoscope, 
  Activity, 
  Pill, 
  FlaskConical, 
  CheckCircle2, 
  Sparkles 
} from 'lucide-react';
import { fetchDocumentFields, extractDocumentFields, getDocumentFileUrl } from '../api';

export default function ExtractedFieldsModal({ document: doc, onClose, onRefreshRequired }) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isExtracting, setIsExtracting] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('json'); // 'json' or 'summary'
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!doc) return;
    loadFields();

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [doc]);

  const loadFields = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetchDocumentFields(doc.document_id);
      setData(res);
    } catch (err) {
      if (err.response && err.response.status === 404) {
        setData(null);
      } else {
        setError(err.response?.data?.detail || err.message || 'Failed to load fields');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunExtraction = async () => {
    setIsExtracting(true);
    setError(null);
    try {
      const res = await extractDocumentFields(doc.document_id);
      setData(res);
      if (onRefreshRequired) onRefreshRequired();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Extraction failed');
    } finally {
      setIsExtracting(false);
    }
  };

  const handleCopyJson = () => {
    if (!data) return;
    const f = data.fields || {};
    const recs = data.extracted_records || data.field_records || [];
    const confMap = {};
    recs.forEach(rec => { confMap[rec.field_name] = rec.confidence_score; });
    const combined = {};
    Object.keys(f).forEach(key => {
      combined[key] = {
        value: f[key],
        confidence_score: confMap[key] !== undefined ? confMap[key] : null,
      };
    });
    const jsonStr = JSON.stringify(combined, null, 2);
    navigator.clipboard.writeText(jsonStr).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  if (!doc) return null;

  const fields = data?.fields || {};
  const records = data?.extracted_records || data?.field_records || [];

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-ink/80 z-50 p-6" onClick={onClose}>
      <div className="bg-surface border border-line rounded-xl shadow-[var(--shadow-float)] overflow-hidden w-full max-w-7xl max-h-[88vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="flex justify-between items-center p-5 border-b border-line bg-paper">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-md bg-teal/10 border border-teal/20 flex items-center justify-center">
              <Sparkles size={20} className="text-teal" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-ink">Extracted Clinical Fields</h2>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-sm text-slate">{doc.filename}</span>
                <span className="font-mono text-teal bg-teal/10 px-1.5 py-0.5 rounded text-xs">{doc.document_id}</span>
                {doc.document_type && (
                  <span className="px-2 py-0.5 rounded-md text-xs font-semibold bg-teal/15 text-teal">
                    {doc.document_type}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              className="px-3 py-1.5 rounded-md font-semibold text-sm bg-surface border border-line text-ink hover:bg-paper transition-colors flex items-center gap-1.5 disabled:opacity-50"
              onClick={handleRunExtraction}
              disabled={isExtracting}
              title="Re-run field extraction"
            >
              <RefreshCw size={13} className={isExtracting ? 'animate-spin' : ''} />
              {isExtracting ? 'Extracting...' : 'Re-extract'}
            </button>
            <button className="p-1.5 rounded-md text-slate hover:text-danger hover:bg-danger/10 transition-colors" onClick={onClose} title="Close">
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Modal Navigation Tabs */}
        <div className="flex gap-2 p-3 bg-paper border-b border-line">
          <button
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-semibold border transition-colors ${activeTab === 'json' ? 'text-teal bg-teal/10 border-teal/20' : 'text-slate hover:text-ink hover:bg-surface border-transparent'}`}
            onClick={() => setActiveTab('json')}
          >
            <Code size={16} />
            JSON View (FR-07)
          </button>
          <button
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-semibold border transition-colors ${activeTab === 'summary' ? 'text-teal bg-teal/10 border-teal/20' : 'text-slate hover:text-ink hover:bg-surface border-transparent'}`}
            onClick={() => setActiveTab('summary')}
          >
            <FileText size={16} />
            Structured Summary
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-5">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center min-h-[300px] text-center gap-3 text-slate">
              <RefreshCw size={28} className="animate-spin text-teal" />
              <p>Loading extracted fields from database...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center min-h-[300px] text-center gap-3 text-danger">
              <AlertCircle size={28} />
              <p>{error}</p>
              <button className="px-4 py-2 rounded-md bg-teal text-white font-semibold hover:bg-teal/90 transition-colors mt-3" onClick={handleRunExtraction}>
                Run Field Extraction
              </button>
            </div>
          ) : !data ? (
            <div className="flex flex-col items-center justify-center min-h-[300px] text-center gap-3 text-slate">
              <FileText size={32} className="opacity-50" />
              <p>No fields extracted for this document yet.</p>
              <p className="text-sm opacity-80">
                Click below to extract structured clinical data using the configured extraction provider.
              </p>
              <button 
                className="px-4 py-2 rounded-md bg-teal text-white font-semibold hover:bg-teal/90 transition-colors flex items-center gap-1.5 mt-3 disabled:opacity-50"
                onClick={handleRunExtraction} 
                disabled={isExtracting}
              >
                <Sparkles size={16} />
                {isExtracting ? 'Extracting...' : 'Extract Fields Now'}
              </button>
            </div>
          ) : activeTab === 'json' ? (
            /* JSON View with Confidence Scores */
            (() => {
              // Build confidence map from field_records
              const confidenceMap = {};
              records.forEach(rec => {
                confidenceMap[rec.field_name] = rec.confidence_score;
              });

              // Build combined JSON with value + confidence for each field
              const fieldsWithConfidence = {};
              Object.keys(fields).forEach(key => {
                const conf = confidenceMap[key];
                fieldsWithConfidence[key] = {
                  value: fields[key],
                  confidence_score: conf !== undefined ? conf : null,
                };
              });

              const getConfidenceColorClass = (score) => {
                if (score === null || score === undefined) return 'bg-slate';
                if (score >= 0.8) return 'bg-success';
                if (score >= 0.5) return 'bg-warning';
                return 'bg-danger';
              };
              
              const getConfidenceTextColorClass = (score) => {
                if (score === null || score === undefined) return 'text-slate';
                if (score >= 0.8) return 'text-success';
                if (score >= 0.5) return 'text-warning';
                return 'text-danger';
              };
              
              const getConfidenceBgContainerClass = (score) => {
                if (score === null || score === undefined) return 'bg-slate/20';
                if (score >= 0.8) return 'bg-success/20';
                if (score >= 0.5) return 'bg-warning/20';
                return 'bg-danger/20';
              };

              const getConfidenceLabel = (score) => {
                if (score === null || score === undefined) return 'N/A';
                if (score >= 0.8) return 'High';
                if (score >= 0.5) return 'Medium';
                return 'Low';
              };

              return (
                <div className="grid grid-cols-1 lg:grid-cols-[0.9fr_1.1fr] gap-4 min-h-[520px]">
                  <section className="flex flex-col min-w-0 bg-surface border border-line rounded-lg overflow-hidden" aria-label="Original uploaded document">
                    <div className="flex justify-between items-center p-3 border-b border-line bg-paper">
                      <div>
                        <span className="block text-xs font-bold text-slate uppercase tracking-wider mb-0.5">Original upload</span>
                        <strong className="text-sm font-semibold text-ink">{doc.filename}</strong>
                      </div>
                      {doc.raw_uri && (
                        <a
                          className="text-teal font-semibold text-xs hover:underline"
                          href={getDocumentFileUrl(doc.document_id)}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Open
                        </a>
                      )}
                    </div>
                    <div className="flex-1 flex items-center justify-center overflow-auto p-4 bg-paper relative">
                      {doc.raw_uri ? (
                        (doc.filetype || '').toLowerCase() === 'pdf' || doc.filename?.toLowerCase().endsWith('.pdf') ? (
                          <iframe
                            title={`Original uploaded file: ${doc.filename}`}
                            src={getDocumentFileUrl(doc.document_id)}
                            className="w-full h-full min-h-[400px] border-0 rounded-sm bg-white"
                          />
                        ) : (
                          <img
                            src={getDocumentFileUrl(doc.document_id)}
                            alt={`Original uploaded file: ${doc.filename}`}
                            className="max-w-full max-h-[600px] object-contain rounded-sm shadow-md"
                          />
                        )
                      ) : (
                        <div className="flex flex-col items-center gap-2 text-slate opacity-70">
                          <FileText size={30} />
                          <span className="text-sm font-medium">Original file unavailable</span>
                        </div>
                      )}
                    </div>
                    <div className="p-2.5 border-t border-line text-xs text-slate">
                      Compare this source with the extracted JSON →
                    </div>
                  </section>

                  <section className="flex flex-col min-w-0" aria-label="Extracted JSON">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-xs text-slate font-mono">
                        schema: ClinicalFieldsSchema (with confidence scores)
                      </span>
                      <button className="flex items-center gap-1.5 text-xs font-semibold text-slate hover:text-ink transition-colors bg-transparent border-0" onClick={handleCopyJson}>
                        {copied ? <Check size={14} className="text-success" /> : <Copy size={14} />}
                        <span>{copied ? 'Copied!' : 'Copy JSON'}</span>
                      </button>
                    </div>

                    {/* Confidence Legend */}
                    <div className="flex items-center gap-3 mb-4 text-xs flex-wrap">
                      <span className="font-bold text-slate uppercase tracking-wider">Confidence:</span>
                      <span className="flex items-center gap-1 text-slate font-medium">
                        <span className="w-2 h-2 rounded-full bg-success"></span> High (≥ 0.80)
                      </span>
                      <span className="flex items-center gap-1 text-slate font-medium">
                        <span className="w-2 h-2 rounded-full bg-warning"></span> Medium (0.50–0.79)
                      </span>
                      <span className="flex items-center gap-1 text-slate font-medium">
                        <span className="w-2 h-2 rounded-full bg-danger"></span> Low (&lt; 0.50)
                      </span>
                    </div>

                    {/* Field-by-field confidence table */}
                    <div className="grid grid-cols-1 gap-2 mb-4">
                      {Object.keys(fields).map(fieldKey => {
                        const score = confidenceMap[fieldKey];
                        const scoreNum = score !== undefined ? score : null;
                        const colorClass = getConfidenceColorClass(scoreNum);
                        const textColorClass = getConfidenceTextColorClass(scoreNum);
                        const bgContainerClass = getConfidenceBgContainerClass(scoreNum);
                        const label = getConfidenceLabel(scoreNum);
                        const pct = scoreNum !== null ? (scoreNum * 100).toFixed(1) : null;
                        const hasValue = fields[fieldKey] !== null && fields[fieldKey] !== undefined;

                        return (
                          <div className="flex justify-between items-center p-2 rounded-md bg-surface border border-line" key={fieldKey}>
                            <div className="flex items-center gap-2 text-sm font-semibold text-ink font-mono">
                              <span className={`w-2 h-2 rounded-full ${hasValue ? colorClass : 'bg-slate'}`}></span>
                              {fieldKey}
                            </div>
                            <div className="flex items-center justify-end gap-2 w-32 shrink-0">
                              {scoreNum !== null ? (
                                <>
                                  <div className="flex-1 h-1.5 rounded-full bg-line overflow-hidden">
                                    <div className={`h-full rounded-full ${colorClass}`} style={{ width: `${pct}%` }}></div>
                                  </div>
                                  <span className={`text-xs font-bold w-8 text-right ${textColorClass}`}>
                                    {pct}%
                                  </span>
                                  <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${bgContainerClass} ${textColorClass}`}>
                                    {label}
                                  </span>
                                </>
                              ) : (
                                <span className="text-slate text-xs">—</span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {/* Full JSON with confidence scores */}
                    <pre className="bg-paper border border-line rounded-lg p-4 overflow-auto text-sm font-mono text-ink flex-1">
                      <code>{JSON.stringify(fieldsWithConfidence, null, 2)}</code>
                    </pre>
                  </section>
                </div>
              );
            })()
          ) : (
            /* Structured Clinical Summary View */
            <div className="grid grid-cols-1 lg:grid-cols-[0.9fr_1.1fr] gap-4 min-h-[520px]">
              <section className="flex flex-col min-w-0 bg-surface border border-line rounded-lg overflow-hidden" aria-label="Original uploaded document">
                <div className="flex justify-between items-center p-3 border-b border-line bg-paper">
                  <div>
                    <span className="block text-xs font-bold text-slate uppercase tracking-wider mb-0.5">Original upload</span>
                    <strong className="text-sm font-semibold text-ink">{doc.filename}</strong>
                  </div>
                  {doc.raw_uri && (
                    <a className="text-teal font-semibold text-xs hover:underline" href={getDocumentFileUrl(doc.document_id)} target="_blank" rel="noreferrer">
                      Open
                    </a>
                  )}
                </div>
                <div className="flex-1 flex items-center justify-center overflow-auto p-4 bg-paper relative">
                  {doc.raw_uri ? (
                    (doc.filetype || '').toLowerCase() === 'pdf' || doc.filename?.toLowerCase().endsWith('.pdf') ? (
                      <iframe title={`Original uploaded file: ${doc.filename}`} src={getDocumentFileUrl(doc.document_id)} className="w-full h-full min-h-[400px] border-0 rounded-sm bg-white" />
                    ) : (
                      <img src={getDocumentFileUrl(doc.document_id)} alt={`Original uploaded file: ${doc.filename}`} className="max-w-full max-h-[600px] object-contain rounded-sm shadow-md" />
                    )
                  ) : (
                    <div className="flex flex-col items-center gap-2 text-slate opacity-70"><FileText size={30} /><span className="text-sm font-medium">Original file unavailable</span></div>
                  )}
                </div>
                <div className="p-2.5 border-t border-line text-xs text-slate">Original uploaded document</div>
              </section>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 min-w-0 content-start">
                {/* Patient Identifiers */}
                <div className="bg-surface border border-line rounded-lg overflow-hidden flex flex-col">
                  <div className="flex items-center gap-2 p-3 border-b border-line bg-paper text-sm font-bold text-ink">
                    <User size={16} className="text-teal" />
                    <h4>Patient Identifiers</h4>
                  </div>
                  <div className="p-3 flex-1 flex flex-col gap-2 text-sm">
                    <div className="flex flex-col">
                      <span className="text-xs font-bold text-slate uppercase tracking-wider">Name:</span>
                      <span className="text-ink font-medium">{fields.patient_identifier?.name || <em>null</em>}</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-xs font-bold text-slate uppercase tracking-wider">Patient ID / MRN:</span>
                      <span className="text-ink font-medium">{fields.patient_identifier?.patient_id || <em>null</em>}</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-xs font-bold text-slate uppercase tracking-wider">DOB:</span>
                      <span className="text-ink font-medium">{fields.patient_identifier?.dob || <em>null</em>}</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-xs font-bold text-slate uppercase tracking-wider">Gender:</span>
                      <span className="text-ink font-medium">{fields.patient_identifier?.gender || <em>null</em>}</span>
                    </div>
                  </div>
                </div>

                {/* Document & Physician */}
                <div className="bg-surface border border-line rounded-lg overflow-hidden flex flex-col">
                  <div className="flex items-center gap-2 p-3 border-b border-line bg-paper text-sm font-bold text-ink">
                    <Calendar size={16} className="text-teal" />
                    <h4>Document & Physician</h4>
                  </div>
                  <div className="p-3 flex-1 flex flex-col gap-2 text-sm">
                    <div className="flex flex-col">
                      <span className="text-xs font-bold text-slate uppercase tracking-wider">Document Date:</span>
                      <span className="text-ink font-medium">{fields.document_date || <em>null</em>}</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-xs font-bold text-slate uppercase tracking-wider">Ordering Physician:</span>
                      <span className="text-ink font-medium">{fields.ordering_physician?.name || <em>null</em>}</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-xs font-bold text-slate uppercase tracking-wider">Specialty / Dept:</span>
                      <span className="text-ink font-medium">{fields.ordering_physician?.department || fields.ordering_physician?.specialty || <em>null</em>}</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-xs font-bold text-slate uppercase tracking-wider">NPI / License:</span>
                      <span className="text-ink font-medium">{fields.ordering_physician?.npi_or_license || fields.ordering_physician?.npi || <em>null</em>}</span>
                    </div>
                  </div>
                </div>

                {/* Vitals */}
                <div className="col-span-1 sm:col-span-2 bg-surface border border-line rounded-lg overflow-hidden flex flex-col">
                  <div className="flex items-center gap-2 p-3 border-b border-line bg-paper text-sm font-bold text-ink">
                    <Activity size={16} className="text-success" />
                    <h4>Vitals</h4>
                  </div>
                  <div className="p-3 flex-1 flex flex-col gap-2 text-sm">
                    {!fields.vitals || Object.values(fields.vitals).every(v => v === null || v === undefined) ? (
                      <p className="text-slate text-sm">No vitals extracted (null)</p>
                    ) : (
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                        <div className="flex flex-col">
                          <span className="text-xs font-bold text-slate uppercase tracking-wider">Blood Pressure</span>
                          <span className="text-ink font-medium">{fields.vitals.blood_pressure || '-'}</span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-xs font-bold text-slate uppercase tracking-wider">Heart Rate</span>
                          <span className="text-ink font-medium">{fields.vitals.heart_rate || '-'}</span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-xs font-bold text-slate uppercase tracking-wider">Temperature</span>
                          <span className="text-ink font-medium">{fields.vitals.temperature || '-'}</span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-xs font-bold text-slate uppercase tracking-wider">Resp. Rate</span>
                          <span className="text-ink font-medium">{fields.vitals.respiratory_rate || '-'}</span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-xs font-bold text-slate uppercase tracking-wider">SpO2</span>
                          <span className="text-ink font-medium">{fields.vitals.spo2 || fields.vitals.oxygen_saturation || '-'}</span>
                        </div>
                        {fields.vitals.weight && (
                          <div className="flex flex-col">
                            <span className="text-xs font-bold text-slate uppercase tracking-wider">Weight</span>
                            <span className="text-ink font-medium">{fields.vitals.weight}</span>
                          </div>
                        )}
                        {fields.vitals.height && (
                          <div className="flex flex-col">
                            <span className="text-xs font-bold text-slate uppercase tracking-wider">Height</span>
                            <span className="text-ink font-medium">{fields.vitals.height}</span>
                          </div>
                        )}
                        {fields.vitals.bmi && (
                          <div className="flex flex-col">
                            <span className="text-xs font-bold text-slate uppercase tracking-wider">BMI</span>
                            <span className="text-ink font-medium">{fields.vitals.bmi}</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Medications */}
                <div className="col-span-1 sm:col-span-2 bg-surface border border-line rounded-lg overflow-hidden flex flex-col">
                  <div className="flex items-center gap-2 p-3 border-b border-line bg-paper text-sm font-bold text-ink">
                    <Pill size={16} className="text-warning" />
                    <h4>Medications ({Array.isArray(fields.medications) ? fields.medications.length : 0})</h4>
                  </div>
                  <div className="p-3 flex-1 flex flex-col gap-2 text-sm overflow-x-auto">
                    {(!fields.medications || !Array.isArray(fields.medications) || fields.medications.length === 0) ? (
                      <p className="text-slate text-sm">No medications extracted (null)</p>
                    ) : (
                      <table className="w-full text-left border-collapse text-sm whitespace-nowrap">
                        <thead>
                          <tr>
                            <th className="p-2 border-b border-line text-xs text-slate font-bold uppercase tracking-wider">Medication Name</th>
                            <th className="p-2 border-b border-line text-xs text-slate font-bold uppercase tracking-wider">Dosage</th>
                            <th className="p-2 border-b border-line text-xs text-slate font-bold uppercase tracking-wider">Frequency</th>
                            <th className="p-2 border-b border-line text-xs text-slate font-bold uppercase tracking-wider">Route</th>
                            <th className="p-2 border-b border-line text-xs text-slate font-bold uppercase tracking-wider">Duration</th>
                          </tr>
                        </thead>
                        <tbody>
                          {fields.medications.map((m, idx) => {
                            const medName = typeof m === 'string' ? m : (m?.medication_name || m?.name || '-');
                            return (
                              <tr key={idx}>
                                <td className="p-2 border-b border-line text-ink font-semibold">{medName}</td>
                                <td className="p-2 border-b border-line text-ink">{typeof m === 'object' ? (m?.dosage || '-') : '-'}</td>
                                <td className="p-2 border-b border-line text-ink">{typeof m === 'object' ? (m?.frequency || '-') : '-'}</td>
                                <td className="p-2 border-b border-line text-ink">{typeof m === 'object' ? (m?.route || '-') : '-'}</td>
                                <td className="p-2 border-b border-line text-ink">{typeof m === 'object' ? (m?.duration || '-') : '-'}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    )}
                  </div>
                </div>

                {/* Lab Results */}
                <div className="col-span-1 sm:col-span-2 bg-surface border border-line rounded-lg overflow-hidden flex flex-col">
                  <div className="flex items-center gap-2 p-3 border-b border-line bg-paper text-sm font-bold text-ink">
                    <FlaskConical size={16} className="text-teal" />
                    <h4>Lab Results ({Array.isArray(fields.lab_results) ? fields.lab_results.length : 0})</h4>
                  </div>
                  <div className="p-3 flex-1 flex flex-col gap-2 text-sm overflow-x-auto">
                    {(!fields.lab_results || !Array.isArray(fields.lab_results) || fields.lab_results.length === 0) ? (
                      <p className="text-slate text-sm">No lab results extracted (null)</p>
                    ) : (
                      <table className="w-full text-left border-collapse text-sm whitespace-nowrap">
                        <thead>
                          <tr>
                            <th className="p-2 border-b border-line text-xs text-slate font-bold uppercase tracking-wider">Test Name</th>
                            <th className="p-2 border-b border-line text-xs text-slate font-bold uppercase tracking-wider">Value</th>
                            <th className="p-2 border-b border-line text-xs text-slate font-bold uppercase tracking-wider">Unit</th>
                            <th className="p-2 border-b border-line text-xs text-slate font-bold uppercase tracking-wider">Reference Range</th>
                            <th className="p-2 border-b border-line text-xs text-slate font-bold uppercase tracking-wider">Flag</th>
                          </tr>
                        </thead>
                        <tbody>
                          {fields.lab_results.map((l, idx) => {
                            const testName = typeof l === 'string' ? l : (l?.test_name || '-');
                            const val = typeof l === 'object' ? (l?.value || '-') : '-';
                            const unit = typeof l === 'object' ? (l?.unit || '-') : '-';
                            const refRange = typeof l === 'object' ? (l?.reference_range || '-') : '-';
                            const flag = typeof l === 'object' ? l?.flag : null;
                            return (
                              <tr key={idx}>
                                <td className="p-2 border-b border-line text-ink font-semibold">{testName}</td>
                                <td className="p-2 border-b border-line text-teal font-semibold">{val}</td>
                                <td className="p-2 border-b border-line text-ink">{unit}</td>
                                <td className="p-2 border-b border-line text-ink">{refRange}</td>
                                <td className="p-2 border-b border-line text-ink">
                                  {flag ? (
                                    <span className="px-2 py-0.5 rounded-md text-xs font-semibold bg-danger/20 text-danger">
                                      {String(flag)}
                                    </span>
                                  ) : '-'}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    )}
                  </div>
                </div>

                {/* Diagnoses, Symptoms & Procedures */}
                <div className="col-span-1 sm:col-span-2 bg-surface border border-line rounded-lg overflow-hidden flex flex-col">
                  <div className="flex items-center gap-2 p-3 border-b border-line bg-paper text-sm font-bold text-ink">
                    <Stethoscope size={16} className="text-teal" />
                    <h4>Diagnoses, Symptoms & Procedures</h4>
                  </div>
                  <div className="p-3 flex-1 flex flex-col gap-3 text-sm">
                    <div>
                      <span className="text-xs font-bold text-slate uppercase tracking-wider block mb-1">Diagnoses:</span>
                      {(!fields.diagnosis || !Array.isArray(fields.diagnosis) || fields.diagnosis.length === 0) ? (
                        <span className="text-ink font-medium"><em>null</em></span>
                      ) : (
                        <div className="flex flex-wrap gap-1.5">
                          {fields.diagnosis.map((d, i) => {
                            if (typeof d === 'string') {
                              return (
                                <span key={i} className="px-2 py-0.5 rounded-md text-xs font-semibold bg-teal/10 text-teal">
                                  {d}
                                </span>
                              );
                            }
                            const code = d?.icd10_code || d?.code;
                            const name = d?.condition_name || d?.name || d?.description || (typeof d === 'object' ? JSON.stringify(d) : String(d));
                            return (
                              <span key={i} className="px-2 py-0.5 rounded-md text-xs font-semibold bg-teal/10 text-teal">
                                {code ? `[${code}] ` : ''}{name}
                              </span>
                            );
                          })}
                        </div>
                      )}
                    </div>
                    <div>
                      <span className="text-xs font-bold text-slate uppercase tracking-wider block mb-1">Symptoms:</span>
                      {(!fields.symptoms || !Array.isArray(fields.symptoms) || fields.symptoms.length === 0) ? (
                        <span className="text-ink font-medium"><em>null</em></span>
                      ) : (
                        <div className="flex flex-wrap gap-1.5">
                          {fields.symptoms.map((s, i) => {
                            const name = typeof s === 'string' ? s : (s?.name || s?.symptom || JSON.stringify(s));
                            return (
                              <span key={i} className="px-2 py-0.5 rounded-md text-xs font-semibold bg-paper border border-line text-slate">{name}</span>
                            );
                          })}
                        </div>
                      )}
                    </div>
                    {fields.procedures && Array.isArray(fields.procedures) && fields.procedures.length > 0 && (
                      <div>
                        <span className="text-xs font-bold text-slate uppercase tracking-wider block mb-1">Procedures:</span>
                        <div className="flex flex-wrap gap-1.5">
                          {fields.procedures.map((p, i) => {
                            const name = typeof p === 'string' ? p : (p?.name || p?.procedure || JSON.stringify(p));
                            return (
                              <span key={i} className="px-2 py-0.5 rounded-md text-xs font-semibold bg-success/15 text-success">
                                {name}
                              </span>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
