import React, { useEffect, useMemo, useState } from 'react';
import { BarChart, Bar, PieChart, Pie, Cell, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { Activity, Building2, Download } from 'lucide-react';
import apiClient from '../api';

// Using the token palette: teal, success, slate, warning, danger
const COLORS = ['#0B6E6E', '#1E7B4D', '#5A6472', '#B9770E', '#B3261E'];

const numberFormatter = (value) => {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: 1 });
};

const ChartCard = ({ title, value, unit, chart, available, note }) => {
  return (
    <div className="bg-surface border border-line rounded-2xl p-5 shadow-sm">
      <div className="flex justify-between items-center mb-3">
        <div className="text-slate text-sm font-bold">{title}</div>
        {available === false && <span className="text-warning text-xs font-bold bg-warning/10 px-2 py-0.5 rounded-full border border-warning/20">Unavailable</span>}
      </div>
      <div className="flex items-baseline gap-1.5 mb-3">
        <span className="text-ink text-3xl font-bold">{numberFormatter(value)}</span>
        {unit && <span className="text-slate text-sm font-semibold">{unit}</span>}
      </div>
      {!available ? (
        <div className="text-warning text-sm leading-relaxed">{note}</div>
      ) : chart && chart.length ? (
        <div style={{ height: 170 }}>
          {chart.some((entry) => entry.name) ? (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={chart} dataKey="count" nameKey="name" innerRadius={30} outerRadius={60} paddingAngle={2}>
                  {chart.map((entry, index) => (
                    <Cell key={`${entry.name}-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-line)', borderRadius: '8px' }}
                  itemStyle={{ color: 'var(--color-ink)', fontWeight: 'bold' }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chart}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E1E5EA" vertical={false} />
                <XAxis dataKey={chart[0]?.date ? 'date' : 'label'} stroke="#5A6472" fontSize={10} tickLine={false} axisLine={false} tickMargin={8} />
                <YAxis stroke="#5A6472" fontSize={10} tickLine={false} axisLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-line)', borderRadius: '8px' }}
                  cursor={{ fill: '#F6F7F9' }}
                />
                <Bar dataKey={chart[0]?.date ? 'value' : 'value'} fill="#0B6E6E" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      ) : (
        <div className="text-slate text-sm">No data for the current filters.</div>
      )}
    </div>
  );
};

const defaultRangeDays = () => {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - 30);
  return {
    start_date: start.toISOString().slice(0, 10),
    end_date: end.toISOString().slice(0, 10),
  };
};

export default function OperationsDashboardPage() {
  const [department, setDepartment] = useState('');
  const [startDate, setStartDate] = useState(defaultRangeDays().start_date);
  const [endDate, setEndDate] = useState(defaultRangeDays().end_date);
  const [metrics, setMetrics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [exportingFormat, setExportingFormat] = useState('');

  const fetchDashboard = async () => {
    setLoading(true);
    setError('');
    try {
      const params = { start_date: startDate, end_date: endDate };
      if (department) params.department = department;
      const endpoint = department ? '/dashboards/department' : '/dashboards/hospital';
      const response = await apiClient.get(endpoint, { params });
      setMetrics(response.data.metrics || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to load dashboard metrics.');
      setMetrics([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, [department, startDate, endDate]);

  const exportDashboard = async (format) => {
    setExportingFormat(format);
    setError('');
    try {
      const response = await apiClient.get('/dashboards/hospital/export', {
        params: { format, department: department || undefined, start_date: startDate, end_date: endDate },
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = `operations-dashboard.${format}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError('Unable to export dashboard.');
    } finally {
      setExportingFormat('');
    }
  };

  const summary = useMemo(() => {
    const map = Object.fromEntries(metrics.map((metric) => [metric.key, metric]));
    return {
      admissions: map.admissions?.value ?? 0,
      diseaseDistribution: map.disease_distribution?.chart ?? [],
      readmissionRate: map.readmission_rate?.value ?? 0,
    };
  }, [metrics]);

  return (
    <div className="app-container flex flex-col gap-6">
      <header className="flex justify-between items-center pb-4 border-b border-line">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-teal/10 flex items-center justify-center text-teal border border-teal/20">
            <Activity size={26} />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-ink">Operations Dashboard</h1>
            <p className="text-sm text-slate">Live admissions, disease, and readmission metrics</p>
          </div>
        </div>
      </header>

      <div className="bg-surface border border-line rounded-2xl p-5 shadow-sm">
        <div className="flex flex-wrap items-end gap-4">
          <label className="flex flex-col gap-1.5 text-slate text-sm font-bold">
            Department
            <select 
              value={department} 
              onChange={(e) => setDepartment(e.target.value)} 
              className="min-w-[180px] rounded-lg px-4 py-2 bg-surface text-ink border border-line focus:outline-none focus:border-teal font-normal"
            >
              <option value="">All departments</option>
              <option value="Cardiology">Cardiology</option>
              <option value="Neurology">Neurology</option>
              <option value="Emergency">Emergency</option>
              <option value="Orthopedics">Orthopedics</option>
            </select>
          </label>
          <label className="flex flex-col gap-1.5 text-slate text-sm font-bold">
            Start date
            <input 
              type="date" 
              value={startDate} 
              onChange={(e) => setStartDate(e.target.value)} 
              className="rounded-lg px-4 py-2 bg-surface text-ink border border-line focus:outline-none focus:border-teal font-normal"
            />
          </label>
          <label className="flex flex-col gap-1.5 text-slate text-sm font-bold">
            End date
            <input 
              type="date" 
              value={endDate} 
              onChange={(e) => setEndDate(e.target.value)} 
              className="rounded-lg px-4 py-2 bg-surface text-ink border border-line focus:outline-none focus:border-teal font-normal"
            />
          </label>
          <div className="flex gap-2 ml-auto flex-wrap">
            {['pdf', 'csv', 'xlsx'].map((format) => (
              <button
                key={format}
                type="button"
                onClick={() => exportDashboard(format)}
                disabled={Boolean(exportingFormat)}
                title={`Export ${format.toUpperCase()}`}
                className="flex items-center gap-1.5 px-4 py-2 border border-teal/20 rounded-lg bg-teal/10 text-teal font-semibold hover:bg-teal/20 transition-colors disabled:opacity-50"
              >
                <Download size={15} />
                {exportingFormat === format ? 'Exporting…' : `Export ${format.toUpperCase()}`}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-danger/10 text-danger border border-danger/20 p-4 rounded-xl font-medium">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-slate p-8 text-center text-lg font-medium flex flex-col items-center gap-4">
          <Activity size={32} className="animate-pulse text-teal" />
          Loading metrics…
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {metrics.map((metric) => (
              <ChartCard
                key={metric.key}
                title={metric.label}
                value={metric.value}
                unit={metric.unit}
                chart={metric.chart || []}
                available={metric.available}
                note={metric.note}
              />
            ))}
          </div>

          <div className="bg-surface border border-line rounded-2xl p-6 shadow-sm">
            <div className="flex items-center gap-2 mb-4 text-ink font-bold text-lg">
              <Building2 size={20} className="text-teal" />
              Summary snapshot
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-paper border border-line p-4 rounded-xl">
                <div className="text-slate text-xs font-bold uppercase tracking-wider mb-1">Admissions</div>
                <div className="text-ink text-2xl font-bold">{summary.admissions}</div>
              </div>
              <div className="bg-paper border border-line p-4 rounded-xl">
                <div className="text-slate text-xs font-bold uppercase tracking-wider mb-1">Disease top category</div>
                <div className="text-ink text-2xl font-bold">{summary.diseaseDistribution[0]?.name || '—'}</div>
              </div>
              <div className="bg-paper border border-line p-4 rounded-xl">
                <div className="text-slate text-xs font-bold uppercase tracking-wider mb-1">Readmission rate</div>
                <div className="text-ink text-2xl font-bold">{summary.readmissionRate.toFixed(1)}%</div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
