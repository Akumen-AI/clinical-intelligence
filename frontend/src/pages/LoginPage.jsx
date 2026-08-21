import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { Activity } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from?.pathname || "/";

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const response = await axios.post(`${API_BASE_URL}/auth/login`, {
        email,
        password
      });

      const { access_token, refresh_token } = response.data;
      login(access_token, refresh_token);
      navigate(from, { replace: true });
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Login failed. Please check your credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--bg-main, #0b0f19)',
      fontFamily: 'Inter, sans-serif'
    }}>
      <div style={{
        background: 'var(--bg-card, #1e293b)',
        padding: '2.5rem',
        borderRadius: '12px',
        width: '100%',
        maxWidth: '400px',
        boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '2rem' }}>
          <Activity size={24} color="var(--primary-cyan, #06b6d4)" style={{ marginRight: '0.5rem' }} />
          <h2 style={{ color: 'var(--text-main, #f8fafc)', margin: 0 }}>Login</h2>
        </div>
        
        {error && (
          <div style={{
            background: 'rgba(244, 63, 94, 0.1)',
            color: '#f43f5e',
            padding: '0.75rem',
            borderRadius: '6px',
            marginBottom: '1.5rem',
            fontSize: '0.875rem'
          }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label style={{ display: 'block', color: 'var(--text-muted, #94a3b8)', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              style={{
                width: '100%',
                padding: '0.75rem',
                borderRadius: '6px',
                border: '1px solid var(--border-color, #334155)',
                background: 'var(--bg-main, #0b0f19)',
                color: 'var(--text-main, #f8fafc)',
                boxSizing: 'border-box'
              }}
            />
          </div>
          <div>
            <label style={{ display: 'block', color: 'var(--text-muted, #94a3b8)', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={{
                width: '100%',
                padding: '0.75rem',
                borderRadius: '6px',
                border: '1px solid var(--border-color, #334155)',
                background: 'var(--bg-main, #0b0f19)',
                color: 'var(--text-main, #f8fafc)',
                boxSizing: 'border-box'
              }}
            />
          </div>
          <button
            type="submit"
            disabled={isLoading}
            style={{
              marginTop: '1rem',
              width: '100%',
              padding: '0.75rem',
              borderRadius: '6px',
              background: 'var(--primary-cyan, #06b6d4)',
              color: '#0b0f19',
              border: 'none',
              fontWeight: '600',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              opacity: isLoading ? 0.7 : 1
            }}
          >
            {isLoading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default LoginPage;
