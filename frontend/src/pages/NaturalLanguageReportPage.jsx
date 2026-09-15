import React, { useState } from 'react';
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { BarChart2, Search } from 'lucide-react';
import apiClient from '../api';

const COLORS = ['#22c55e', '#38bdf8', '#f59e0b', '#a78bfa', '#f472b6', '#fb7185'];

export default function NaturalLanguageReportPage() {
  const [request, setRequest] = useState('');
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const generate = async (event) => {
    event.preventDefault();
    if (!request.trim()) return;
    setLoading(true); setError('');
    try {
      const response = await apiClient.post('/reports/generate', { nl_query: request });
      setReport(response.data);
    } catch (err) {
      setReport(null);
      setError(err.response?.data?.detail || 'Unable to generate the report.');
    } finally { setLoading(false); }
  };

  const renderChart = () => {
    if (!report) return null;
    const data = report.data || [];
    if (!data.length) return <div style={{ color: '#94a3b8', padding: '2rem 0' }}>No matching canonical records.</div>;
    if (report.chart_type === 'pie') return <ResponsiveContainer width="100%" height={320}><PieChart><Pie data={data} dataKey="count" nameKey="label" outerRadius={110} label>{data.map((entry, i) => <Cell key={`${entry.label}-${i}`} fill={COLORS[i % COLORS.length]} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer>;
    if (report.chart_type === 'line') return <ResponsiveContainer width="100%" height={320}><LineChart data={data}><CartesianGrid strokeDasharray="3 3" stroke="#334155" /><XAxis dataKey="label" stroke="#94a3b8" /><YAxis stroke="#94a3b8" /><Tooltip /><Line type="monotone" dataKey="count" stroke="#38bdf8" strokeWidth={3} /></LineChart></ResponsiveContainer>;
    return <ResponsiveContainer width="100%" height={320}><BarChart data={data}><CartesianGrid strokeDasharray="3 3" stroke="#334155" /><XAxis dataKey="label" stroke="#94a3b8" /><YAxis stroke="#94a3b8" /><Tooltip /><Bar dataKey="count" fill="#38bdf8" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer>;
  };

  const readableFilters = (filters) => {
    const labels = {
      diagnosis_contains: 'Diagnosis contains',
      icd10_code: 'ICD-10 code',
      medication_contains: 'Medication contains',
      rxnorm_code: 'RxNorm code',
      department: 'Department',
      date_from: 'Start date',
      date_to: 'End date',
    };
    return Object.entries(filters || {}).filter(([key]) => labels[key]).map(([key, value]) => `${labels[key]}: ${value}`).join(' · ');
  };

  return <div className="app-container">
    <header className="app-header" style={{ marginBottom: '1.5rem' }}><div className="brand-wrapper"><div className="brand-logo" style={{ background: 'linear-gradient(135deg, #0ea5e9, #8b5cf6)' }}><BarChart2 size={26} color="#fff" /></div><div className="brand-title"><h1>Natural-language reports</h1><p>Ask for a clinical report in plain language</p></div></div></header>
    <form onSubmit={generate} className="glass-card" style={{ padding: '1rem 1.25rem', marginBottom: '1rem', display: 'flex', gap: '0.75rem' }}>
      <input aria-label="Report request" value={request} onChange={(e) => setRequest(e.target.value)} placeholder="e.g. generate a report on diabetic patients this quarter" style={{ flex: 1, borderRadius: '10px', padding: '0.75rem 1rem', background: '#0f172a', color: '#e2e8f0', border: '1px solid #334155' }} />
      <button type="submit" disabled={loading} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', border: 0, borderRadius: '10px', padding: '0.75rem 1rem', background: '#0891b2', color: 'white', cursor: loading ? 'wait' : 'pointer' }}><Search size={16} />{loading ? 'Generating…' : 'Generate report'}</button>
    </form>
    {error && <div style={{ background: 'rgba(127,29,29,0.4)', color: '#fecaca', border: '1px solid rgba(248,113,113,0.4)', padding: '0.8rem 1rem', borderRadius: '12px', marginBottom: '1rem' }}>{error}</div>}
    {report && <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 2fr) minmax(260px, 1fr)', gap: '1rem' }}>
      <section className="glass-card" style={{ padding: '1rem 1.25rem' }}><h2 style={{ color: '#f8fafc', fontSize: '1.05rem', marginBottom: '0.5rem' }}>Report chart</h2>{renderChart()}</section>
      <section className="glass-card" style={{ padding: '1rem 1.25rem' }}><h2 style={{ color: '#f8fafc', fontSize: '1.05rem', marginBottom: '0.75rem' }}>Query used</h2><p style={{ color: '#cbd5e1', fontSize: '0.85rem', lineHeight: 1.6 }}>{readableFilters(report.resolved_filters)}</p><div style={{ color: '#94a3b8', fontSize: '0.8rem', marginTop: '0.75rem' }}>Chart: <strong style={{ color: '#e2e8f0' }}>{report.chart_type}</strong></div><details style={{ marginTop: '0.75rem', color: '#94a3b8', fontSize: '0.75rem' }}><summary>Resolved filter JSON</summary><pre style={{ whiteSpace: 'pre-wrap', color: '#cbd5e1', lineHeight: 1.6 }}>{JSON.stringify(report.resolved_filters, null, 2)}</pre></details></section>
    </div>}
  </div>;
}
