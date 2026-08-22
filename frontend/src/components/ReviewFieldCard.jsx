import React, { useState, useEffect, useRef } from 'react';
import {
  CheckCircle2,
  XCircle,
  Edit3,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  FileText,
  Zap,
} from 'lucide-react';
import LinkPatientModal from './LinkPatientModal';
import DynamicJSONEditor from './DynamicJSONEditor';
import apiClient from '../services/api';

const COMPLEX_FIELDS = [
  'vitals', 'diagnosis', 'medications', 'lab_results',
  'patient_identifier', 'ordering_physician', 'symptoms', 'procedures', 'patient_assignment'
];

export default function ReviewFieldCard({
  item,
  index,
  total,
  onAccept,
  onReject,
  onPrev,
  onNext,
  isSubmitting,
}) {
  const [editMode, setEditMode] = useState(false);
  const [editValue, setEditValue] = useState('');
  const [isLinkModalOpen, setIsLinkModalOpen] = useState(false);
  const editRef = useRef(null);

  useEffect(() => {
    setEditMode(false);
    setEditValue(item?.extracted_value ?? '');
  }, [item?.id]);

  useEffect(() => {
    if (editMode && editRef.current) {
      editRef.current.focus();
      editRef.current.select();
    }
  }, [editMode]);

  useEffect(() => {
    const handler = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) return;
      if (isSubmitting) return;

      switch (e.key.toLowerCase()) {
        case 'a':
        case ' ':
          e.preventDefault();
          onAccept(null);
          break;
        case 'r':
          e.preventDefault();
          onReject();
          break;
        case 'e':
          e.preventDefault();
          setEditMode(true);
          break;
        case 'arrowleft':
          e.preventDefault();
          onPrev();
          break;
        case 'arrowright':
          e.preventDefault();
          onNext();
          break;
        default:
          break;
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isSubmitting, onAccept, onReject, onPrev, onNext]);

  if (!item) return null;

  const conf = item.confidence_score;
  const confPct = (conf * 100).toFixed(1);
  
  let confColorClass = 'text-emerald-500';
  let confBgClass = 'bg-emerald-500';
  let confBorderClass = 'border-emerald-500/30';
  let confContainerClass = 'bg-emerald-500/10';
  let confLabel = 'High';

  if (conf < 0.5) {
    confColorClass = 'text-error';
    confBgClass = 'bg-error';
    confBorderClass = 'border-error/30';
    confContainerClass = 'bg-error-container/20';
    confLabel = 'Low';
  } else if (conf < 0.8) {
    confColorClass = 'text-amber-500';
    confBgClass = 'bg-amber-500';
    confBorderClass = 'border-amber-500/30';
    confContainerClass = 'bg-amber-500/10';
    confLabel = 'Medium';
  }

  const progressPct = total > 0 ? ((index + 1) / total) * 100 : 0;

  const handleEditSubmit = () => {
    onAccept(editValue.trim() !== (item.extracted_value ?? '').trim() ? editValue.trim() : null);
    setEditMode(false);
  };

  const handleLinkPatient = async (payload) => {
    if (payload.create_new) {
      try {
        const res = await apiClient.post('/patients', {
          mrn: payload.mrn,
          name: payload.name,
          dob: payload.dob,
          sex: payload.sex
        });
        onAccept(res.data.patient_id);
      } catch (err) {
        alert(err.response?.data?.detail || 'Failed to create patient');
      }
    } else {
      onAccept(payload.patient_id);
    }
  };

  const isPatientAssignment = item.field_name === 'patient_assignment';
  let parsedAssignment = null;
  if (isPatientAssignment && item.extracted_value) {
    try { parsedAssignment = JSON.parse(item.extracted_value); } catch(e) {}
  }

  return (
    <div className="flex flex-col h-full bg-surface-container rounded-2xl border border-outline-variant/20 overflow-hidden">
      
      {/* Top Banner: Document Ref */}
      <div className="flex justify-between items-center px-4 py-2 bg-surface-container-high border-b border-outline-variant/10">
        <div className="flex items-center gap-2">
          <FileText size={14} className="text-on-surface-variant" />
          <span className="text-sm font-semibold text-on-surface truncate max-w-[200px]">{item.document_filename || item.document_id}</span>
        </div>
        <span className="px-2 py-0.5 rounded text-[10px] font-bold text-on-surface-variant bg-surface-variant uppercase border border-outline-variant/20">
          {item.document_filetype || 'DOC'}
        </span>
      </div>

      <div className="p-5 flex-grow flex flex-col">
        {/* Progress Header */}
        <div className="flex justify-between items-end mb-2">
          <div className="text-sm font-semibold text-on-surface">Field {index + 1} of {total}</div>
          <div className="text-xs text-on-surface-variant">{total - index - 1} remaining</div>
        </div>
        
        {/* Progress Bar */}
        <div className="h-1.5 w-full bg-outline-variant/20 rounded-full overflow-hidden mb-6">
          <div className="h-full bg-primary transition-all duration-300" style={{ width: `${progressPct}%` }}></div>
        </div>

        {/* Field Name & Confidence */}
        <div className="flex justify-between items-start mb-4">
          <h2 className="text-title-lg font-title-lg text-on-surface">{item.field_name}</h2>
          
          <div className={`flex items-center gap-2 px-2.5 py-1 rounded-full border ${confBorderClass} ${confContainerClass}`}>
            <span className={`w-2 h-2 rounded-full ${confBgClass}`}></span>
            <span className={`text-xs font-bold ${confColorClass}`}>{confPct}%</span>
            <span className={`text-[10px] font-semibold ${confColorClass} uppercase opacity-80`}>{confLabel}</span>
          </div>
        </div>

        {/* Confidence Bar underneath */}
        <div className="h-1 w-full bg-outline-variant/10 rounded-full overflow-hidden mb-6">
          <div className={`h-full ${confBgClass}`} style={{ width: `${confPct}%` }}></div>
        </div>

        {/* Value Section */}
        <div className="flex-grow flex flex-col mb-6">
          <label className="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-2">
            {editMode ? 'Corrected Value' : (isPatientAssignment ? 'Extracted Patient Info' : 'Extracted Value')}
          </label>
          
          <div className="flex-grow flex flex-col bg-surface-container-highest/20 rounded-xl border border-outline-variant/10 p-4 min-h-[120px]">
            {isPatientAssignment ? (
              <div className="flex flex-col justify-between h-full">
                {parsedAssignment ? (
                  <div className="text-sm text-on-surface space-y-1 mb-4">
                    <div><span className="font-semibold text-on-surface-variant">Name:</span> {parsedAssignment.name || 'N/A'}</div>
                    <div><span className="font-semibold text-on-surface-variant">DOB:</span> {parsedAssignment.dob || 'N/A'}</div>
                    <div><span className="font-semibold text-on-surface-variant">Gender:</span> {parsedAssignment.gender || 'N/A'}</div>
                  </div>
                ) : (
                  <em className="text-on-surface-variant/70 text-sm mb-4 block">No patient info extracted</em>
                )}
                <button 
                  className="mt-auto py-2.5 w-full bg-primary text-on-primary rounded-lg font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50"
                  onClick={() => setIsLinkModalOpen(true)}
                  disabled={isSubmitting}
                >
                  Assign Patient
                </button>
                <LinkPatientModal 
                  isOpen={isLinkModalOpen}
                  onClose={() => setIsLinkModalOpen(false)}
                  documentId={item.document_id}
                  suggestedPatientData={{
                    name: parsedAssignment?.name || '',
                    dob: parsedAssignment?.dob || '',
                    sex: parsedAssignment?.gender || '',
                    mrn: parsedAssignment?.patient_id || ''
                  }}
                  onLink={handleLinkPatient}
                />
              </div>
            ) : editMode ? (
              COMPLEX_FIELDS.includes(item.field_name) ? (
                <div className="flex-grow">
                  <DynamicJSONEditor
                    initialValue={item.extracted_value ?? ''}
                    fieldName={item.field_name}
                    onChange={setEditValue}
                    onSubmit={handleEditSubmit}
                    onCancel={() => {
                      setEditMode(false);
                      setEditValue(item.extracted_value ?? '');
                    }}
                  />
                </div>
              ) : (
                <textarea
                  ref={editRef}
                  className="w-full flex-grow bg-surface-container border border-outline-variant/40 rounded-lg p-3 text-on-surface text-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary resize-none"
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleEditSubmit();
                    }
                    if (e.key === 'Escape') {
                      setEditMode(false);
                      setEditValue(item.extracted_value ?? '');
                    }
                  }}
                  placeholder="Enter corrected value…"
                />
              )
            ) : (
              <div className="text-base text-on-surface leading-relaxed break-words whitespace-pre-wrap font-medium">
                {item.extracted_value ?? <em className="text-on-surface-variant/50">null / not extracted</em>}
              </div>
            )}
          </div>
        </div>

        {/* Confidence Warning */}
        {conf < 0.5 && (
          <div className="flex items-center gap-2 px-4 py-3 bg-error-container/10 border border-error/30 rounded-lg text-error text-sm font-medium mb-6">
            <AlertTriangle size={16} />
            <span>Low confidence — please verify carefully against the document image.</span>
          </div>
        )}

        {/* Action Buttons */}
        {isPatientAssignment ? null : editMode ? (
          <div className="flex gap-3 mb-6">
            <button
              className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg font-semibold transition-colors disabled:opacity-50"
              onClick={handleEditSubmit}
              disabled={isSubmitting}
              title="Submit correction and approve (Enter)"
            >
              <CheckCircle2 size={18} /> Submit Edit
            </button>
            <button
              className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-surface-variant hover:bg-surface-variant/80 text-on-surface rounded-lg font-semibold border border-outline-variant/30 transition-colors disabled:opacity-50"
              onClick={() => { setEditMode(false); setEditValue(item.extracted_value ?? ''); }}
              disabled={isSubmitting}
              title="Cancel edit (Esc)"
            >
              <XCircle size={18} /> Cancel
            </button>
          </div>
        ) : (
          <div className="flex gap-2 mb-6">
            <button
              className="flex-1 flex flex-col items-center justify-center py-3 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-500 rounded-xl border border-emerald-500/30 transition-colors disabled:opacity-50 group"
              onClick={() => onAccept(null)}
              disabled={isSubmitting}
              title="Accept extracted value (A)"
            >
              <div className="flex items-center gap-1.5 font-bold mb-1"><CheckCircle2 size={18} /> Accept</div>
              <kbd className="text-[10px] font-mono px-1.5 py-0.5 bg-emerald-500/20 rounded border border-emerald-500/30 group-hover:bg-emerald-500 group-hover:text-white transition-colors">A</kbd>
            </button>
            <button
              className="flex-1 flex flex-col items-center justify-center py-3 bg-primary/10 hover:bg-primary/20 text-primary rounded-xl border border-primary/30 transition-colors disabled:opacity-50 group"
              onClick={() => setEditMode(true)}
              disabled={isSubmitting}
              title="Edit value then approve (E)"
            >
              <div className="flex items-center gap-1.5 font-bold mb-1"><Edit3 size={18} /> Edit</div>
              <kbd className="text-[10px] font-mono px-1.5 py-0.5 bg-primary/20 rounded border border-primary/30 group-hover:bg-primary group-hover:text-white transition-colors">E</kbd>
            </button>
            <button
              className="flex-1 flex flex-col items-center justify-center py-3 bg-error-container/10 hover:bg-error-container/20 text-error rounded-xl border border-error/30 transition-colors disabled:opacity-50 group"
              onClick={onReject}
              disabled={isSubmitting}
              title="Reject this field (R)"
            >
              <div className="flex items-center gap-1.5 font-bold mb-1"><XCircle size={18} /> Reject</div>
              <kbd className="text-[10px] font-mono px-1.5 py-0.5 bg-error/20 rounded border border-error/30 group-hover:bg-error group-hover:text-white transition-colors">R</kbd>
            </button>
          </div>
        )}

        {/* Navigation */}
        <div className="flex items-center justify-between pt-4 border-t border-outline-variant/10">
          <button
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-semibold text-on-surface-variant hover:text-on-surface hover:bg-surface-variant transition-colors disabled:opacity-30 disabled:hover:bg-transparent group"
            onClick={onPrev}
            disabled={index === 0 || isSubmitting}
          >
            <ChevronLeft size={16} /> Prev <kbd className="hidden sm:inline-block text-[10px] font-mono px-1 border border-outline-variant/30 rounded ml-1 group-hover:bg-surface-variant group-hover:border-outline-variant">←</kbd>
          </button>
          
          <div className="flex gap-1 items-center">
            {Array.from({ length: Math.min(total, 7) }).map((_, i) => {
              const isActive = i === index % 7;
              return (
                <div 
                  key={i} 
                  className={`w-1.5 h-1.5 rounded-full transition-colors ${isActive ? 'bg-primary scale-125' : 'bg-outline-variant/30'}`}
                />
              );
            })}
            {total > 7 && <span className="text-[10px] font-bold text-on-surface-variant ml-1">+{total - 7}</span>}
          </div>

          <button
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-semibold text-on-surface-variant hover:text-on-surface hover:bg-surface-variant transition-colors disabled:opacity-30 disabled:hover:bg-transparent group"
            onClick={onNext}
            disabled={index >= total - 1 || isSubmitting}
          >
            <kbd className="hidden sm:inline-block text-[10px] font-mono px-1 border border-outline-variant/30 rounded mr-1 group-hover:bg-surface-variant group-hover:border-outline-variant">→</kbd> Next <ChevronRight size={16} />
          </button>
        </div>
      </div>

      {/* Keyboard Hint Footer */}
      <div className="bg-surface-container-high py-2 px-4 border-t border-outline-variant/10 flex items-center justify-center gap-1.5 text-xs font-medium text-on-surface-variant">
        <Zap size={14} className="text-primary" />
        <span>Keyboard:</span>
        <kbd className="px-1 py-0.5 bg-surface-variant rounded border border-outline-variant/30">Space</kbd> <span>accept</span>
        <span>·</span>
        <kbd className="px-1 py-0.5 bg-surface-variant rounded border border-outline-variant/30">E</kbd> <span>edit</span>
        <span>·</span>
        <kbd className="px-1 py-0.5 bg-surface-variant rounded border border-outline-variant/30">R</kbd> <span>reject</span>
      </div>
    </div>
  );
}
