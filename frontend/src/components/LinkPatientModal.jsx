import React, { useState, useEffect } from 'react';
import { X, Search, UserPlus, Link2 } from 'lucide-react';
import apiClient from '../api';

export default function LinkPatientModal({ isOpen, onClose, onLink, documentId, suggestedPatientData = {} }) {
  const generateMRN = () => {
    const d = new Date();
    const dateStr = d.toISOString().split('T')[0].replace(/-/g, '');
    const rand = Math.floor(1000 + Math.random() * 9000);
    return `MRN-${dateStr}-${rand}`;
  };

  const [tab, setTab] = useState('search');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);

  // Create form state
  const [formData, setFormData] = useState({
    mrn: '',
    name: '',
    dob: '',
    sex: ''
  });

  useEffect(() => {
    if (isOpen) {
      setSearchQuery(suggestedPatientData.mrn || suggestedPatientData.name || '');
      setFormData({
        mrn: generateMRN(),
        name: suggestedPatientData.name || '',
        dob: suggestedPatientData.dob || '',
        sex: suggestedPatientData.sex || ''
      });
    }
  }, [isOpen, suggestedPatientData]);

  useEffect(() => {
    if (isOpen && tab === 'search' && searchQuery) {
      handleSearch();
    }
  }, [isOpen, tab]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleSearch = async () => {
    if (!searchQuery) return;
    setIsSearching(true);
    try {
      const res = await apiClient.get('/patients', { params: { search: searchQuery } });
      setSearchResults(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsSearching(false);
    }
  };

  const handleCreateAndLink = async (e) => {
    e.preventDefault();
    onLink({
      create_new: true,
      mrn: formData.mrn,
      name: formData.name,
      dob: formData.dob,
      sex: formData.sex
    });
  };

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-ink/80 z-50 p-4 sm:p-6" onClick={onClose}>
      <div className="bg-surface border border-line rounded-xl shadow-[var(--shadow-float)] overflow-hidden w-full max-w-lg flex flex-col" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="flex justify-between items-center p-5 border-b border-line bg-paper">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-teal/10 border border-teal/20 flex items-center justify-center">
              <Link2 size={20} className="text-teal" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-ink">Link to Patient</h2>
              <p className="text-xs text-slate mt-0.5">Connect this document to a patient record</p>
            </div>
          </div>
          <button className="p-1.5 rounded-lg text-slate hover:text-danger hover:bg-danger/10 transition-colors" onClick={onClose} title="Close">
            <X size={20} />
          </button>
        </div>
        
        {/* Modal Navigation Tabs */}
        <div className="flex gap-2 p-3 bg-paper border-b border-line">
          <button 
            className={`flex items-center justify-center flex-1 gap-2 px-3 py-2 rounded-lg text-sm font-bold border transition-colors ${tab === 'search' ? 'text-teal bg-teal/10 border-teal/20' : 'text-slate hover:text-ink hover:bg-surface border-transparent'}`}
            onClick={() => setTab('search')}
          >
            <Search size={16} /> Search Existing
          </button>
          <button 
            className={`flex items-center justify-center flex-1 gap-2 px-3 py-2 rounded-lg text-sm font-bold border transition-colors ${tab === 'create' ? 'text-teal bg-teal/10 border-teal/20' : 'text-slate hover:text-ink hover:bg-surface border-transparent'}`}
            onClick={() => setTab('create')}
          >
            <UserPlus size={16} /> Create New
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 flex-1 overflow-y-auto">
          {tab === 'search' ? (
            <div className="flex flex-col h-full gap-4">
              <div className="flex gap-2">
                <input 
                  type="text" 
                  className="flex-1 bg-paper border border-line rounded-lg px-4 py-2 text-ink text-sm focus:outline-none focus:border-teal focus:ring-1 focus:ring-teal transition-all"
                  placeholder="Search by MRN or Name..." 
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                />
                <button 
                  className="bg-surface border border-line text-ink font-bold px-4 py-2 rounded-lg text-sm hover:bg-paper transition-colors disabled:opacity-50" 
                  onClick={handleSearch} 
                  disabled={isSearching}
                >
                  Search
                </button>
              </div>
              <div className="flex-1 overflow-y-auto min-h-[200px] border border-line rounded-lg bg-paper p-1">
                {isSearching ? (
                  <div className="p-4 text-center text-slate text-sm font-medium">Searching...</div>
                ) : searchResults.length === 0 ? (
                  <div className="p-8 flex flex-col items-center justify-center text-slate h-full">
                    <Search size={24} className="mb-2 opacity-50" />
                    <p className="text-sm font-medium">No patients found.</p>
                  </div>
                ) : (
                  <div className="flex flex-col gap-1">
                    {searchResults.map(p => (
                      <div key={p.patient_id} className="p-3 bg-surface border border-line rounded-md flex justify-between items-center shadow-sm hover:border-teal/50 transition-colors">
                        <div className="flex flex-col">
                          <div className="text-sm font-bold text-ink">
                            {p.name} <span className="text-slate font-mono font-normal ml-1 text-xs">({p.mrn})</span>
                          </div>
                          <div className="text-xs text-slate mt-1 font-medium">DOB: {p.dob || 'N/A'}</div>
                        </div>
                        <button 
                          className="bg-teal text-white font-bold px-3 py-1.5 rounded-md text-xs hover:bg-teal/90 transition-colors shadow-sm" 
                          onClick={() => onLink({ patient_id: p.patient_id })}
                        >
                          Link
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <form onSubmit={handleCreateAndLink} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-slate uppercase tracking-wider">MRN *</label>
                <input 
                  type="text" 
                  className="bg-paper border border-line rounded-lg px-4 py-2.5 text-ink text-sm focus:outline-none focus:border-teal focus:ring-1 focus:ring-teal font-mono" 
                  required 
                  value={formData.mrn} 
                  onChange={e => setFormData({...formData, mrn: e.target.value})} 
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-slate uppercase tracking-wider">Full Name *</label>
                <input 
                  type="text" 
                  className="bg-paper border border-line rounded-lg px-4 py-2.5 text-ink text-sm focus:outline-none focus:border-teal focus:ring-1 focus:ring-teal" 
                  required 
                  value={formData.name} 
                  onChange={e => setFormData({...formData, name: e.target.value})} 
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-bold text-slate uppercase tracking-wider">Date of Birth</label>
                  <input 
                    type="date" 
                    className="bg-paper border border-line rounded-lg px-4 py-2.5 text-ink text-sm focus:outline-none focus:border-teal focus:ring-1 focus:ring-teal" 
                    value={formData.dob} 
                    onChange={e => setFormData({...formData, dob: e.target.value})} 
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-bold text-slate uppercase tracking-wider">Sex</label>
                  <select 
                    className="bg-paper border border-line rounded-lg px-4 py-2.5 text-ink text-sm focus:outline-none focus:border-teal focus:ring-1 focus:ring-teal appearance-none" 
                    value={formData.sex} 
                    onChange={e => setFormData({...formData, sex: e.target.value})}
                  >
                    <option value="">Select...</option>
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
              </div>
              <div className="flex justify-end gap-3 mt-4 pt-4 border-t border-line">
                <button type="button" className="px-5 py-2 rounded-lg font-bold text-sm text-slate bg-surface border border-line hover:bg-paper transition-colors" onClick={onClose}>
                  Cancel
                </button>
                <button type="submit" className="px-5 py-2 rounded-lg font-bold text-sm text-white bg-teal hover:shadow-md hover:-translate-y-[1px] transition-all">
                  Create & Link
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
