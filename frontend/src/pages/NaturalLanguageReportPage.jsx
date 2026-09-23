import React, { useState } from 'react';
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { BarChart2, Search, RotateCcw, Loader2, AlertTriangle, Filter } from 'lucide-react';
import apiClient from '../api';

const COLORS = ['#22c55e', '#38bdf8', '#f59e0b', '#a78bfa', '#f472b6', '#fb7185'];

export default function NaturalLanguageReportPage() {
  const [request, setRequest] = useState('');
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [lastRequest, setLastRequest] = useState('');

  const generate = async (event, queryStr) => {
    if (event) event.preventDefault();
    const query = queryStr || request;
    if (!query.trim()) return;
    setLoading(true); setError(''); setReport(null);
    setLastRequest(query);
    try {
      const response = await apiClient.post('/reports/generate', { nl_query: query });
      setReport(response.data);
    } catch (err) {
      setReport(null);
      setError(err.response?.data?.detail || 'Unable to generate the report. Please try again.');
    } finally { setLoading(false); }
  };

  const renderChart = () => {
    if (!report) return null;
    const data = report.data || [];
    if (!data.length) return <div className="text-on-surface-variant p-8 text-center bg-surface-container rounded-lg border border-outline-variant/20 mt-4">No matching canonical records found for the given criteria.</div>;
    
    if (report.chart_type === 'pie') return <div className="mt-4"><ResponsiveContainer width="100%" height={350}><PieChart><Pie data={data} dataKey="count" nameKey="label" outerRadius={120} label>{data.map((entry, i) => <Cell key={`${entry.label}-${i}`} fill={COLORS[i % COLORS.length]} />)}</Pie><Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} /></PieChart></ResponsiveContainer></div>;
    
    if (report.chart_type === 'line') return <div className="mt-4"><ResponsiveContainer width="100%" height={350}><LineChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}><CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} /><XAxis dataKey="label" stroke="#94a3b8" tick={{ fill: '#94a3b8' }} /><YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8' }} /><Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} /><Line type="monotone" dataKey="count" stroke="#38bdf8" strokeWidth={3} dot={{ r: 4, fill: '#38bdf8' }} /></LineChart></ResponsiveContainer></div>;
    
    return <div className="mt-4"><ResponsiveContainer width="100%" height={350}><BarChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}><CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} /><XAxis dataKey="label" stroke="#94a3b8" tick={{ fill: '#94a3b8' }} /><YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8' }} /><Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} /><Bar dataKey="count" fill="#38bdf8" radius={[4, 4, 0, 0]}><Cell fill="#38bdf8" /></Bar></BarChart></ResponsiveContainer></div>;
  };

  const renderQueryPlan = () => {
    if (!report?.query_plan) return null;
    const plan = report.query_plan;
    
    return (
      <div className="flex flex-col gap-3 mt-4">
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="bg-surface-container-high p-3 rounded-lg border border-outline-variant/30">
            <span className="text-on-surface-variant text-xs font-bold uppercase tracking-wider block mb-1">Cohort Scope</span>
            <span className="text-on-surface font-medium">{plan.cohort || 'All Patients'}</span>
          </div>
          <div className="bg-surface-container-high p-3 rounded-lg border border-outline-variant/30">
            <span className="text-on-surface-variant text-xs font-bold uppercase tracking-wider block mb-1">Metric</span>
            <span className="text-on-surface font-medium capitalize">{plan.metric || 'Count'}</span>
          </div>
          <div className="bg-surface-container-high p-3 rounded-lg border border-outline-variant/30">
            <span className="text-on-surface-variant text-xs font-bold uppercase tracking-wider block mb-1">Date Range</span>
            <span className="text-on-surface font-medium">{plan.date_range || 'All Time'}</span>
          </div>
          <div className="bg-surface-container-high p-3 rounded-lg border border-outline-variant/30">
            <span className="text-on-surface-variant text-xs font-bold uppercase tracking-wider block mb-1">Grouping</span>
            <span className="text-on-surface font-medium capitalize">{plan.grouping || 'None'}</span>
          </div>
        </div>
        
        {plan.filters && Object.keys(plan.filters).length > 0 && (
          <div className="bg-surface-container-high p-3 rounded-lg border border-outline-variant/30">
            <span className="text-on-surface-variant text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 mb-2">
              <Filter size={14} /> Explicit Filters
            </span>
            <div className="flex flex-wrap gap-2">
              {Object.entries(plan.filters).map(([k, v]) => (
                <span key={k} className="px-2 py-1 bg-primary/10 border border-primary/20 text-primary rounded-md text-xs font-medium">
                  {k}: {v}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="app-container flex flex-col min-h-0">
      <header className="app-header shrink-0">
        <div className="brand-wrapper">
          <div className="brand-logo" style={{ background: 'linear-gradient(135deg, var(--accent-emerald), var(--primary-cyan))' }}>
            <BarChart2 size={26} color="#ffffff" />
          </div>
          <div className="brand-title">
            <h1>Natural-Language Reports</h1>
            <p>Generate clinical analytics using plain text queries</p>
          </div>
        </div>
      </header>

      <form onSubmit={(e) => generate(e, request)} className="bg-surface-container rounded-xl border border-outline-variant/30 p-4 mb-6 flex gap-3 shadow-sm shrink-0">
        <input 
          aria-label="Report request" 
          value={request} 
          onChange={(e) => setRequest(e.target.value)} 
          placeholder="e.g. show me the distribution of diagnoses for diabetic patients" 
          className="flex-1 bg-surface-container-high border border-outline-variant/40 rounded-lg px-4 py-3 text-on-surface focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary shadow-inner"
          disabled={loading}
        />
        <button 
          type="submit" 
          disabled={loading || !request.trim()} 
          className="px-6 py-3 bg-gradient-to-r from-primary to-secondary text-white rounded-lg font-bold flex items-center justify-center gap-2 hover:opacity-90 disabled:opacity-50 transition-opacity"
        >
          {loading ? <Loader2 size={18} className="animate-spin" /> : <Search size={18} />}
          {loading ? 'Analyzing...' : 'Generate'}
        </button>
      </form>

      <div className="flex-1 overflow-y-auto">
        {loading && (
          <div className="flex flex-col items-center justify-center py-20 bg-surface-container/50 rounded-xl border border-outline-variant/10">
            <Loader2 size={40} className="animate-spin text-primary mb-4" />
            <h3 className="text-lg font-semibold text-on-surface">Generating Report...</h3>
            <p className="text-sm text-on-surface-variant">Translating query, applying RBAC scopes, and fetching canonical records.</p>
          </div>
        )}

        {error && !loading && (
          <div className="p-5 rounded-xl bg-error-container/20 border border-error/30 text-error flex flex-col sm:flex-row justify-between items-center gap-4">
            <div className="flex items-center gap-3">
              <AlertTriangle size={24} className="shrink-0" />
              <span className="font-medium">{error}</span>
            </div>
            <button 
              onClick={() => generate(null, lastRequest)} 
              className="px-4 py-2 bg-error/10 hover:bg-error/20 border border-error/30 text-error rounded-lg font-semibold flex items-center gap-2 transition-colors whitespace-nowrap"
            >
              <RotateCcw size={16} /> Retry Query
            </button>
          </div>
        )}

        {report && !loading && (
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 animate-fade-in-up">
            <div className="xl:col-span-2 flex flex-col gap-6">
              <section className="bg-surface-container rounded-xl border border-outline-variant/20 p-6 shadow-sm">
                <h2 className="text-title-md font-title-md text-on-surface mb-2">Report Visualization</h2>
                <div className="text-sm text-on-surface-variant mb-4">
                  Rendered as <span className="font-semibold text-on-surface">{report.chart_type} chart</span>
                </div>
                {renderChart()}
              </section>
            </div>
            
            <div className="flex flex-col gap-6">
              <section className="bg-surface-container rounded-xl border border-outline-variant/20 p-6 shadow-sm h-full flex flex-col">
                <h2 className="text-title-md font-title-md text-on-surface mb-2">Execution Plan</h2>
                <p className="text-sm text-on-surface-variant mb-4">
                  The LLM generated the following structured execution plan which was safely executed against the backend data access layer.
                </p>
                {renderQueryPlan()}
                
                <details className="mt-auto pt-6 text-on-surface-variant/70 text-xs">
                  <summary className="cursor-pointer hover:text-on-surface-variant transition-colors font-medium">View Raw JSON Plan</summary>
                  <pre className="mt-3 p-3 bg-surface-container-highest rounded border border-outline-variant/20 overflow-x-auto text-[10px] text-on-surface-variant leading-relaxed">
                    {JSON.stringify(report.query_plan || report.resolved_filters, null, 2)}
                  </pre>
                </details>
              </section>
            </div>
          </div>
        )}

        {!report && !loading && !error && (
          <div className="flex flex-col items-center justify-center py-24 text-center opacity-60">
            <BarChart2 size={64} className="text-on-surface-variant mb-6" />
            <h2 className="text-xl font-bold text-on-surface mb-2">Awaiting Query</h2>
            <p className="text-on-surface-variant max-w-md mx-auto">
              Use natural language to ask questions about your hospital's canonical data.
              Security scopes are automatically applied based on your role.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
