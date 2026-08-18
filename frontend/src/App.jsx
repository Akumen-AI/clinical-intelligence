import React, { useState } from 'react';
import UploadPage from './pages/UploadPage';
import ReviewQueuePage from './pages/ReviewQueuePage';
import CanonicalRecordPage from './pages/CanonicalRecordPage';
import TimelinePage from './pages/TimelinePage';
import PolicyChatbot from './components/PolicyChatbot';
import PolicyDocumentUploader from './components/PolicyDocumentUploader';
import { Activity, ClipboardCheck, Database, Clock } from 'lucide-react';
import PatientQAPage from './pages/PatientQAPage';
import PatientsPage from './pages/PatientsPage';
import { Activity, ClipboardCheck, Database, Clock, MessageCircleQuestion, Users } from 'lucide-react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Unhandled React Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--bg-main, #0b0f19)',
          color: 'var(--text-main, #f8fafc)',
          padding: '2rem',
          textAlign: 'center',
          fontFamily: 'Inter, sans-serif'
        }}>
          <h2 style={{ fontSize: '1.5rem', marginBottom: '0.75rem', color: '#f43f5e' }}>Something went wrong rendering the UI</h2>
          <p style={{ color: '#94a3b8', maxWidth: '500px', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
            {this.state.error?.message || 'An unexpected rendering error occurred.'}
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
            style={{
              background: '#06b6d4',
              color: '#0b0f19',
              border: 'none',
              borderRadius: '8px',
              padding: '0.6rem 1.25rem',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            Reload Page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

function App() {
  const [activePage, setActivePage] = useState('intake'); // 'intake' | 'review' | 'canonical' | 'timeline'

  return (
    <ErrorBoundary>
      <div className="App">
        <PolicyDocumentUploader />
        {/* Global navigation bar */}
        <nav className="global-nav">
          <div className="global-nav-inner">
            <div className="global-nav-brand">
              <Activity size={18} color="var(--primary-cyan)" />
              <span>Clinical Intelligence Platform</span>
            </div>
            <div className="global-nav-tabs">
              <button
                id="nav-intake-tab"
                className={`global-nav-tab ${activePage === 'intake' ? 'active' : ''}`}
                onClick={() => setActivePage('intake')}
              >
                <Activity size={15} />
                Document Intake
              </button>
              <button
                id="nav-review-tab"
                className={`global-nav-tab ${activePage === 'review' ? 'active' : ''}`}
                onClick={() => setActivePage('review')}
              >
                <ClipboardCheck size={15} />
                Review Queue
              </button>
              <button
                id="nav-canonical-tab"
                className={`global-nav-tab ${activePage === 'canonical' ? 'active' : ''}`}
                onClick={() => setActivePage('canonical')}
              >
                <Database size={15} />
                Canonical Records
              </button>
              <button
                id="nav-timeline-tab"
                className={`global-nav-tab ${activePage === 'timeline' ? 'active' : ''}`}
                onClick={() => setActivePage('timeline')}
              >
                <Clock size={15} />
                Patient Timeline
              </button>
              <button
                id="nav-ask-tab"
                className={`global-nav-tab ${activePage === 'ask' ? 'active' : ''}`}
                onClick={() => setActivePage('ask')}
              >
                <MessageCircleQuestion size={15} />
                Patient Q&A
              </button>
              <button
                id="nav-patients-tab"
                className={`global-nav-tab ${activePage === 'patients' ? 'active' : ''}`}
                onClick={() => setActivePage('patients')}
              >
                <Users size={15} />
                Patients
              </button>
            </div>
          </div>
        </nav>

        {activePage === 'intake' && <UploadPage />}
        {activePage === 'review' && <ReviewQueuePage />}
        {activePage === 'canonical' && <CanonicalRecordPage />}
        {activePage === 'timeline' && <TimelinePage />}
        <PolicyChatbot />
        {activePage === 'ask' && <PatientQAPage />}
        {activePage === 'patients' && <PatientsPage />}
      </div>
    </ErrorBoundary>
  );
}

export default App;
