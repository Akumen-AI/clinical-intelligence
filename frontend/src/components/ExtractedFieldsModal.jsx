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
import { fetchDocumentFields, extractDocumentFields } from '../services/api';

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
    const jsonStr = JSON.stringify(data.fields || data, null, 2);
    navigator.clipboard.writeText(jsonStr).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  if (!doc) return null;

  const fields = data?.fields || {};
  const records = data?.extracted_records || data?.field_records || [];

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content glass-card" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div className="modal-icon-badge">
              <Sparkles size={20} color="var(--primary-cyan)" />
            </div>
            <div>
              <h2 className="modal-title">Extracted Clinical Fields</h2>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.2rem' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{doc.filename}</span>
                <span className="uuid-text" style={{ fontSize: '0.75rem' }}>{doc.document_id}</span>
                {doc.document_type && (
                  <span className="tag" style={{ background: 'rgba(6, 182, 212, 0.15)', color: 'var(--primary-cyan)' }}>
                    {doc.document_type}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <button
              className="btn btn-secondary"
              onClick={handleRunExtraction}
              disabled={isExtracting}
              style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
              title="Re-run field extraction"
            >
              <RefreshCw size={13} className={isExtracting ? 'spin' : ''} />
              {isExtracting ? 'Extracting...' : 'Re-extract'}
            </button>
            <button className="btn-icon" onClick={onClose} title="Close">
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Modal Navigation Tabs */}
        <div className="modal-tabs">
          <button
            className={`modal-tab ${activeTab === 'json' ? 'active' : ''}`}
            onClick={() => setActiveTab('json')}
          >
            <Code size={16} />
            JSON View (FR-07)
          </button>
          <button
            className={`modal-tab ${activeTab === 'summary' ? 'active' : ''}`}
            onClick={() => setActiveTab('summary')}
          >
            <FileText size={16} />
            Structured Summary
          </button>
        </div>

        {/* Modal Body */}
        <div className="modal-body">
          {isLoading ? (
            <div className="modal-state-box">
              <RefreshCw size={28} className="spin" color="var(--primary-cyan)" />
              <p>Loading extracted fields from database...</p>
            </div>
          ) : error ? (
            <div className="modal-state-box error">
              <AlertCircle size={28} color="var(--accent-rose)" />
              <p>{error}</p>
              <button className="btn btn-primary" onClick={handleRunExtraction} style={{ marginTop: '0.75rem' }}>
                Run Field Extraction
              </button>
            </div>
          ) : !data ? (
            <div className="modal-state-box">
              <FileText size={32} style={{ opacity: 0.5 }} />
              <p>No fields extracted for this document yet.</p>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>
                Click below to extract structured clinical data using the configured extraction provider.
              </p>
              <button 
                className="btn btn-primary" 
                onClick={handleRunExtraction} 
                disabled={isExtracting}
                style={{ marginTop: '0.75rem' }}
              >
                <Sparkles size={16} />
                {isExtracting ? 'Extracting...' : 'Extract Fields Now'}
              </button>
            </div>
          ) : activeTab === 'json' ? (
            /* JSON View */
            <div className="json-container">
              <div className="json-toolbar">
                <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)', fontFamily: 'monospace' }}>
                  schema: ClinicalFieldsSchema (null-preserved)
                </span>
                <button className="btn-copy" onClick={handleCopyJson}>
                  {copied ? <Check size={14} color="#10b981" /> : <Copy size={14} />}
                  <span>{copied ? 'Copied!' : 'Copy JSON'}</span>
                </button>
              </div>
              <pre className="json-code-block">
                <code>{JSON.stringify(fields, null, 2)}</code>
              </pre>
            </div>
          ) : (
            /* Structured Clinical Summary View */
            <div className="summary-cards-grid">
              {/* Patient Identifiers */}
              <div className="summary-card">
                <div className="summary-card-header">
                  <User size={16} color="var(--primary-cyan)" />
                  <h4>Patient Identifiers</h4>
                </div>
                <div className="summary-card-content">
                  <div className="field-row">
                    <span className="field-label">Name:</span>
                    <span className="field-val">{fields.patient_identifier?.name || <em>null</em>}</span>
                  </div>
                  <div className="field-row">
                    <span className="field-label">Patient ID / MRN:</span>
                    <span className="field-val">{fields.patient_identifier?.patient_id || <em>null</em>}</span>
                  </div>
                  <div className="field-row">
                    <span className="field-label">DOB:</span>
                    <span className="field-val">{fields.patient_identifier?.dob || <em>null</em>}</span>
                  </div>
                  <div className="field-row">
                    <span className="field-label">Age / Gender:</span>
                    <span className="field-val">
                      {fields.patient_identifier?.age ? `${fields.patient_identifier.age} yrs` : 'null'} / {fields.patient_identifier?.gender || 'null'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Document & Physician */}
              <div className="summary-card">
                <div className="summary-card-header">
                  <Calendar size={16} color="var(--primary-blue)" />
                  <h4>Document & Physician</h4>
                </div>
                <div className="summary-card-content">
                  <div className="field-row">
                    <span className="field-label">Document Date:</span>
                    <span className="field-val">{fields.document_date || <em>null</em>}</span>
                  </div>
                  <div className="field-row">
                    <span className="field-label">Ordering Physician:</span>
                    <span className="field-val">{fields.ordering_physician?.name || <em>null</em>}</span>
                  </div>
                  <div className="field-row">
                    <span className="field-label">Specialty / Dept:</span>
                    <span className="field-val">{fields.ordering_physician?.specialty || fields.ordering_physician?.department || <em>null</em>}</span>
                  </div>
                  <div className="field-row">
                    <span className="field-label">NPI / License:</span>
                    <span className="field-val">{fields.ordering_physician?.npi_or_license || fields.ordering_physician?.npi || <em>null</em>}</span>
                  </div>
                </div>
              </div>

              {/* Vitals */}
              {fields.vitals && (
                <div className="summary-card full-width">
                  <div className="summary-card-header">
                    <Activity size={16} color="var(--accent-emerald)" />
                    <h4>Vitals</h4>
                  </div>
                  <div className="vitals-grid">
                    <div className="vital-item">
                      <span className="vital-label">Blood Pressure</span>
                      <span className="vital-val">{fields.vitals.blood_pressure || 'null'}</span>
                    </div>
                    <div className="vital-item">
                      <span className="vital-label">Heart Rate</span>
                      <span className="vital-val">{fields.vitals.heart_rate || 'null'}</span>
                    </div>
                    <div className="vital-item">
                      <span className="vital-label">Temperature</span>
                      <span className="vital-val">{fields.vitals.temperature || 'null'}</span>
                    </div>
                    <div className="vital-item">
                      <span className="vital-label">Respiratory Rate</span>
                      <span className="vital-val">{fields.vitals.respiratory_rate || 'null'}</span>
                    </div>
                    <div className="vital-item">
                      <span className="vital-label">SpO2</span>
                      <span className="vital-val">{fields.vitals.oxygen_saturation || 'null'}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Medications */}
              <div className="summary-card full-width">
                <div className="summary-card-header">
                  <Pill size={16} color="var(--accent-amber)" />
                  <h4>Medications ({fields.medications?.length || 0})</h4>
                </div>
                <div className="summary-card-content">
                  {(!fields.medications || fields.medications.length === 0) ? (
                    <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem' }}>No medications extracted (null)</p>
                  ) : (
                    <table className="mini-table">
                      <thead>
                        <tr>
                          <th>Medication Name</th>
                          <th>Dosage</th>
                          <th>Frequency</th>
                          <th>Route</th>
                          <th>Duration</th>
                        </tr>
                      </thead>
                      <tbody>
                        {fields.medications.map((m, idx) => (
                          <tr key={idx}>
                            <td style={{ fontWeight: '600', color: 'var(--text-main)' }}>{m.name || '-'}</td>
                            <td>{m.dosage || '-'}</td>
                            <td>{m.frequency || '-'}</td>
                            <td>{m.route || '-'}</td>
                            <td>{m.duration || '-'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>

              {/* Lab Results */}
              <div className="summary-card full-width">
                <div className="summary-card-header">
                  <FlaskConical size={16} color="var(--primary-violet)" />
                  <h4>Lab Results ({fields.lab_results?.length || 0})</h4>
                </div>
                <div className="summary-card-content">
                  {(!fields.lab_results || fields.lab_results.length === 0) ? (
                    <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem' }}>No lab results extracted (null)</p>
                  ) : (
                    <table className="mini-table">
                      <thead>
                        <tr>
                          <th>Test Name</th>
                          <th>Value</th>
                          <th>Unit</th>
                          <th>Reference Range</th>
                          <th>Flag</th>
                        </tr>
                      </thead>
                      <tbody>
                        {fields.lab_results.map((l, idx) => (
                          <tr key={idx}>
                            <td style={{ fontWeight: '600', color: 'var(--text-main)' }}>{l.test_name || '-'}</td>
                            <td style={{ color: 'var(--primary-cyan)', fontWeight: '600' }}>{l.value || '-'}</td>
                            <td>{l.unit || '-'}</td>
                            <td>{l.reference_range || '-'}</td>
                            <td>
                              {l.flag ? (
                                <span className="tag" style={{ background: 'rgba(239, 68, 68, 0.2)', color: '#ef4444' }}>
                                  {l.flag}
                                </span>
                              ) : '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>

              {/* Diagnoses, Symptoms & Procedures */}
              <div className="summary-card full-width">
                <div className="summary-card-header">
                  <Stethoscope size={16} color="var(--primary-cyan)" />
                  <h4>Diagnoses, Symptoms & Procedures</h4>
                </div>
                <div className="summary-card-content" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  <div>
                    <span className="field-label" style={{ display: 'block', marginBottom: '0.25rem' }}>Diagnoses:</span>
                    {(!fields.diagnosis || fields.diagnosis.length === 0) ? (
                      <span className="field-val"><em>null</em></span>
                    ) : (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                        {fields.diagnosis.map((d, i) => (
                          <span key={i} className="tag" style={{ background: 'rgba(59, 130, 246, 0.15)', color: 'var(--primary-blue)' }}>
                            {d.code ? `[${d.code}] ` : ''}{d.description || d}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div>
                    <span className="field-label" style={{ display: 'block', marginBottom: '0.25rem' }}>Symptoms:</span>
                    {(!fields.symptoms || fields.symptoms.length === 0) ? (
                      <span className="field-val"><em>null</em></span>
                    ) : (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                        {fields.symptoms.map((s, i) => (
                          <span key={i} className="tag">{s}</span>
                        ))}
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
