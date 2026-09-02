import React, { useState } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';
import LoginPage from './pages/LoginPage';
import UploadPage from './pages/UploadPage';
import ReviewQueuePage from './pages/ReviewQueuePage';

import TimelinePage from './pages/TimelinePage';
import PatientDashboardPage from './pages/PatientDashboardPage';
import PolicyChatbot from './components/PolicyChatbot';
import PolicyDocumentUploader from './components/PolicyDocumentUploader';
import { Activity, ClipboardCheck, Database, Clock, MessageCircleQuestion, Users, LogOut } from 'lucide-react';
import PatientQAPage from './pages/PatientQAPage';
import PatientsPage from './pages/PatientsPage';
import OperationsDashboardPage from './pages/OperationsDashboardPage';

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

import Layout from './components/Layout';
import { RoleProtectedRoute } from './components/RoleProtectedRoute';

const ProtectedRoute = ({ children }) => {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <div style={{ color: 'white', display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: 'var(--bg-main)' }}>Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
};

function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        
        {/* Protected routes wrapped in the Layout with Sidebar */}
        <Route path="/" element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }>
          {/* Default route redirect */}
          <Route index element={<Navigate to="/intake" replace />} />
          
          <Route path="intake" element={
            <RoleProtectedRoute routeKey="intake">
              <UploadPage />
            </RoleProtectedRoute>
          } />
          
          <Route path="review" element={
            <RoleProtectedRoute routeKey="review">
              <ReviewQueuePage />
            </RoleProtectedRoute>
          } />
          
          <Route path="patients" element={
            <RoleProtectedRoute routeKey="patients">
              <PatientsPage />
            </RoleProtectedRoute>
          } />

          <Route path="operations-dashboard" element={
            <RoleProtectedRoute routeKey="dashboards">
              <OperationsDashboardPage />
            </RoleProtectedRoute>
          } />
          
          {/* Patient Details Redirection */}
          <Route path="patients/:patientId" element={<Navigate to="/patients/:patientId/dashboard" replace />} />
          
          <Route path="patients/:patientId/dashboard" element={
            <RoleProtectedRoute routeKey="patientDashboard">
              <PatientDashboardPage />
            </RoleProtectedRoute>
          } />

          <Route path="patients/:patientId/timeline" element={
            <RoleProtectedRoute routeKey="patients">
              <TimelinePage />
            </RoleProtectedRoute>
          } />
          
          <Route path="patients/:patientId/ask" element={
            <RoleProtectedRoute routeKey="patients">
              <PatientQAPage />
            </RoleProtectedRoute>
          } />
          
          <Route path="patients/ask" element={
            <RoleProtectedRoute routeKey="patients">
              <PatientQAPage />
            </RoleProtectedRoute>
          } />
          

          
          <Route path="policy-assistant" element={
            <RoleProtectedRoute routeKey="policyChat">
              <PolicyChatbot />
            </RoleProtectedRoute>
          } />
          

          
          <Route path="*" element={<Navigate to="/patients" replace />} />
        </Route>
      </Routes>
    </ErrorBoundary>
  );
}

export default App;
