import React, { useEffect, useRef, useState } from 'react';
import { 
  Bot, 
  Send, 
  RefreshCw, 
  AlertTriangle, 
  FileText, 
  ExternalLink,
  ShieldCheck,
  Building2,
  Info
} from 'lucide-react';
import apiClient from '../services/api';
import PolicyDocumentUploader from './PolicyDocumentUploader';
import { useAuth } from '../contexts/AuthContext';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
const NO_GROUNDED_ANSWER = 'no grounded answer found';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

function getCitations(response) {
  if (!Array.isArray(response?.citations)) return [];
  return response.citations;
}

function citationDocumentId(citation) {
  return citation?.document_id || citation?.source_document_id || citation?.document || 'Policy document';
}

function citationSection(citation) {
  return citation?.section_heading || citation?.section || citation?.heading || 'Policy section';
}

function citationSourceUrl(citation) {
  const sourceUrl = citation?.source_url;
  if (!sourceUrl) return '#';
  if (sourceUrl.startsWith('http')) return sourceUrl;
  if (API_BASE_URL.startsWith('http')) return `${new URL(API_BASE_URL).origin}${sourceUrl}`;
  return sourceUrl;
}

export default function PolicyChatbot() {
  const { user } = useAuth();
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([
    { 
      id: 'welcome', 
      role: 'assistant', 
      content: 'Welcome to the Hospital Policy Assistant. I am an AI trained on our verified internal guidelines, SOPs, and compliance frameworks. How can I help you today?' 
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading, error]);

  const submitQuestion = async (event) => {
    event?.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || isLoading) return;

    setMessages((current) => [
      ...current,
      { id: `user-${Date.now()}`, role: 'user', content: trimmedQuestion },
    ]);
    setQuestion('');
    setError('');
    setIsLoading(true);

    try {
      const response = await apiClient.post('/policy-chat', { question: trimmedQuestion });
      setMessages((current) => [
        ...current,
        {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: response.data?.answer || 'No answer was returned by the policy service.',
          citations: getCitations(response.data),
        },
      ]);
    } catch (requestError) {
      const detail = requestError.response?.data?.detail;
      setError(detail || 'The policy chatbot could not be reached. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const allowedUploadRoles = ['hospital_admin', 'it', 'compliance'];
  const canUpload = user && user.role && allowedUploadRoles.includes(user.role.toLowerCase());

  const allowedChatRoles = ['doctor', 'nurse', 'hospital_admin'];
  const canChat = user && user.role && allowedChatRoles.includes(user.role.toLowerCase());

  return (
    <div className="app-container flex-1 flex flex-col min-h-0">
      
      {/* Header Section */}
      <header className="app-header">
        <div className="brand-wrapper">
          <div className="brand-logo" style={{ background: 'linear-gradient(135deg, var(--accent-emerald), var(--primary-cyan))' }}>
            <Building2 size={26} color="#ffffff" />
          </div>
          <div className="brand-title">
            <h1>Hospital Policy Assistant</h1>
            <p>Ask questions about hospital guidelines, standard operating procedures, and compliance rules.</p>
          </div>
        </div>
        
        {/* Upload Controls for Admins */}
        {canUpload && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div className="bg-surface-container-high px-4 py-2 rounded-xl border border-outline-variant/20 flex items-center gap-4 shadow-sm">
              <div className="flex items-center gap-2">
                <ShieldCheck className="text-emerald-500" size={18} />
                <span className="text-sm font-semibold text-on-surface">Policy Management</span>
              </div>
              <PolicyDocumentUploader />
            </div>
          </div>
        )}
      </header>

      {/* Main Container */}
      {canChat && (
      <div className="flex-1 flex flex-col bg-surface-container rounded-2xl border border-outline-variant/20 overflow-hidden relative shadow-sm min-h-[500px]">
        
        {/* Chat Toolbar */}
        <div className="flex justify-between items-center px-4 py-3 bg-surface-container-high border-b border-outline-variant/10 shadow-sm shrink-0">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="text-sm font-bold text-on-surface">Secure RAG Knowledge Base</span>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 flex flex-col gap-6 scroll-smooth bg-surface-container-highest/20">
          {messages.map((message) => {
            const isUser = message.role === 'user';
            const isUngrounded = !isUser && message.content.toLowerCase().includes(NO_GROUNDED_ANSWER);
            
            return (
              <div key={message.id} className={`flex flex-col max-w-[90%] sm:max-w-[85%] ${isUser ? 'self-end' : 'self-start'} group animate-fade-in-up`}>
                
                {/* Bubble */}
                <div className={`p-4 md:p-5 rounded-2xl shadow-sm text-sm md:text-base leading-relaxed break-words ${
                  isUser 
                    ? 'bg-primary text-on-primary rounded-tr-sm' 
                    : isUngrounded 
                      ? 'bg-amber-500/10 border border-amber-500/30 text-amber-500 rounded-tl-sm' 
                      : 'bg-surface-container-high border border-outline-variant/30 text-on-surface rounded-tl-sm'
                }`}>
                  {!isUser && !isUngrounded && (
                    <div className="flex items-center gap-2 mb-2 font-bold uppercase tracking-wider text-[10px] text-primary/80">
                      <Bot size={12} /> Policy Assistant
                    </div>
                  )}
                  {isUngrounded && (
                    <div className="flex items-center gap-2 mb-2 font-bold uppercase tracking-wider text-[10px] text-amber-500/80">
                      <AlertTriangle size={12} /> No Grounded Sources Found
                    </div>
                  )}
                  <div className="markdown-content">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {message.content}
                    </ReactMarkdown>
                  </div>
                </div>
                
                {/* Inline Citations */}
                {!isUser && message.citations?.length > 0 && (
                  <div className="flex flex-col gap-2 mt-3 pl-1">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant/70">Sources used for this answer:</span>
                    <div className="flex flex-wrap gap-2">
                      {message.citations.map((citation, index) => (
                        <a
                          key={`${citationDocumentId(citation)}-${index}`}
                          href={citationSourceUrl(citation)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-2 px-3 py-1.5 bg-surface-variant/50 hover:bg-primary/10 border border-outline-variant/30 hover:border-primary/30 rounded-lg text-xs font-semibold text-on-surface hover:text-primary transition-colors no-underline shadow-sm"
                          title={`Section: ${citationSection(citation)}`}
                        >
                          <FileText size={14} className="opacity-70" />
                          <div className="flex flex-col max-w-[200px]">
                            <span className="truncate">{citationDocumentId(citation)}</span>
                            <span className="text-[9px] font-medium opacity-70 truncate">{citationSection(citation)}</span>
                          </div>
                          <ExternalLink size={12} className="ml-1 opacity-50" />
                        </a>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          {isLoading && (
            <div className="self-start max-w-[85%] bg-surface-container-high border border-outline-variant/30 rounded-2xl rounded-tl-sm p-5 shadow-sm animate-fade-in-up">
              <div className="flex items-center gap-3 text-primary">
                <RefreshCw size={18} className="animate-spin" />
                <span className="text-sm font-semibold">Searching internal policies...</span>
              </div>
            </div>
          )}
          
          {error && (
            <div className="self-center max-w-[85%] w-full p-4 rounded-xl border flex items-start gap-3 mt-4 bg-error-container/20 border-error/30 text-error">
              <AlertTriangle size={18} className="shrink-0 mt-0.5" />
              <span className="font-medium text-sm">{error}</span>
            </div>
          )}

          <div ref={messagesEndRef} className="h-4" />
        </div>

        {/* Disclaimer & Input Area */}
        <div className="bg-surface-container-high border-t border-outline-variant/10 shrink-0 relative z-10 p-4">
          <div className="text-[10px] sm:text-xs text-center text-on-surface-variant/60 font-medium mb-3 uppercase tracking-wider flex items-center justify-center gap-2">
            <Info size={12} className="opacity-70" /> 
            AI generated responses should be verified against official primary sources.
          </div>
          
          <form onSubmit={submitQuestion} className="flex gap-3 relative max-w-4xl mx-auto">
            <input
              type="text"
              placeholder="Ask a policy question..."
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              disabled={isLoading}
              className="flex-1 bg-surface-container-highest/60 border border-outline-variant/40 rounded-xl px-5 py-3.5 text-sm md:text-base text-on-surface focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all disabled:opacity-60 shadow-inner"
            />
            <button
              type="submit"
              disabled={!question.trim() || isLoading}
              className="btn btn-primary px-6 rounded-xl flex items-center justify-center transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md hover:shadow-lg active:scale-95 bg-gradient-to-r from-primary to-secondary"
            >
              <Send size={18} className="text-white" />
            </button>
          </form>
        </div>
      </div>
      )}
      
    </div>
  );
}
