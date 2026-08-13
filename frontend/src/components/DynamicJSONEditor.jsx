import React, { useState, useEffect } from 'react';
import { Plus, Trash2 } from 'lucide-react';

const SCHEMAS = {
  medications: { medication_name: '', dosage: '', frequency: '', route: '', duration: '', instructions: '' },
  diagnosis: { condition_name: '', icd10_code: '', notes: '' },
  lab_results: { test_name: '', value: '', unit: '', reference_range: '', flag: '' },
  vitals: { blood_pressure: '', heart_rate: '', respiratory_rate: '', temperature: '', spo2: '', weight: '', height: '', bmi: '' },
  patient_identifier: { patient_id: '', name: '', dob: '', gender: '' },
  ordering_physician: { name: '', npi_or_license: '', department: '' }
};

export default function DynamicJSONEditor({ initialValue, fieldName, onChange, onSubmit, onCancel }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    try {
      if (typeof initialValue === 'string') {
        setData(JSON.parse(initialValue));
      } else {
        setData(initialValue);
      }
    } catch (err) {
      setError('Could not parse JSON. Falling back to raw text editor.');
      setData(initialValue);
    }
  }, [initialValue]);

  const handleChange = (newData) => {
    setData(newData);
    try {
      onChange(JSON.stringify(newData));
    } catch (err) {
      onChange(newData);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      // Don't auto-submit on enter if we are in an input field, it's annoying for forms
      // unless it's the textarea fallback
      if (e.target.tagName === 'TEXTAREA') {
        e.preventDefault();
        onSubmit && onSubmit();
      }
    }
    if (e.key === 'Escape') {
      onCancel && onCancel();
    }
  };

  if (error || typeof data === 'string' || data === null) {
    return (
      <textarea
        className="rfc-edit-input"
        value={typeof data === 'string' ? data : JSON.stringify(data) || ''}
        onChange={(e) => {
          setData(e.target.value);
          onChange(e.target.value);
        }}
        onKeyDown={handleKeyDown}
        rows={5}
        placeholder="Enter corrected value…"
      />
    );
  }

  // Handle Array of Objects (or Strings)
  if (Array.isArray(data)) {
    const isArrayOfStrings = data.length > 0 && typeof data[0] === 'string';

    const handleAddItem = () => {
      const newItem = isArrayOfStrings 
        ? '' 
        : (SCHEMAS[fieldName] ? { ...SCHEMAS[fieldName] } : {});
      handleChange([...data, newItem]);
    };

    const handleRemoveItem = (index) => {
      const newData = [...data];
      newData.splice(index, 1);
      handleChange(newData);
    };

    const handleItemChange = (index, key, val) => {
      const newData = [...data];
      if (isArrayOfStrings) {
        newData[index] = val;
      } else {
        newData[index] = { ...newData[index], [key]: val };
      }
      handleChange(newData);
    };

    return (
      <div className="dynamic-editor-array" onKeyDown={handleKeyDown}>
        {data.map((item, i) => (
          <div key={i} style={{ padding: '0.75rem', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-light)', borderRadius: '6px', marginBottom: '0.5rem', position: 'relative' }}>
            <button 
              className="icon-btn" 
              onClick={() => handleRemoveItem(i)}
              title="Remove item"
              style={{ position: 'absolute', top: '0.25rem', right: '0.25rem', color: 'var(--accent-rose)' }}
            >
              <Trash2 size={14} />
            </button>
            {isArrayOfStrings ? (
              <input 
                type="text" 
                className="input-field" 
                value={item} 
                onChange={e => handleItemChange(i, null, e.target.value)} 
                style={{ width: 'calc(100% - 24px)' }}
              />
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginTop: '0.25rem', width: 'calc(100% - 20px)' }}>
                {Object.keys(item).map(key => (
                  <div key={key}>
                    <label style={{ fontSize: '0.75rem', color: 'var(--text-dim)', textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</label>
                    <input 
                      type="text" 
                      className="input-field" 
                      value={item[key] === null ? '' : item[key]} 
                      onChange={e => handleItemChange(i, key, e.target.value)} 
                    />
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        {data.length === 0 && <p style={{ fontSize: '0.85rem', color: 'var(--text-dim)', marginBottom: '0.5rem' }}>No items.</p>}
        <button className="btn btn-secondary" onClick={handleAddItem} style={{ width: '100%', fontSize: '0.85rem' }}>
          <Plus size={14} /> Add Item
        </button>
      </div>
    );
  }

  // Handle Object
  if (typeof data === 'object' && data !== null) {
    const handleFieldChange = (key, val) => {
      handleChange({ ...data, [key]: val });
    };

    const handleAddField = () => {
      const keyName = prompt('Enter new field name (e.g. pulse_rate):');
      if (keyName && !data.hasOwnProperty(keyName)) {
        handleChange({ ...data, [keyName.toLowerCase().replace(/\s+/g, '_')]: '' });
      }
    };

    const handleRemoveField = (key) => {
      const newData = { ...data };
      delete newData[key];
      handleChange(newData);
    };

    return (
      <div className="dynamic-editor-object" onKeyDown={handleKeyDown}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', background: 'rgba(255,255,255,0.03)', padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border-light)' }}>
          {Object.keys(data).map(key => (
            <div key={key} style={{ position: 'relative' }}>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-dim)', textTransform: 'capitalize', display: 'flex', justifyContent: 'space-between' }}>
                {key.replace(/_/g, ' ')}
                <Trash2 size={12} style={{ cursor: 'pointer', color: 'var(--accent-rose)' }} onClick={() => handleRemoveField(key)} title="Remove field" />
              </label>
              <input 
                type="text" 
                className="input-field" 
                value={data[key] === null ? '' : data[key]} 
                onChange={e => handleFieldChange(key, e.target.value)} 
              />
            </div>
          ))}
          {Object.keys(data).length === 0 && <div style={{ gridColumn: 'span 2', fontSize: '0.85rem', color: 'var(--text-dim)' }}>No fields.</div>}
        </div>
        <button className="btn btn-secondary" onClick={handleAddField} style={{ width: '100%', marginTop: '0.75rem', fontSize: '0.85rem' }}>
          <Plus size={14} /> Add Field
        </button>
      </div>
    );
  }

  return null;
}
