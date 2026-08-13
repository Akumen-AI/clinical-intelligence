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

/**
 * ReviewFieldCard – right-panel component for the side-by-side review UI.
 *
 * Props:
 *  - item:          PendingReviewContextResponse object (from /context endpoint)
 *  - index:         0-based index of this item in the current document's pending list
 *  - total:         total pending items in the current document
 *  - onAccept(correctedValue|null): call with null to accept as-is, or string for edited value
 *  - onReject():    call to reject the field
 *  - onPrev():      navigate to previous field
 *  - onNext():      navigate to next field
 *  - isSubmitting:  boolean — disables actions while in-flight
 */
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

  // Reset edit state when item changes
  useEffect(() => {
    setEditMode(false);
    setEditValue(item?.extracted_value ?? '');
  }, [item?.id]);

  // Focus the edit input when entering edit mode
  useEffect(() => {
    if (editMode && editRef.current) {
      editRef.current.focus();
      editRef.current.select();
    }
  }, [editMode]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e) => {
      // Don't steal input while the reviewer is correcting a value.
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) return;
      if (isSubmitting) return;

      switch (e.key.toLowerCase()) {
        case 'a':
          e.preventDefault();
          onAccept(null);
          break;
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
  const confColor =
    conf >= 0.8 ? '#10b981' : conf >= 0.5 ? '#f59e0b' : '#ef4444';
  const confLabel = conf >= 0.8 ? 'High' : conf >= 0.5 ? 'Medium' : 'Low';

  const progressPct = total > 0 ? ((index) / total) * 100 : 0;

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
    <div className="rfc-root">
      {/* ── Document reference ── */}
      <div className="rfc-doc-ref">
        <FileText size={13} color="var(--text-dim)" />
        <span className="rfc-doc-name">{item.document_filename || item.document_id}</span>
        <span className="rfc-doc-type tag">{item.document_filetype?.toUpperCase() || 'DOC'}</span>
      </div>

      {/* ── Progress ── */}
      <div className="rfc-progress-wrap">
        <div className="rfc-progress-labels">
          <span>Field {index + 1} of {total}</span>
          <span style={{ color: 'var(--text-dim)' }}>{total - index - 1} remaining</span>
        </div>
        <div className="rfc-progress-track">
          <div className="rfc-progress-fill" style={{ width: `${progressPct}%` }} />
        </div>
      </div>

      {/* ── Field header ── */}
      <div className="rfc-field-header">
        <div className="rfc-field-name">{item.field_name}</div>
        <div className="rfc-conf-badge" style={{ background: `${confColor}22`, border: `1px solid ${confColor}55` }}>
          <span className="confidence-dot" style={{ background: confColor }} />
          <span style={{ color: confColor, fontWeight: 700 }}>{confPct}%</span>
          <span style={{ color: confColor, opacity: 0.8 }}>{confLabel}</span>
        </div>
      </div>

      {/* ── Confidence bar ── */}
      <div className="rfc-conf-bar-track">
        <div className="rfc-conf-bar-fill" style={{ width: `${confPct}%`, background: confColor }} />
      </div>

      {/* ── Extracted value / edit ── */}
      <div className="rfc-value-section">
        <label className="rfc-value-label">
          {editMode ? 'Corrected Value' : (isPatientAssignment ? 'Extracted Patient Info' : 'Extracted Value')}
        </label>

        {isPatientAssignment ? (
          <div className="rfc-value-display">
            {parsedAssignment ? (
              <div>
                <div><strong>Name:</strong> {parsedAssignment.name || 'N/A'}</div>
                <div><strong>DOB:</strong> {parsedAssignment.dob || 'N/A'}</div>
                <div><strong>Gender:</strong> {parsedAssignment.gender || 'N/A'}</div>
              </div>
            ) : (
              <em style={{ color: 'var(--text-dim)' }}>No patient info extracted</em>
            )}
            <button 
              className="btn btn-primary" 
              style={{ marginTop: '1rem', width: '100%' }}
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
          ) : (
            <textarea
              ref={editRef}
              className="rfc-edit-input"
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
              rows={3}
              placeholder="Enter corrected value…"
            />
          )
        ) : (
          <div className="rfc-value-display">
            {item.extracted_value ?? <em style={{ color: 'var(--text-dim)' }}>null / not extracted</em>}
          </div>
        )}
      </div>

      {/* ── Confidence warning ── */}
      {conf < 0.5 && (
        <div className="rfc-low-conf-warn">
          <AlertTriangle size={13} color="#f59e0b" />
          <span>Low confidence — please verify carefully against the document image.</span>
        </div>
      )}

      {/* ── Action buttons ── */}
      {isPatientAssignment ? null : editMode ? (
        <div className="rfc-actions">
          <button
            id="review-submit-edit-btn"
            className="rfc-btn rfc-btn-accept"
            onClick={handleEditSubmit}
            disabled={isSubmitting}
            title="Submit correction and approve (Enter)"
          >
            <CheckCircle2 size={16} />
            Submit Edit
          </button>
          <button
            className="rfc-btn rfc-btn-reject"
            onClick={() => { setEditMode(false); setEditValue(item.extracted_value ?? ''); }}
            disabled={isSubmitting}
            title="Cancel edit (Esc)"
          >
            <XCircle size={16} />
            Cancel
          </button>
        </div>
      ) : (
        <div className="rfc-actions">
          <button
            id="review-accept-btn"
            className="rfc-btn rfc-btn-accept"
            onClick={() => onAccept(null)}
            disabled={isSubmitting}
            title="Accept extracted value (A)"
          >
            <CheckCircle2 size={16} />
            Accept
            <kbd className="rfc-kbd">A</kbd>
          </button>
          <button
            id="review-edit-btn"
            className="rfc-btn rfc-btn-edit"
            onClick={() => setEditMode(true)}
            disabled={isSubmitting}
            title="Edit value then approve (E)"
          >
            <Edit3 size={16} />
            Edit
            <kbd className="rfc-kbd">E</kbd>
          </button>
          <button
            id="review-reject-btn"
            className="rfc-btn rfc-btn-reject"
            onClick={onReject}
            disabled={isSubmitting}
            title="Reject this field (R)"
          >
            <XCircle size={16} />
            Reject
            <kbd className="rfc-kbd">R</kbd>
          </button>
        </div>
      )}

      {/* ── Navigation ── */}
      <div className="rfc-nav">
        <button
          id="review-prev-btn"
          className="rfc-nav-btn"
          onClick={onPrev}
          disabled={index === 0 || isSubmitting}
          title="Previous field (←)"
        >
          <ChevronLeft size={16} />
          Prev
          <kbd className="rfc-kbd">←</kbd>
        </button>
        <div className="rfc-nav-dots">
          {Array.from({ length: Math.min(total, 9) }).map((_, i) => (
            <span
              key={i}
              className="rfc-nav-dot"
              style={{
                background: i === index % 9 ? 'var(--primary-cyan)' : 'var(--border-light)',
              }}
            />
          ))}
          {total > 9 && <span style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>+{total - 9}</span>}
        </div>
        <button
          id="review-next-btn"
          className="rfc-nav-btn"
          onClick={onNext}
          disabled={index >= total - 1 || isSubmitting}
          title="Next field (→)"
        >
          Next
          <kbd className="rfc-kbd">→</kbd>
          <ChevronRight size={16} />
        </button>
      </div>

      {/* ── Keyboard hint ── */}
      <div className="rfc-hint-strip">
        <Zap size={11} color="var(--primary-cyan)" />
          <span>Shortcuts: <kbd className="rfc-kbd">A</kbd>/<kbd className="rfc-kbd">Space</kbd> accept · <kbd className="rfc-kbd">E</kbd> edit · <kbd className="rfc-kbd">R</kbd> reject · <kbd className="rfc-kbd">← →</kbd> navigate</span>
      </div>
    </div>
  );
}
