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
    <div className="min-h-screen flex items-center justify-center bg-paper font-sans px-4">
      <div className="w-full max-w-md bg-surface border border-line rounded-xl p-8 shadow-[var(--shadow-float)]">
        <div className="flex flex-col items-center justify-center mb-8">
          <div className="w-14 h-14 bg-teal rounded-2xl flex items-center justify-center text-white mb-6">
            <Activity size={32} />
          </div>
          <div className="text-2xl tracking-tight mb-2">
            <span className="text-ink font-medium">Clinical</span>
            <span className="text-teal font-bold">Intelligence</span>
          </div>
          <p className="text-slate text-sm text-center">
            Sign in to access your secure workspace
          </p>
        </div>

        {error && (
          <div className="bg-danger/10 text-danger border border-danger/20 p-3 rounded-md mb-6 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-slate text-sm font-medium mb-1.5">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-3 py-2 rounded-md border border-line bg-surface text-ink focus:outline-none focus:border-teal focus:ring-1 focus:ring-teal"
            />
          </div>
          <div>
            <label className="block text-slate text-sm font-medium mb-1.5">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-3 py-2 rounded-md border border-line bg-surface text-ink focus:outline-none focus:border-teal focus:ring-1 focus:ring-teal"
            />
          </div>
          <button
            type="submit"
            disabled={isLoading}
            className="mt-4 w-full py-2.5 rounded-md bg-teal text-white font-medium hover:bg-teal/90 disabled:opacity-70 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default LoginPage;
