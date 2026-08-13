import React, { useState, useEffect } from 'react';
import { X, Search, UserPlus } from 'lucide-react';
import apiClient from '../services/api';

export default function LinkPatientModal({ isOpen, onClose, onLink, documentId, suggestedMrn = '' }) {
  const [tab, setTab] = useState('search');
  const [searchQuery, setSearchQuery] = useState(suggestedMrn);
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);

  // Create form state
  const [formData, setFormData] = useState({
    mrn: suggestedMrn,
    name: '',
    dob: '',
    sex: ''
  });

  useEffect(() => {
    if (isOpen && tab === 'search' && searchQuery) {
      handleSearch();
    }
  }, [isOpen, tab]);

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
    <div className="modal-backdrop">
      <div className="modal-content" style={{ width: '450px' }}>
        <div className="modal-header">
          <h3>Link to Patient</h3>
          <button className="icon-btn" onClick={onClose}><X size={18} /></button>
        </div>
        
        <div className="modal-tabs">
          <button 
            className={`tab-btn ${tab === 'search' ? 'active' : ''}`}
            onClick={() => setTab('search')}
          >
            <Search size={14} /> Search Existing
          </button>
          <button 
            className={`tab-btn ${tab === 'create' ? 'active' : ''}`}
            onClick={() => setTab('create')}
          >
            <UserPlus size={14} /> Create New
          </button>
        </div>

        <div className="modal-body">
          {tab === 'search' ? (
            <div>
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
                <input 
                  type="text" 
                  className="input-field" 
                  style={{ flex: 1 }}
                  placeholder="Search MRN or Name..." 
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                />
                <button className="btn btn-primary" onClick={handleSearch} disabled={isSearching}>
                  Search
                </button>
              </div>
              <div className="search-results">
                {isSearching ? <p>Searching...</p> : searchResults.length === 0 ? (
                  <p style={{ color: 'var(--text-dim)' }}>No patients found.</p>
                ) : (
                  searchResults.map(p => (
                    <div key={p.patient_id} className="patient-card" style={{ padding: '0.75rem', border: '1px solid var(--border-color)', borderRadius: '6px', marginBottom: '0.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <strong>{p.name}</strong> <span style={{ color: 'var(--text-dim)', fontSize: '0.85em' }}>({p.mrn})</span>
                        <div style={{ fontSize: '0.85em', color: 'var(--text-dim)' }}>DOB: {p.dob || 'N/A'}</div>
                      </div>
                      <button className="btn btn-secondary" onClick={() => onLink({ patient_id: p.patient_id })}>
                        Link
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          ) : (
            <form onSubmit={handleCreateAndLink}>
              <div className="form-group" style={{ marginBottom: '1rem' }}>
                <label>MRN *</label>
                <input type="text" className="input-field" required value={formData.mrn} onChange={e => setFormData({...formData, mrn: e.target.value})} />
              </div>
              <div className="form-group" style={{ marginBottom: '1rem' }}>
                <label>Full Name *</label>
                <input type="text" className="input-field" required value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} />
              </div>
              <div className="form-group" style={{ marginBottom: '1rem' }}>
                <label>Date of Birth</label>
                <input type="date" className="input-field" value={formData.dob} onChange={e => setFormData({...formData, dob: e.target.value})} />
              </div>
              <div className="form-group" style={{ marginBottom: '1rem' }}>
                <label>Sex</label>
                <select className="input-field" value={formData.sex} onChange={e => setFormData({...formData, sex: e.target.value})}>
                  <option value="">Select...</option>
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                  <option value="Other">Other</option>
                </select>
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1.5rem' }}>
                <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
                <button type="submit" className="btn btn-primary">Create & Link</button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
