import React, { useState } from 'react';
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { BarChart2, Search } from 'lucide-react';
import apiClient from '../api';

const COLORS = ['#0B6E6E', '#1E7B4D', '#5A6472', '#B9770E', '#B3261E'];

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
    if (!data.length) return <div className="text-slate p-8 text-center">No matching canonical records.</div>;
    
    if (report.chart_type === 'pie') {
      return (
        <ResponsiveContainer width="100%" height={320}>
          <PieChart>
            <Pie data={data} dataKey="count" nameKey="label" outerRadius={110} label>
              {data.map((entry, i) => <Cell key={`${entry.label}-${i}`} fill={COLORS[i % COLORS.length]} />)}
            </Pie>
            <Tooltip contentStyle={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-line)', borderRadius: '8px' }} />
          </PieChart>
        </ResponsiveContainer>
      );
    }
    
    if (report.chart_type === 'line') {
      return (
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E1E5EA" vertical={false} />
            <XAxis dataKey="label" stroke="#5A6472" tickLine={false} axisLine={false} tickMargin={10} />
            <YAxis stroke="#5A6472" tickLine={false} axisLine={false} />
            <Tooltip contentStyle={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-line)', borderRadius: '8px' }} />
            <Line type="monotone" dataKey="count" stroke="#0B6E6E" strokeWidth={3} activeDot={{ r: 6, fill: "#0B6E6E", stroke: "#FFFFFF", strokeWidth: 2 }} />
          </LineChart>
        </ResponsiveContainer>
      );
    }
    
    return (
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E1E5EA" vertical={false} />
          <XAxis dataKey="label" stroke="#5A6472" tickLine={false} axisLine={false} tickMargin={10} />
          <YAxis stroke="#5A6472" tickLine={false} axisLine={false} />
          <Tooltip cursor={{ fill: '#F6F7F9' }} contentStyle={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-line)', borderRadius: '8px' }} />
          <Bar dataKey="count" fill="#0B6E6E" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    );
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

  return (
    <div className="app-container flex flex-col gap-6">
      <header className="flex justify-between items-center pb-4 border-b border-line">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-teal/10 flex items-center justify-center text-teal border border-teal/20">
            <BarChart2 size={26} />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-ink mb-1">Natural-language reports</h1>
            <p className="text-sm text-slate">Ask for a clinical report in plain language</p>
          </div>
        </div>
      </header>

      <form onSubmit={generate} className="bg-surface border border-line rounded-xl p-4 shadow-sm flex flex-col sm:flex-row gap-3">
        <input 
          aria-label="Report request" 
          value={request} 
          onChange={(e) => setRequest(e.target.value)} 
          placeholder="e.g. generate a report on diabetic patients this quarter" 
          className="flex-1 rounded-lg px-4 py-3 bg-paper border border-line text-ink focus:outline-none focus:border-teal" 
        />
        <button 
          type="submit" 
          disabled={loading} 
          className="flex items-center justify-center gap-2 px-6 py-3 bg-teal text-white font-bold rounded-lg hover:shadow-md hover:-translate-y-[1px] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Search size={16} />
          {loading ? 'Generating…' : 'Generate report'}
        </button>
      </form>

      {error && (
        <div className="bg-danger/10 text-danger border border-danger/20 p-4 rounded-xl font-medium">
          {error}
        </div>
      )}

      {report && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <section className="lg:col-span-2 bg-surface border border-line rounded-2xl p-5 shadow-sm">
            <h2 className="text-lg font-bold text-ink mb-4 border-b border-line pb-2">Report chart</h2>
            {renderChart()}
          </section>
          <section className="lg:col-span-1 bg-surface border border-line rounded-2xl p-5 shadow-sm flex flex-col">
            <h2 className="text-lg font-bold text-ink mb-4 border-b border-line pb-2">Query used</h2>
            <p className="text-sm font-semibold text-ink leading-relaxed mb-4">
              {readableFilters(report.resolved_filters)}
            </p>
            <div className="text-sm text-slate mb-4">
              Chart: <strong className="text-ink font-mono">{report.chart_type}</strong>
            </div>
            <details className="mt-auto pt-4 border-t border-line text-xs text-slate">
              <summary className="cursor-pointer font-bold uppercase tracking-wider hover:text-teal transition-colors">Resolved filter JSON</summary>
              <pre className="mt-2 p-3 bg-paper border border-line rounded-lg overflow-x-auto font-mono text-ink">
                {JSON.stringify(report.resolved_filters, null, 2)}
              </pre>
            </details>
          </section>
        </div>
      )}
    </div>
  );
}
