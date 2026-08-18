import React, { useState, useEffect } from 'react';
import { Users, Copy, CheckCircle2, User, AlertCircle, RefreshCw, ChevronLeft, Activity, FileText, Pill, FileSymlink } from 'lucide-react';
import { fetchPatients, fetchPatientRecords } from '../services/api';

function PatientProfileView({ patientId, onBack }) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copiedId, setCopiedId] = useState(null);

  useEffect(() => {
    loadProfile();
  }, [patientId]);

  const loadProfile = async () => {
    setLoading(true);
    try {
      const data = await fetchPatientRecords(patientId);
      setProfile(data);
    } catch (err) {
      console.error(err);
      setError("Failed to load patient profile.");
    } finally {
      setLoading(false);
    }
  };

  const handleCopyId = (id) => {
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  if (loading) {
    return (
      <div className="glass-card" style={{ textAlign: 'center', padding: '4rem 1.5rem', color: 'var(--text-muted)' }}>
        <RefreshCw size={32} className="spin" style={{ margin: '0 auto 1rem', color: 'var(--accent-emerald)' }} />
        <p>Loading profile...</p>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="glass-card" style={{ padding: '2rem', textAlign: 'center' }}>
        <p style={{ color: 'var(--text-error)' }}>{error}</p>
        <button onClick={onBack} className="btn btn-secondary" style={{ marginTop: '1rem' }}>Back</button>
      </div>
    );
  }

  const { patient, diagnoses, medications, lab_results, documents } = profile;

  return (
    <div className="glass-card" style={{ padding: '2rem' }}>
      <button onClick={onBack} className="btn btn-secondary" style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <ChevronLeft size={16} /> Back to Directory
      </button>

      <div className="alert-banner" style={{ marginBottom: '1.5rem', background: 'rgba(56, 189, 248, 0.1)', border: '1px solid var(--primary-cyan)', color: 'var(--primary-cyan)' }}>
        <AlertCircle size={18} style={{ flexShrink: 0 }} />
        <span><strong>Note:</strong> This detailed view is intended for testing/admin purposes, pending clearer product requirements.</span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '2rem' }}>
        <div style={{ width: '64px', height: '64px', borderRadius: '50%', background: 'rgba(16, 185, 129, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-emerald)' }}>
          <User size={32} />
        </div>
        <div>
          <h2 style={{ fontSize: '1.8rem', fontWeight: 600, margin: 0, color: 'var(--text-main)' }}>{patient.name}</h2>
          <div style={{ fontSize: '1rem', color: 'var(--text-dim)', marginTop: '0.2rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <span><strong style={{color: 'var(--text-main)'}}>OP ID:</strong> {patient.patient_number}</span>
            <span><strong style={{color: 'var(--text-main)'}}>MRN:</strong> {patient.mrn}</span>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        <div style={{ background: 'rgba(15, 23, 42, 0.5)', padding: '1rem', borderRadius: 'var(--radius-sm)' }}>
          <span style={{ color: 'var(--text-dim)', display: 'block', fontSize: '0.8rem', marginBottom: '0.3rem' }}>DOB</span>
          <span style={{ color: 'var(--text-main)', fontSize: '1.1rem' }}>{patient.dob || 'Unknown'}</span>
        </div>
        <div style={{ background: 'rgba(15, 23, 42, 0.5)', padding: '1rem', borderRadius: 'var(--radius-sm)' }}>
          <span style={{ color: 'var(--text-dim)', display: 'block', fontSize: '0.8rem', marginBottom: '0.3rem' }}>Sex</span>
          <span style={{ color: 'var(--text-main)', fontSize: '1.1rem' }}>{patient.sex || 'Unknown'}</span>
        </div>
        <div style={{ background: 'rgba(15, 23, 42, 0.5)', padding: '1rem', borderRadius: 'var(--radius-sm)', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <span style={{ color: 'var(--text-dim)', display: 'block', fontSize: '0.8rem', marginBottom: '0.3rem' }}>OP ID</span>
          <button onClick={() => handleCopyId(patient.patient_number || patient.mrn)} className="btn btn-secondary" style={{ padding: '0.3rem 0.5rem', fontSize: '0.75rem', width: 'fit-content' }}>
            {copiedId === (patient.patient_number || patient.mrn) ? <CheckCircle2 size={12} /> : <Copy size={12} />}
            {copiedId === (patient.patient_number || patient.mrn) ? 'Copied!' : 'Copy OP ID'}
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
        {/* Left Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          <section>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-main)', borderBottom: '1px solid var(--border-light)', paddingBottom: '0.5rem', marginBottom: '1rem' }}>
              <Activity size={18} color="var(--accent-emerald)" /> Diagnoses
            </h3>
            {diagnoses.length > 0 ? (
              <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {diagnoses.map(d => (
                  <li key={d.id} style={{ background: 'rgba(255,255,255,0.02)', padding: '0.75rem', borderRadius: 'var(--radius-sm)' }}>
                    <div style={{ color: 'var(--text-main)' }}>{d.raw_text}</div>
                    {d.icd10_code && <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>ICD-10: {d.icd10_code}</div>}
                  </li>
                ))}
              </ul>
            ) : <p style={{ color: 'var(--text-muted)' }}>No diagnoses found.</p>}
          </section>

          <section>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-main)', borderBottom: '1px solid var(--border-light)', paddingBottom: '0.5rem', marginBottom: '1rem' }}>
              <Pill size={18} color="var(--accent-emerald)" /> Medications
            </h3>
            {medications.length > 0 ? (
              <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {medications.map(m => (
                  <li key={m.id} style={{ background: 'rgba(255,255,255,0.02)', padding: '0.75rem', borderRadius: 'var(--radius-sm)' }}>
                    <div style={{ color: 'var(--text-main)' }}>{m.raw_text}</div>
                    {m.rxnorm_code && <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>RxNorm: {m.rxnorm_code}</div>}
                  </li>
                ))}
              </ul>
            ) : <p style={{ color: 'var(--text-muted)' }}>No medications found.</p>}
          </section>
        </div>

        {/* Right Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          <section>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-main)', borderBottom: '1px solid var(--border-light)', paddingBottom: '0.5rem', marginBottom: '1rem' }}>
              <FileSymlink size={18} color="var(--accent-emerald)" /> Lab Results
            </h3>
            {lab_results.length > 0 ? (
              <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {lab_results.map(l => (
                  <li key={l.id} style={{ background: 'rgba(255,255,255,0.02)', padding: '0.75rem', borderRadius: 'var(--radius-sm)' }}>
                    <div style={{ color: 'var(--text-main)' }}>{l.raw_text}</div>
                    {l.loinc_code && <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>LOINC: {l.loinc_code}</div>}
                  </li>
                ))}
              </ul>
            ) : <p style={{ color: 'var(--text-muted)' }}>No lab results found.</p>}
          </section>

          <section>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-main)', borderBottom: '1px solid var(--border-light)', paddingBottom: '0.5rem', marginBottom: '1rem' }}>
              <FileText size={18} color="var(--accent-emerald)" /> Documents
            </h3>
            {documents.length > 0 ? (
              <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {documents.map(d => (
                  <li key={d.document_id} style={{ background: 'rgba(255,255,255,0.02)', padding: '0.75rem', borderRadius: 'var(--radius-sm)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ color: 'var(--text-main)' }}>{d.filename}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>{d.document_type || 'Unknown Type'}</div>
                    </div>
                  </li>
                ))}
              </ul>
            ) : <p style={{ color: 'var(--text-muted)' }}>No documents found.</p>}
          </section>
        </div>
      </div>
    </div>
  );
}

export default function PatientsPage() {
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copiedId, setCopiedId] = useState(null);
  const [selectedPatientId, setSelectedPatientId] = useState(null);

  useEffect(() => {
    loadPatients();
  }, []);

  const loadPatients = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchPatients();
      setPatients(data);
    } catch (err) {
      console.error('Failed to load patients:', err);
      setError('Failed to fetch patient records from the server.');
    } finally {
      setLoading(false);
    }
  };

  const handleCopyId = (e, id) => {
    e.stopPropagation();
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="app-container" style={{ paddingBottom: '3rem' }}>
      {/* Header Section */}
      <header className="app-header">
        <div className="brand-wrapper">
          <div className="brand-logo" style={{ background: 'linear-gradient(135deg, var(--accent-emerald), var(--primary-cyan))' }}>
            <Users size={26} color="#ffffff" />
          </div>
          <div className="brand-title">
            <h1>Patient Directory</h1>
            <p>Browse and manage synthetic patient records</p>
          </div>
        </div>
        <button onClick={loadPatients} className="btn btn-secondary" disabled={loading} style={{ padding: '0.5rem 1rem' }}>
          <RefreshCw size={16} className={loading ? 'spin' : ''} />
          Refresh
        </button>
      </header>

      {/* Error state */}
      {error && (
        <div className="alert-banner error" style={{ marginBottom: '1.5rem' }}>
          <AlertCircle size={18} style={{ flexShrink: 0 }} />
          <span>{error}</span>
        </div>
      )}

      {/* Main Content Area */}
      {selectedPatientId ? (
        <PatientProfileView 
          patientId={selectedPatientId} 
          onBack={() => setSelectedPatientId(null)} 
        />
      ) : loading ? (
        <div className="glass-card" style={{ textAlign: 'center', padding: '4rem 1.5rem', color: 'var(--text-muted)' }}>
          <RefreshCw size={32} className="spin" style={{ margin: '0 auto 1rem', color: 'var(--accent-emerald)' }} />
          <p style={{ fontSize: '1.1rem' }}>Loading patient records...</p>
        </div>
      ) : patients.length === 0 ? (
        <div className="glass-card" style={{ textAlign: 'center', padding: '5rem 1.5rem' }}>
          <Users size={48} color="var(--text-muted)" style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
          <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-main)' }}>
            No patients found
          </h3>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', maxWidth: '400px', margin: '0 auto' }}>
            No synthetic patients have been seeded into the database yet.
          </p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1.5rem' }}>
          {patients.map(patient => (
            <div 
              key={patient.patient_id} 
              className="glass-card patient-card-hover" 
              style={{ padding: '1.5rem', position: 'relative', overflow: 'hidden', cursor: 'pointer', transition: 'all 0.2s ease' }}
              onClick={() => setSelectedPatientId(patient.patient_id)}
            >
              <div style={{ position: 'absolute', top: 0, left: 0, width: '4px', height: '100%', background: 'var(--accent-emerald)' }}></div>
              
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                <div style={{
                  width: '40px', height: '40px', borderRadius: '50%',
                  background: 'rgba(16, 185, 129, 0.15)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: 'var(--accent-emerald)'
                }}>
                  <User size={20} />
                </div>
                <div>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 600, margin: 0, color: 'var(--text-main)' }}>{patient.name}</h3>
                  <div style={{ fontSize: '0.85rem', color: 'var(--primary-cyan)', marginTop: '0.2rem', fontWeight: 500 }}>{patient.patient_number || patient.mrn}</div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1.25rem', fontSize: '0.85rem' }}>
                <div style={{ background: 'rgba(15, 23, 42, 0.5)', padding: '0.5rem 0.75rem', borderRadius: 'var(--radius-sm)' }}>
                  <span style={{ color: 'var(--text-dim)', display: 'block', fontSize: '0.7rem', marginBottom: '0.2rem' }}>DOB</span>
                  <span style={{ color: 'var(--text-main)' }}>{patient.dob || 'Unknown'}</span>
                </div>
                <div style={{ background: 'rgba(15, 23, 42, 0.5)', padding: '0.5rem 0.75rem', borderRadius: 'var(--radius-sm)' }}>
                  <span style={{ color: 'var(--text-dim)', display: 'block', fontSize: '0.7rem', marginBottom: '0.2rem' }}>Sex</span>
                  <span style={{ color: 'var(--text-main)' }}>{patient.sex || 'Unknown'}</span>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-light)', paddingTop: '1rem' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '140px' }}>
                  OP ID: {patient.patient_number || patient.mrn}
                </div>
                <button
                  onClick={(e) => handleCopyId(e, patient.patient_number || patient.mrn)}
                  className={`btn ${copiedId === (patient.patient_number || patient.mrn) ? 'btn-primary' : 'btn-secondary'}`}
                  style={{
                    padding: '0.35rem 0.75rem',
                    fontSize: '0.75rem',
                    display: 'flex', alignItems: 'center', gap: '0.35rem',
                    background: copiedId === (patient.patient_number || patient.mrn) ? 'var(--accent-emerald)' : '',
                    color: copiedId === (patient.patient_number || patient.mrn) ? '#fff' : ''
                  }}
                >
                  {copiedId === (patient.patient_number || patient.mrn) ? <CheckCircle2 size={14} /> : <Copy size={14} />}
                  {copiedId === (patient.patient_number || patient.mrn) ? 'Copied' : 'Copy'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
      <style dangerouslySetInnerHTML={{__html: `
        .patient-card-hover:hover {
          transform: translateY(-2px);
          box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
          border-color: rgba(16, 185, 129, 0.3);
        }
      `}} />
    </div>
  );
}
