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
        className="w-full bg-surface border border-line rounded-lg p-3 text-ink text-sm focus:outline-none focus:border-teal focus:ring-1 focus:ring-teal resize-none"
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
      <div className="flex flex-col gap-2" onKeyDown={handleKeyDown}>
        {data.map((item, i) => (
          <div key={i} className="p-3 bg-paper border border-line rounded-md relative mb-2">
            <button 
              className="absolute top-2 right-2 p-1 text-slate hover:text-danger rounded transition-colors"
              onClick={() => handleRemoveItem(i)}
              title="Remove item"
            >
              <Trash2 size={14} />
            </button>
            {isArrayOfStrings ? (
              <input 
                type="text" 
                className="w-[calc(100%-24px)] px-3 py-1.5 bg-surface border border-line rounded-md text-ink text-sm focus:outline-none focus:border-teal" 
                value={item} 
                onChange={e => handleItemChange(i, null, e.target.value)} 
              />
            ) : (
              <div className="grid grid-cols-2 gap-2 mt-1 w-[calc(100%-20px)]">
                {Object.keys(item).map(key => (
                  <div key={key}>
                    <label className="text-xs text-slate capitalize block mb-1">{key.replace(/_/g, ' ')}</label>
                    <input 
                      type="text" 
                      className="w-full px-2 py-1.5 bg-surface border border-line rounded-md text-ink text-sm focus:outline-none focus:border-teal" 
                      value={item[key] === null ? '' : item[key]} 
                      onChange={e => handleItemChange(i, key, e.target.value)} 
                    />
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        {data.length === 0 && <p className="text-sm text-slate mb-2">No items.</p>}
        <button className="flex items-center justify-center gap-1.5 w-full py-2 bg-paper hover:bg-line/50 text-ink text-sm font-semibold rounded-md border border-line transition-colors" onClick={handleAddItem}>
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
      <div className="flex flex-col" onKeyDown={handleKeyDown}>
        <div className="grid grid-cols-2 gap-3 p-3 bg-paper border border-line rounded-md">
          {Object.keys(data).map(key => (
            <div key={key} className="relative">
              <label className="flex justify-between items-center text-xs text-slate capitalize mb-1">
                {key.replace(/_/g, ' ')}
                <Trash2 size={12} className="cursor-pointer text-danger hover:opacity-80" onClick={() => handleRemoveField(key)} title="Remove field" />
              </label>
              <input 
                type="text" 
                className="w-full px-2 py-1.5 bg-surface border border-line rounded-md text-ink text-sm focus:outline-none focus:border-teal" 
                value={data[key] === null ? '' : data[key]} 
                onChange={e => handleFieldChange(key, e.target.value)} 
              />
            </div>
          ))}
          {Object.keys(data).length === 0 && <div className="col-span-2 text-sm text-slate">No fields.</div>}
        </div>
        <button className="flex items-center justify-center gap-1.5 w-full py-2 mt-3 bg-paper hover:bg-line/50 text-ink text-sm font-semibold rounded-md border border-line transition-colors" onClick={handleAddField}>
          <Plus size={14} /> Add Field
        </button>
      </div>
    );
  }

  return null;
}
