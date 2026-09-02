import React, { useEffect, useMemo, useState } from 'react';
import { BarChart, Bar, PieChart, Pie, Cell, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { Activity, CalendarRange, Building2, Stethoscope } from 'lucide-react';
import apiClient from '../services/api-client';

const COLORS = ['#22c55e', '#38bdf8', '#f59e0b', '#a78bfa', '#f472b6', '#fb7185'];

const numberFormatter = (value) => {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: 1 });
};

const ChartCard = ({ title, value, unit, chart, available, note }) => {
  return (
    <div style={{ background: 'rgba(15,23,42,0.7)', border: '1px solid rgba(148, 163, 184, 0.2)', borderRadius: '16px', padding: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
        <div style={{ color: '#cbd5e1', fontSize: '0.85rem', fontWeight: 600 }}>{title}</div>
        {available === false && <span style={{ color: '#fbbf24', fontSize: '0.7rem' }}>Unavailable</span>}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.35rem', marginBottom: '0.75rem' }}>
        <span style={{ color: '#f8fafc', fontSize: '1.8rem', fontWeight: 700 }}>{numberFormatter(value)}</span>
        {unit && <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>{unit}</span>}
      </div>
      {!available ? (
        <div style={{ color: '#fbbf24', fontSize: '0.8rem', lineHeight: 1.5 }}>{note}</div>
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
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chart}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey={chart[0]?.date ? 'date' : 'label'} stroke="#94a3b8" fontSize={10} />
                <YAxis stroke="#94a3b8" fontSize={10} />
                <Tooltip />
                <Bar dataKey={chart[0]?.date ? 'value' : 'value'} fill="#38bdf8" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      ) : (
        <div style={{ color: '#64748b', fontSize: '0.8rem' }}>No data for the current filters.</div>
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

  const summary = useMemo(() => {
    const map = Object.fromEntries(metrics.map((metric) => [metric.key, metric]));
    return {
      admissions: map.admissions?.value ?? 0,
      diseaseDistribution: map.disease_distribution?.chart ?? [],
      readmissionRate: map.readmission_rate?.value ?? 0,
    };
  }, [metrics]);

  return (
    <div className="app-container">
      <header className="app-header" style={{ marginBottom: '1.5rem' }}>
        <div className="brand-wrapper">
          <div className="brand-logo" style={{ background: 'linear-gradient(135deg, #0ea5e9, #22c55e)' }}>
            <Activity size={26} color="#fff" />
          </div>
          <div className="brand-title">
            <h1>Operations Dashboard</h1>
            <p>Live admissions, disease, and readmission metrics</p>
          </div>
        </div>
      </header>

      <div className="glass-card" style={{ padding: '1rem 1.25rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', color: '#cbd5e1', fontSize: '0.8rem' }}>
            Department
            <select value={department} onChange={(e) => setDepartment(e.target.value)} style={{ minWidth: '180px', borderRadius: '10px', padding: '0.6rem 0.8rem', background: '#0f172a', color: '#e2e8f0', border: '1px solid #334155' }}>
              <option value="">All departments</option>
              <option value="Cardiology">Cardiology</option>
              <option value="Neurology">Neurology</option>
              <option value="Emergency">Emergency</option>
              <option value="Orthopedics">Orthopedics</option>
            </select>
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', color: '#cbd5e1', fontSize: '0.8rem' }}>
            Start date
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} style={{ borderRadius: '10px', padding: '0.6rem 0.8rem', paddingRight: '2rem', background: '#0f172a', color: '#e2e8f0', border: '1px solid #334155', colorScheme: 'dark', width: '100%' }} />
            </div>
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', color: '#cbd5e1', fontSize: '0.8rem' }}>
            End date
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} style={{ borderRadius: '10px', padding: '0.6rem 0.8rem', paddingRight: '2rem', background: '#0f172a', color: '#e2e8f0', border: '1px solid #334155', colorScheme: 'dark', width: '100%' }} />
            </div>
          </label>
        </div>
      </div>

      {error && <div style={{ background: 'rgba(127,29,29,0.4)', color: '#fecaca', border: '1px solid rgba(248,113,113,0.4)', padding: '0.8rem 1rem', borderRadius: '12px', marginBottom: '1rem' }}>{error}</div>}

      {loading ? (
        <div style={{ color: '#cbd5e1', padding: '2rem' }}>Loading metrics…</div>
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1rem' }}>
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

          <div className="glass-card" style={{ marginTop: '1.5rem', padding: '1rem 1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.75rem', color: '#e2e8f0', fontWeight: 700 }}>
              <Building2 size={18} />
              Summary snapshot
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '1rem' }}>
              <div style={{ background: 'rgba(15,23,42,0.6)', padding: '0.8rem', borderRadius: '12px' }}>
                <div style={{ color: '#94a3b8', fontSize: '0.75rem' }}>Admissions</div>
                <div style={{ color: '#f8fafc', fontSize: '1.4rem', fontWeight: 700 }}>{summary.admissions}</div>
              </div>
              <div style={{ background: 'rgba(15,23,42,0.6)', padding: '0.8rem', borderRadius: '12px' }}>
                <div style={{ color: '#94a3b8', fontSize: '0.75rem' }}>Disease top category</div>
                <div style={{ color: '#f8fafc', fontSize: '1.4rem', fontWeight: 700 }}>{summary.diseaseDistribution[0]?.name || '—'}</div>
              </div>
              <div style={{ background: 'rgba(15,23,42,0.6)', padding: '0.8rem', borderRadius: '12px' }}>
                <div style={{ color: '#94a3b8', fontSize: '0.75rem' }}>Readmission rate</div>
                <div style={{ color: '#f8fafc', fontSize: '1.4rem', fontWeight: 700 }}>{summary.readmissionRate.toFixed(1)}%</div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
