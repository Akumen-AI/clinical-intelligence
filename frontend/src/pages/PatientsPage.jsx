import React, { useState, useEffect } from 'react';
import { Users, Copy, CheckCircle2, User, AlertCircle, RefreshCw, MessageCircleQuestion, Search } from 'lucide-react';
import { fetchPatients } from '../api';
import { useNavigate } from 'react-router-dom';

export default function PatientsPage() {
  const [patients, setPatients] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copiedId, setCopiedId] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadPatients();
  }, []);

  const loadPatients = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchPatients();
      setPatients(data);
    } catch (err) {
      console.error('Failed to load patients:', err);
      setError('Failed to fetch patient records from the server.');
    } finally {
      setLoading(false);
    }
  };

  const handleCopyId = (e, id) => {
    e.stopPropagation();
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const filteredPatients = patients.filter(p => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    const name = (p.name || '').toLowerCase();
    const mrn = (p.mrn || '').toLowerCase();
    const patientNumber = (p.patient_number || '').toLowerCase();
    return name.includes(query) || mrn.includes(query) || patientNumber.includes(query);
  });

  return (
    <div className="app-container">
      {/* Header Section */}
      <header className="flex justify-between items-center mb-8 pb-6 border-b border-line">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-teal flex items-center justify-center text-white">
            <Users size={26} color="#ffffff" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-ink mb-1">Patient Directory</h1>
            <p className="text-sm text-slate">Browse and manage synthetic patient records</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate" />
            <input 
              type="text" 
              placeholder="Search by name or ID..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 pr-4 py-2 rounded-lg border border-line bg-surface text-ink text-sm w-64 focus:outline-none focus:border-teal"
            />
          </div>
          <button 
            onClick={loadPatients} 
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface border border-line text-ink hover:bg-paper transition-colors text-sm font-semibold disabled:opacity-50" 
            disabled={loading}
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </header>

      {/* Error state */}
      {error && (
        <div className="flex items-center gap-2 px-4 py-3 bg-danger/10 border border-danger/20 rounded-lg text-danger text-sm font-medium mb-6">
          <AlertCircle size={18} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Main Content Area */}
      {loading ? (
        <div className="bg-surface border border-line rounded-xl text-center py-16 text-slate">
          <RefreshCw size={32} className="animate-spin mx-auto mb-4 text-teal" />
          <p className="text-lg font-medium">Loading patient records...</p>
        </div>
      ) : patients.length === 0 ? (
        <div className="bg-surface border border-line rounded-xl text-center py-20">
          <Users size={48} className="mx-auto mb-4 text-slate opacity-50" />
          <h3 className="text-xl font-semibold mb-2 text-ink">
            No patients found
          </h3>
          <p className="text-sm text-slate max-w-md mx-auto">
            No synthetic patients have been seeded into the database yet.
          </p>
        </div>
      ) : (
        <div className="bg-surface border border-line rounded-xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm whitespace-nowrap">
              <thead className="bg-paper sticky top-0 z-10 border-b border-line">
                <tr>
                  <th className="p-4 text-xs font-bold text-slate uppercase tracking-wider">Patient Name</th>
                  <th className="p-4 text-xs font-bold text-slate uppercase tracking-wider">Patient ID / MRN</th>
                  <th className="p-4 text-xs font-bold text-slate uppercase tracking-wider">DOB</th>
                  <th className="p-4 text-xs font-bold text-slate uppercase tracking-wider">Sex</th>
                  <th className="p-4 text-xs font-bold text-slate uppercase tracking-wider text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredPatients.length === 0 ? (
                  <tr>
                    <td colSpan="5" className="p-8 text-center text-slate">No patients match your search.</td>
                  </tr>
                ) : filteredPatients.map(patient => (
                  <tr 
                    key={patient.patient_id}
                    className="border-b border-line hover:bg-paper transition-colors cursor-pointer group"
                    onClick={() => navigate(`/patients/${patient.patient_id}/dashboard`)}
                  >
                    <td className="p-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-teal/10 flex items-center justify-center text-teal">
                          <User size={16} />
                        </div>
                        <span className="font-semibold text-ink text-base group-hover:text-teal transition-colors">{patient.name}</span>
                      </div>
                    </td>
                    <td className="p-4 font-mono text-slate">{patient.patient_number || patient.mrn}</td>
                    <td className="p-4 text-ink">{patient.dob || 'Unknown'}</td>
                    <td className="p-4 text-ink capitalize">{patient.sex || 'Unknown'}</td>
                    <td className="p-4 text-right">
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/patients/${patient.patient_id}/ask`);
                          }}
                          className="px-2.5 py-1.5 bg-surface border border-line text-slate hover:text-teal hover:bg-teal/10 rounded-md transition-colors flex items-center gap-1.5 text-xs font-semibold"
                        >
                          <MessageCircleQuestion size={14} /> Q&A
                        </button>
                        <button
                          onClick={(e) => handleCopyId(e, patient.patient_number || patient.mrn)}
                          className={`px-2.5 py-1.5 border rounded-md transition-colors flex items-center gap-1.5 text-xs font-semibold ${
                            copiedId === (patient.patient_number || patient.mrn)
                              ? 'bg-success/10 text-success border-success/20'
                              : 'bg-surface border-line text-slate hover:text-ink hover:bg-line/50'
                          }`}
                        >
                          {copiedId === (patient.patient_number || patient.mrn) ? <CheckCircle2 size={14} /> : <Copy size={14} />}
                          {copiedId === (patient.patient_number || patient.mrn) ? 'Copied' : 'Copy'}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
