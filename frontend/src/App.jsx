import React, { useState } from 'react';
import UploadPage from './pages/UploadPage';
import ReviewQueuePage from './pages/ReviewQueuePage';
import { Activity, ClipboardCheck } from 'lucide-react';

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
  const [activePage, setActivePage] = useState('intake'); // 'intake' | 'review'

  return (
    <ErrorBoundary>
      <div className="App">
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
            </div>
          </div>
        </nav>

        {activePage === 'intake' ? <UploadPage /> : <ReviewQueuePage />}
      </div>
    </ErrorBoundary>
  );
}

export default App;
