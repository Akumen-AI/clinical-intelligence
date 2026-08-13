import React, { useState, useEffect } from 'react';
import { Users, Copy, CheckCircle2, User, Activity, AlertCircle, RefreshCw } from 'lucide-react';
import { fetchPatients } from '../services/api';

export default function PatientsPage() {
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copiedId, setCopiedId] = useState(null);

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

  const handleCopyId = (id) => {
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
      {loading ? (
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
            <div key={patient.patient_id} className="glass-card" style={{ padding: '1.5rem', position: 'relative', overflow: 'hidden' }}>
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
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginTop: '0.2rem' }}>MRN: {patient.mrn}</div>
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
                  ID: {patient.patient_id}
                </div>
                <button
                  onClick={() => handleCopyId(patient.patient_id)}
                  className={`btn ${copiedId === patient.patient_id ? 'btn-primary' : 'btn-secondary'}`}
                  style={{
                    padding: '0.35rem 0.75rem',
                    fontSize: '0.75rem',
                    display: 'flex', alignItems: 'center', gap: '0.35rem',
                    background: copiedId === patient.patient_id ? 'var(--accent-emerald)' : '',
                    color: copiedId === patient.patient_id ? '#fff' : ''
                  }}
                >
                  {copiedId === patient.patient_id ? <CheckCircle2 size={14} /> : <Copy size={14} />}
                  {copiedId === patient.patient_id ? 'Copied!' : 'Copy ID'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
