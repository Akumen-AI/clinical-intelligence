import React, { useEffect, useRef, useState } from 'react';
import { Bot, ChevronDown, Loader2, MessageCircle, Send, X } from 'lucide-react';
import apiClient from '../services/api';

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
  const [isOpen, setIsOpen] = useState(false);
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([
    { id: 'welcome', role: 'assistant', content: 'Ask me about hospital policies and SOPs.' },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

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

  return (
    <div className="policy-chatbot">
      {isOpen && (
        <section className="policy-chat-panel" aria-label="Hospital policy chatbot">
          <header className="policy-chat-header">
            <div className="policy-chat-heading">
              <span className="policy-chat-avatar"><Bot size={17} /></span>
              <div>
                <strong>Policy assistant</strong>
                <span>Hospital policies &amp; SOPs</span>
              </div>
            </div>
            <button
              type="button"
              className="policy-chat-close"
              aria-label="Close policy chatbot"
              onClick={() => setIsOpen(false)}
            >
              <X size={18} />
            </button>
          </header>

          <div className="policy-chat-messages" aria-live="polite">
            {messages.map((message) => {
              const isUngrounded = message.role === 'assistant'
                && message.content.toLowerCase().includes(NO_GROUNDED_ANSWER);
              return (
                <div key={message.id} className={`policy-chat-message ${message.role}`}>
                  <div className={`policy-chat-bubble ${isUngrounded ? 'ungrounded' : ''}`}>
                    {message.content}
                  </div>
                  {message.citations?.length > 0 && (
                    <div className="policy-chat-citations">
                      <span className="policy-chat-citations-label">Sources</span>
                      {message.citations.map((citation, index) => (
                        <div className="policy-chat-citation" key={`${citationDocumentId(citation)}-${index}`}>
                          <a
                            href={citationSourceUrl(citation)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="policy-chat-source-link"
                          >
                            {citationDocumentId(citation)}
                          </a>
                          <em>{citationSection(citation)}</em>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
            {isLoading && (
              <div className="policy-chat-message assistant">
                <div className="policy-chat-bubble policy-chat-loading">
                  <Loader2 size={15} className="policy-chat-spinner" />
                  Searching policy index…
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {error && <div className="policy-chat-error" role="alert">{error}</div>}

          <form className="policy-chat-composer" onSubmit={submitQuestion}>
            <input
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask a policy question…"
              aria-label="Policy question"
              disabled={isLoading}
            />
            <button type="submit" aria-label="Send policy question" disabled={!question.trim() || isLoading}>
              <Send size={16} />
            </button>
          </form>
        </section>
      )}

      <button
        type="button"
        className={`policy-chat-fab ${isOpen ? 'open' : ''}`}
        aria-label={isOpen ? 'Close policy chatbot' : 'Open policy chatbot'}
        aria-expanded={isOpen}
        onClick={() => setIsOpen((open) => !open)}
      >
        {isOpen ? <ChevronDown size={24} /> : <MessageCircle size={24} />}
      </button>
    </div>
  );
}
