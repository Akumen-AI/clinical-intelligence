import React, { useState, useRef, useEffect } from 'react';
import {
  MessageCircleQuestion,
  User,
  RefreshCw,
  Send,
  FileText,
  AlertTriangle,
  Info,
  ExternalLink,
  PlusCircle,
  FileSearch
} from 'lucide-react';
import { askPatientQuestion, getDocumentFileUrl, fetchPatient } from '../services/api';
import { useParams, useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
const parseSnippetData = (snippet) => {
  if (!snippet) return { type: 'text', text: '' };
  
  if (snippet.includes('"test_name"')) {
    const labResults = [];
    const parts = snippet.split('"test_name"');
    for (let i = 1; i < parts.length; i++) {
       const part = parts[i];
       const nameMatch = part.match(/^\s*:\s*"([^"]+)"/);
       const valMatch = part.match(/"value"\s*:\s*"?([^",}]+)"?/);
       const unitMatch = part.match(/"unit"\s*:\s*"([^"]+)"/);
       const flagMatch = part.match(/"flag"\s*:\s*"([^"]+)"/);
       
       if (nameMatch && valMatch) {
         labResults.push({
           name: nameMatch[1],
           value: valMatch[1].replace(/"/g, ''),
           unit: unitMatch ? unitMatch[1] : '',
           flag: flagMatch && flagMatch[1] !== 'null' ? flagMatch[1] : ''
         });
       }
    }
    if (labResults.length > 0) {
      return { type: 'labs', data: labResults };
    }
  }
  
  if (snippet.includes('":')) {
    let clean = snippet.replace(/[{}]/g, '').trim();
    clean = clean.replace(/"([^"]+)"\s*:/g, '$1:').replace(/"/g, '');
    return { type: 'text', text: clean };
  }
  
  return { type: 'text', text: snippet };
};

export default function PatientQAPage() {
  const { patientId } = useParams();
  const navigate = useNavigate();
  const [patientIdInput, setPatientIdInput] = useState(patientId || '');
  const [activePatientId, setActivePatientId] = useState('');
  const [activePatient, setActivePatient] = useState(null);
  
  // Chat state
  const [history, setHistory] = useState([]); // { role: 'user' | 'assistant', text: string, sources: CitationSchema[] }
  const [question, setQuestion] = useState('');
  const [conversationId, setConversationId] = useState(null);
  
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
      loadPatientData(patientId);
    }
  }, [patientId]);

  const loadPatientData = async (idToLoad) => {
    if (!idToLoad) return;
    
    setLoading(true);
    setError(null);
    setErrorType(null);
    
    try {
      const patientData = await fetchPatient(idToLoad);
      setActivePatientId(idToLoad);
      setActivePatient(patientData);
      // Explicitly clear conversation context when switching patients
      resetConversation();
    } catch (err) {
      setError(`Patient '${idToLoad}' not found. Please verify the ID/MRN.`);
      setErrorType('not_found');
      setActivePatientId('');
      setActivePatient(null);
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
    setActivePatient(null);
    resetConversation();
    setError(null);
    setErrorType(null);
    navigate('/patients');
  };

  const resetConversation = () => {
    setHistory([]);
    setQuestion('');
    setConversationId(null);
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
      const data = await askPatientQuestion(activePatientId, userQuestion, conversationId);
      
      // Store the conversation ID returned by the backend for subsequent turns
      if (data.conversation_id) {
        setConversationId(data.conversation_id);
      }

      const sources = data.citations || data.source_documents || [];
      
      setHistory(prev => [...prev, { 
        role: 'assistant', 
        text: data.answer,
        sources: sources
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

  // Derive the active contexts for the right-hand browser based on the *most recent* assistant response
  const activeContexts = history.length > 0 && history[history.length - 1].role === 'assistant' 
    ? history[history.length - 1].sources || [] 
    : [];

  // Group contexts by document_id to avoid duplicates
  const groupedContexts = React.useMemo(() => {
    const groups = {};
    activeContexts.forEach(ctx => {
      const docId = typeof ctx === 'string' ? ctx : ctx.document_id;
      if (!groups[docId]) {
        groups[docId] = {
          docId,
          snippets: []
        };
      }
      if (typeof ctx === 'object') {
        groups[docId].snippets.push(ctx);
      }
    });
    return Object.values(groups);
  }, [activeContexts]);

  return (
    <div className="app-container flex-1 flex flex-col min-h-0">
      
      {/* Header Section */}
      <header className="app-header">
        <div className="brand-wrapper">
          <div className="brand-logo" style={{ background: 'linear-gradient(135deg, var(--accent-emerald), var(--primary-cyan))' }}>
            <MessageCircleQuestion size={26} color="#ffffff" />
          </div>
          <div className="brand-title">
            <h1>Patient Clinical Q&A</h1>
            <p>Query verified clinical intelligence scoped to a specific patient.</p>
          </div>
        </div>

        {/* Patient Selection Form */}
        <form onSubmit={handleLoadPatient} className="flex items-center gap-3 bg-surface-container-high px-4 py-1.5 rounded-xl border border-outline-variant/20">
          <div className="flex items-center gap-2 text-sm font-semibold text-primary">
            <User size={16} />
            <span className="hidden sm:inline-block">Target Patient:</span>
          </div>

          <div className="relative w-48">
            <input
              type="text"
              placeholder="e.g. P001..."
              value={patientIdInput}
              onChange={(e) => setPatientIdInput(e.target.value)}
              disabled={!!activePatientId}
              className="w-full pl-3 pr-3 py-1.5 bg-surface-container-highest/50 border border-outline-variant/40 rounded-lg text-sm text-on-surface focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary disabled:opacity-60"
            />
          </div>

          {!activePatientId ? (
            <button type="submit" disabled={loading} className="btn btn-primary px-4 py-1.5 text-sm whitespace-nowrap flex items-center gap-2">
              {loading && <RefreshCw size={14} className="animate-spin" />}
              {loading ? 'Loading...' : 'Load'}
            </button>
          ) : (
            <button type="button" onClick={handleClearPatient} className="btn btn-secondary px-4 py-1.5 text-sm whitespace-nowrap">
              Change
            </button>
          )}
        </form>
      </header>

      {/* Global Error for Patient Loading */}
      {error && !activePatientId && (
        <div className={`p-4 mb-6 rounded-xl border flex items-start gap-3 ${errorType === 'server_error' ? 'bg-error-container/20 border-error/30 text-error' : 'bg-amber-500/10 border-amber-500/30 text-amber-500'}`}>
          {errorType === 'server_error' ? <AlertTriangle size={20} className="shrink-0 mt-0.5" /> : <Info size={20} className="shrink-0 mt-0.5" />}
          <span className="font-medium">{error}</span>
        </div>
      )}

      {!activePatientId ? (
        <div className="flex-1 flex flex-col items-center justify-center bg-surface-container rounded-2xl border border-outline-variant/20 p-8 text-center mt-4">
          <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center mb-6">
            <MessageCircleQuestion size={40} className="text-primary" />
          </div>
          <h2 className="text-headline-sm font-headline-sm text-on-surface mb-2">No patient loaded</h2>
          <p className="text-on-surface-variant max-w-md">Enter a Patient ID above to securely query their clinical documents and records via RAG.</p>
        </div>
      ) : (
        <div className="flex-1 flex flex-col lg:flex-row gap-6 min-h-0">
          
          {/* ── Left Pane: Chat Thread ── */}
          <div className="flex-1 flex flex-col bg-surface-container rounded-2xl border border-outline-variant/20 overflow-hidden relative shadow-sm min-h-[500px]">
            
            {/* Patient Context Header */}
            {activePatient && (
              <div className="bg-surface-container-highest/40 border-b border-outline-variant/10 px-5 py-4 flex justify-between items-center shrink-0">
                <div>
                  <h2 className="text-lg font-bold text-on-surface">
                    Patient Context: {activePatient.name || 'Unknown Name'}
                  </h2>
                  <div className="text-sm text-on-surface-variant flex items-center gap-2 mt-1">
                    <span>MRN: #{activePatient.mrn || activePatient.patient_number || activePatient.patient_id.slice(0, 8)}</span>
                    <span>&bull;</span>
                    <span>{activePatient.sex || 'Unknown'}</span>
                    <span>&bull;</span>
                    <span>{activePatient.dob ? `${Math.floor((new Date() - new Date(activePatient.dob)) / 31557600000)}y` : 'Age Unknown'}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                  AI Active
                </div>
              </div>
            )}
            
            {/* Chat Toolbar */}
            <div className="flex justify-between items-center px-4 py-2 bg-surface-container-high border-b border-outline-variant/10 shadow-sm shrink-0">
              <div className="flex items-center gap-2">
                {/* Replaced by AI Active badge in header, but keeping this for spacing/legacy if needed, or remove it */}
              </div>
              <div className="flex items-center gap-4 ml-auto">
                {conversationId && (
                  <span className="text-xs font-mono text-on-surface-variant/50 hidden sm:inline-block border border-outline-variant/20 px-2 py-0.5 rounded">
                    Conv: {conversationId.slice(0, 8)}...
                  </span>
                )}
                <button onClick={resetConversation} className="flex items-center gap-1.5 text-xs font-semibold text-primary hover:text-primary/80 transition-colors">
                  <PlusCircle size={14} /> New Conversation
                </button>
              </div>
            </div>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 md:p-6 flex flex-col gap-6 scroll-smooth bg-surface-container-highest/20">
              {history.length === 0 && !loading && !error && (
                <div className="m-auto text-center flex flex-col items-center">
                  <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4 border border-primary/20">
                    <MessageCircleQuestion size={32} className="text-primary" />
                  </div>
                  <h3 className="text-lg font-bold text-on-surface mb-2">How can I help you?</h3>
                  <p className="text-on-surface-variant text-sm mb-4">Ask a question about Patient <strong className="text-on-surface">{activePatientId}</strong>.</p>
                  <div className="flex flex-col gap-2 w-full max-w-sm">
                    <button onClick={() => setQuestion("What are the patient's active medications?")} className="px-4 py-2 bg-surface-container hover:bg-surface-variant rounded-lg border border-outline-variant/20 text-sm font-medium text-left transition-colors">
                      "What are the patient's active medications?"
                    </button>
                    <button onClick={() => setQuestion("What were the latest lab results?")} className="px-4 py-2 bg-surface-container hover:bg-surface-variant rounded-lg border border-outline-variant/20 text-sm font-medium text-left transition-colors">
                      "What were the latest lab results?"
                    </button>
                  </div>
                </div>
              )}

              {history.map((msg, i) => {
                const isUser = msg.role === 'user';
                const hasSources = msg.sources && msg.sources.length > 0;
                // Treat as fallback if assistant has 0 sources (ungrounded)
                const isFallback = !isUser && !hasSources;

                return (
                  <div key={i} className={`flex flex-col max-w-[90%] sm:max-w-[85%] ${isUser ? 'self-end' : 'self-start'} group animate-fade-in-up`}>
                    
                    {/* Bubble */}
                    <div className={`p-4 md:p-5 rounded-2xl shadow-sm text-sm md:text-base leading-relaxed break-words ${
                      isUser 
                        ? 'bg-primary text-on-primary rounded-tr-sm' 
                        : isFallback 
                          ? 'bg-amber-500/10 border border-amber-500/30 text-amber-500 rounded-tl-sm' 
                          : 'bg-surface-container-high border border-outline-variant/30 text-on-surface rounded-tl-sm'
                    }`}>
                      {isFallback && (
                        <div className="flex items-center gap-2 mb-2 font-bold uppercase tracking-wider text-[10px] text-amber-500/80">
                          <AlertTriangle size={12} /> No Grounded Sources Found
                        </div>
                      )}
                      <div className="markdown-content">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {msg.text}
                        </ReactMarkdown>
                      </div>
                    </div>
                    
                    {/* Inline Citation Chips */}
                    {!isUser && hasSources && (
                      <div className="flex flex-wrap gap-2 mt-2 pl-1">
                        {Array.from(new Set(msg.sources.map(s => typeof s === 'string' ? s : s.document_id))).map((docId, idx) => (
                          <a
                            key={`${docId}-${idx}`}
                            href={getDocumentFileUrl(docId)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-surface-variant/50 hover:bg-primary/10 border border-outline-variant/30 hover:border-primary/30 rounded-full text-[11px] font-bold text-on-surface-variant hover:text-primary transition-colors no-underline"
                            title={`View source document (ID: ${docId})`}
                          >
                            <FileText size={12} />
                            Source {idx + 1}
                          </a>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}

              {loading && (
                <div className="self-start max-w-[85%] bg-surface-container-high border border-outline-variant/30 rounded-2xl rounded-tl-sm p-5 shadow-sm animate-fade-in-up">
                  <div className="flex items-center gap-3 text-primary">
                    <RefreshCw size={18} className="animate-spin" />
                    <span className="text-sm font-semibold">Analyzing clinical records...</span>
                  </div>
                </div>
              )}
              
              {error && (
                <div className={`self-center max-w-[85%] w-full p-4 rounded-xl border flex items-start gap-3 mt-4 ${errorType === 'server_error' ? 'bg-error-container/20 border-error/30 text-error' : 'bg-amber-500/10 border-amber-500/30 text-amber-500'}`}>
                  {errorType === 'server_error' ? <AlertTriangle size={18} className="shrink-0 mt-0.5" /> : <Info size={18} className="shrink-0 mt-0.5" />}
                  <span className="font-medium text-sm">{error}</span>
                </div>
              )}

              <div ref={chatEndRef} className="h-4" />
            </div>

            {/* Disclaimer & Input Area */}
            <div className="bg-surface-container-high border-t border-outline-variant/10 shrink-0 relative z-10 p-4">
              <div className="text-[10px] sm:text-xs text-center text-on-surface-variant/60 font-medium mb-3 uppercase tracking-wider flex items-center justify-center gap-2">
                <AlertTriangle size={12} className="opacity-70" /> 
                AI generated responses should be verified against primary sources.
              </div>
              
              <form onSubmit={handleAskQuestion} className="flex gap-3 relative max-w-4xl mx-auto">
                <input
                  type="text"
                  placeholder={`Ask a question about Patient ${activePatientId}...`}
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  disabled={loading}
                  className="flex-1 bg-surface-container-highest/60 border border-outline-variant/40 rounded-xl px-5 py-3.5 text-sm md:text-base text-on-surface focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all disabled:opacity-60 shadow-inner"
                />
                <button
                  type="submit"
                  disabled={!question.trim() || loading}
                  className="btn btn-primary px-6 rounded-xl flex items-center justify-center transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md hover:shadow-lg active:scale-95 bg-gradient-to-r from-primary to-secondary"
                >
                  <Send size={18} className="text-white" />
                </button>
              </form>
            </div>
          </div>

          {/* ── Right Pane: Context Browser ── */}
          <div className="w-full lg:w-[400px] xl:w-[450px] shrink-0 flex flex-col bg-surface-container rounded-2xl border border-outline-variant/20 overflow-hidden shadow-sm min-h-[400px]">
            <div className="flex justify-between items-center px-5 py-4 bg-surface-container-high border-b border-outline-variant/10 shadow-sm shrink-0">
              <h3 className="text-title-sm font-title-sm text-on-surface flex items-center gap-2">
                <FileSearch className="text-secondary" size={18} /> Context Browser
              </h3>
            </div>

            <div className="flex-1 overflow-y-auto p-4 bg-surface-container-highest/10 flex flex-col gap-4">
              {groupedContexts.length === 0 ? (
                <div className="m-auto text-center flex flex-col items-center justify-center h-full opacity-60">
                  <FileSearch size={32} className="text-on-surface-variant mb-3" />
                  <p className="text-sm font-semibold text-on-surface">No context available</p>
                  <p className="text-xs text-on-surface-variant mt-1 max-w-[200px]">Sources for the AI's response will appear here.</p>
                </div>
              ) : (
                groupedContexts.map((group, idx) => {
                  const docId = group.docId;
                  const fileUrl = getDocumentFileUrl(docId);

                  return (
                    <div key={docId} className="bg-surface-container-high border border-outline-variant/30 rounded-xl shadow-sm overflow-hidden flex flex-col animate-fade-in-up" style={{ animationDelay: `${idx * 100}ms` }}>
                      <div className="flex justify-between items-center px-3 py-2 bg-surface-variant/40 border-b border-outline-variant/20">
                        <div className="flex items-center gap-2">
                          <FileText size={14} className="text-on-surface-variant" />
                          <span className="text-xs font-bold text-on-surface truncate max-w-[200px]" title={docId}>
                            Document {docId.slice(0, 8)}
                          </span>
                        </div>
                        {fileUrl && (
                          <a href={fileUrl} target="_blank" rel="noopener noreferrer" className="text-primary hover:text-primary/80 transition-colors" title="View Source">
                            <ExternalLink size={14} />
                          </a>
                        )}
                      </div>
                      
                      <div className="p-3 flex flex-col gap-3">
                        {group.snippets.map((ctx, sIdx) => {
                          const parsed = parseSnippetData(ctx.snippet);
                          return (
                            <div key={sIdx} className="text-sm text-on-surface/90">
                              {parsed.type === 'labs' ? (
                                <table className="w-full text-xs">
                                  <tbody>
                                    {parsed.data.map((lab, lIdx) => (
                                      <tr key={lIdx} className="border-b border-outline-variant/10 last:border-0">
                                        <td className="py-1.5 pr-2 font-medium">{lab.name}</td>
                                        <td className={`py-1.5 text-right whitespace-nowrap ${lab.flag && lab.flag.toLowerCase() !== 'normal' ? 'text-amber-400 font-bold bg-amber-400/10 px-1 rounded' : ''}`}>
                                          {lab.value} {lab.unit}
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              ) : (
                                <p className="italic font-serif leading-relaxed text-[13px] opacity-90 break-words border-l-2 border-primary/30 pl-2">
                                  "{parsed.text}"
                                </p>
                              )}
                              {ctx.location && (
                                <div className="mt-2 text-[10px] text-on-surface-variant flex items-center gap-1 font-mono">
                                  <span className="w-1 h-1 rounded-full bg-secondary/50"></span>
                                  Loc: {ctx.location}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

        </div>
      )}
    </div>
  );
}
