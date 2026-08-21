import React, { useState, useRef, useEffect } from 'react';
import {
  MessageCircleQuestion,
  User,
  RefreshCw,
  Send,
  FileText,
  AlertTriangle,
  Info
} from 'lucide-react';
import { askPatientQuestion, getDocumentFileUrl, fetchPatient } from '../services/api';
import { useParams, useNavigate } from 'react-router-dom';

export default function PatientQAPage() {
  const { patientId } = useParams();
  const navigate = useNavigate();
  const [patientIdInput, setPatientIdInput] = useState(patientId || '');
  const [activePatientId, setActivePatientId] = useState('');
  
  // Chat state
  const [history, setHistory] = useState([]); // { role: 'user' | 'assistant', text: string, sources: [] }
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [errorType, setErrorType] = useState(null); // 'not_found', 'server_error', 'validation'
  const chatEndRef = useRef(null);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [history, loading, error]);

  // Sync state with URL params
  useEffect(() => {
    if (patientId && patientId !== activePatientId) {
      setPatientIdInput(patientId);
      // Trigger load patient automatically if route changes
      loadPatientData(patientId);
    }
  }, [patientId]);

  const loadPatientData = async (idToLoad) => {
    if (!idToLoad) return;
    
    setLoading(true);
    setError(null);
    setErrorType(null);
    
    try {
      await fetchPatient(idToLoad);
      setActivePatientId(idToLoad);
      setHistory([]);
      setQuestion('');
    } catch (err) {
      setError(`Patient '${idToLoad}' not found. Please verify the ID/MRN.`);
      setErrorType('not_found');
      setActivePatientId('');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadPatient = (e) => {
    e.preventDefault();
    if (!patientIdInput.trim()) return;
    navigate(`/patients/${patientIdInput.trim()}/ask`);
  };

  const handleClearPatient = () => {
    setPatientIdInput('');
    setActivePatientId('');
    setHistory([]);
    setQuestion('');
    setError(null);
    setErrorType(null);
    navigate('/patients');
  };

  const handleAskQuestion = async (e) => {
    e.preventDefault();
    if (!question.trim() || !activePatientId || loading) return;

    const userQuestion = question.trim();
    setHistory(prev => [...prev, { role: 'user', text: userQuestion }]);
    setQuestion('');
    setLoading(true);
    setError(null);
    setErrorType(null);

    try {
      const data = await askPatientQuestion(activePatientId, userQuestion);
      setHistory(prev => [...prev, { 
        role: 'assistant', 
        text: data.answer,
        sources: data.source_documents || []
      }]);
    } catch (err) {
      console.error('Failed to ask question:', err);
      const status = err.response?.status;
      let errorMsg = 'Failed to reach the server. Please try again.';
      let eType = 'server_error';

      if (err.response?.data?.detail) {
        if (typeof err.response.data.detail === 'string') {
          errorMsg = err.response.data.detail;
        } else if (Array.isArray(err.response.data.detail)) {
          errorMsg = err.response.data.detail.map(d => d.msg).join(', ');
          eType = 'validation';
        }
        if (status === 404) eType = 'not_found';
      } else if (status >= 500) {
        errorMsg = 'Network or server error (500). Please try again later.';
      } else if (status === 404) {
        errorMsg = 'Patient not found or no documents indexed yet.';
        eType = 'not_found';
      }
      
      setError(errorMsg);
      setErrorType(eType);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container" style={{ paddingBottom: '3rem', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header Section */}
      <header className="app-header" style={{ flexShrink: 0 }}>
        <div className="brand-wrapper">
          <div className="brand-logo" style={{ background: 'linear-gradient(135deg, var(--primary-violet), var(--primary-cyan))' }}>
            <MessageCircleQuestion size={26} color="#ffffff" />
          </div>
          <div className="brand-title">
            <h1>Patient Q&A</h1>
            <p>Query clinical intelligence scoped to a specific patient</p>
          </div>
        </div>
      </header>

      {/* Patient Selection Toolbar */}
      <div className="glass-card" style={{ marginBottom: '1.5rem', padding: '1.25rem 1.5rem', flexShrink: 0 }}>
        <form onSubmit={handleLoadPatient} style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--primary-violet)', fontWeight: '600', fontSize: '0.9rem' }}>
            <User size={16} />
            <span>Target Patient:</span>
          </div>

          <div style={{ position: 'relative', flex: 1, minWidth: '220px' }}>
            <User size={16} style={{ position: 'absolute', left: '0.85rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Enter Patient ID (e.g. P001)..."
              value={patientIdInput}
              onChange={(e) => setPatientIdInput(e.target.value)}
              disabled={!!activePatientId}
              style={{
                width: '100%',
                padding: '0.6rem 0.85rem 0.6rem 2.5rem',
                background: 'rgba(15, 23, 42, 0.7)',
                border: '1px solid var(--border-light)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--text-main)',
                fontSize: '0.875rem',
                outline: 'none',
                opacity: activePatientId ? 0.6 : 1
              }}
            />
          </div>

          {!activePatientId ? (
            <button type="submit" className="btn btn-primary" disabled={loading} style={{ padding: '0.6rem 1.25rem', fontSize: '0.85rem', background: 'linear-gradient(135deg, var(--primary-violet), var(--primary-blue))', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              {loading && <RefreshCw size={14} className="spin" />}
              {loading ? 'Loading...' : 'Load Patient'}
            </button>
          ) : (
            <button type="button" className="btn btn-secondary" onClick={handleClearPatient} style={{ padding: '0.6rem 1rem', fontSize: '0.85rem' }}>
              Change Patient
            </button>
          )}
        </form>
      </div>

      {/* Global Error Banner for Patient Loading */}
      {error && !activePatientId && (
        <div 
          className={`alert-banner ${errorType === 'server_error' ? 'error' : ''}`} 
          style={{ 
            marginBottom: '1.5rem',
            ...(errorType !== 'server_error' ? { 
              background: 'rgba(245, 158, 11, 0.12)', 
              border: '1px solid rgba(245, 158, 11, 0.3)', 
              color: '#FCD34D' 
            } : {})
          }}
        >
          {errorType === 'server_error' ? <AlertTriangle size={18} style={{ flexShrink: 0 }} /> : <Info size={18} style={{ flexShrink: 0 }} />}
          <span style={{ marginLeft: '0.75rem' }}>{error}</span>
        </div>
      )}

      {/* Main Chat Area */}
      {!activePatientId ? (
        <div className="glass-card" style={{ textAlign: 'center', padding: '5rem 1.5rem', flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <MessageCircleQuestion size={48} color="var(--text-muted)" style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
          <h3 style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-main)' }}>
            No patient loaded
          </h3>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', maxWidth: '460px', margin: '0 auto' }}>
            Enter a Patient ID above to start asking questions about their clinical records.
          </p>
        </div>
      ) : (
        <div className="glass-card" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', padding: 0 }}>
          
          {/* Chat History */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {history.length === 0 && !loading && !error && (
              <div style={{ textAlign: 'center', margin: 'auto', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                <p>Ask a question about Patient <strong>{activePatientId}</strong>.</p>
                <p style={{ fontSize: '0.8rem', marginTop: '0.5rem', opacity: 0.7 }}>e.g., "What medications is the patient taking?"</p>
              </div>
            )}

            {history.map((msg, i) => (
              <div key={i} style={{ 
                alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: '85%',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.5rem'
              }}>
                <div style={{
                  background: msg.role === 'user' 
                    ? 'linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(59, 130, 246, 0.2))' 
                    : 'rgba(15, 23, 42, 0.6)',
                  border: `1px solid ${msg.role === 'user' ? 'rgba(139, 92, 246, 0.4)' : 'var(--border-light)'}`,
                  borderRadius: 'var(--radius-md)',
                  padding: '1rem 1.25rem',
                  color: 'var(--text-main)',
                  fontSize: '0.95rem',
                  lineHeight: '1.5',
                  whiteSpace: 'pre-wrap'
                }}>
                  {msg.text}
                </div>
                
                {/* Sources Chips */}
                {msg.sources && msg.sources.length > 0 && (() => {
                  const uniqueDocIds = Array.from(new Set(msg.sources.map(source => typeof source === 'string' ? source : source.document_id)));
                  return (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', paddingLeft: '0.25rem' }}>
                      {uniqueDocIds.map((docId, idx) => (
                        <a
                          key={`${docId}-${idx}`}
                          href={getDocumentFileUrl(docId)}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.3rem',
                            background: 'rgba(6, 182, 212, 0.1)',
                            border: '1px solid rgba(6, 182, 212, 0.25)',
                            padding: '0.2rem 0.6rem',
                            borderRadius: 'var(--radius-full)',
                            fontSize: '0.75rem',
                            color: 'var(--primary-cyan)',
                            textDecoration: 'none',
                            transition: 'all 0.2s'
                          }}
                          onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(6, 182, 212, 0.2)'; e.currentTarget.style.borderColor = 'rgba(6, 182, 212, 0.4)'; }}
                          onMouseOut={(e) => { e.currentTarget.style.background = 'rgba(6, 182, 212, 0.1)'; e.currentTarget.style.borderColor = 'rgba(6, 182, 212, 0.25)'; }}
                        >
                          <FileText size={12} />
                          Source {idx + 1}
                        </a>
                      ))}
                    </div>
                  );
                })()}
              </div>
            ))}

            {loading && (
              <div style={{ alignSelf: 'flex-start', background: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border-light)', borderRadius: 'var(--radius-md)', padding: '1rem 1.25rem' }}>
                <RefreshCw size={20} className="spin" color="var(--primary-cyan)" />
              </div>
            )}
            
            {error && (
              <div 
                className={`alert-banner ${errorType === 'server_error' ? 'error' : ''}`} 
                style={{ 
                  alignSelf: 'center', 
                  maxWidth: '85%', 
                  marginBottom: 0,
                  ...(errorType !== 'server_error' ? { 
                    background: 'rgba(245, 158, 11, 0.12)', 
                    border: '1px solid rgba(245, 158, 11, 0.3)', 
                    color: '#FCD34D' 
                  } : {})
                }}
              >
                {errorType === 'server_error' ? <AlertTriangle size={18} style={{ flexShrink: 0 }} /> : <Info size={18} style={{ flexShrink: 0 }} />}
                <span style={{ marginLeft: '0.75rem' }}>{error}</span>
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          {/* Input Area */}
          <div style={{ padding: '1.25rem', borderTop: '1px solid var(--border-light)', background: 'rgba(8, 12, 20, 0.4)' }}>
            <form onSubmit={handleAskQuestion} style={{ display: 'flex', gap: '0.75rem' }}>
              <input
                type="text"
                placeholder={`Ask a question about Patient ${activePatientId}...`}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                disabled={loading}
                style={{
                  flex: 1,
                  padding: '0.85rem 1.25rem',
                  background: 'rgba(15, 23, 42, 0.7)',
                  border: '1px solid var(--border-light)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-main)',
                  fontSize: '0.95rem',
                  outline: 'none',
                  transition: 'border-color 0.2s'
                }}
                onFocus={(e) => e.target.style.borderColor = 'var(--primary-violet)'}
                onBlur={(e) => e.target.style.borderColor = 'var(--border-light)'}
              />
              <button
                type="submit"
                disabled={!question.trim() || loading}
                className="btn btn-primary"
                style={{ 
                  padding: '0 1.5rem',
                  background: 'linear-gradient(135deg, var(--primary-violet), var(--primary-blue))',
                  opacity: (!question.trim() || loading) ? 0.5 : 1
                }}
              >
                <Send size={18} />
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
