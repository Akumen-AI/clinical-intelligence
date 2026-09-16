import React, { useState, useEffect } from 'react';
import { saveNote, fetchNotes } from '../api';

export default function AddNote({ patientId, complaintType, onNoteSaved }) {
  const [noteContent, setNoteContent] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [savedNote, setSavedNote] = useState(null);
  const [notesList, setNotesList] = useState([]);

  const loadNotes = async () => {
    if (!patientId) return;
    try {
      const notes = await fetchNotes(patientId);
      setNotesList(notes);
    } catch (e) {
      console.error("Failed to fetch notes:", e);
    }
  };

  useEffect(() => {
    loadNotes();
  }, [patientId]);

  const handleSave = async () => {
    if (!noteContent.trim() || !patientId) return;
    setSaving(true);
    setSaveError(null);
    try {
      const result = await saveNote({
        patient_id: patientId,
        complaint_type: complaintType,
        content: noteContent,
      });
      setSavedNote(result);
      setNoteContent('');
      await loadNotes();
      onNoteSaved?.(result);
    } catch (err) {
      const detail = err?.response?.data?.detail ?? "Save failed. Please try again.";
      setSaveError(detail);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col gap-4 p-4 bg-surface rounded-xl border border-line shadow-sm">
      <div className="flex flex-col gap-2">
        <label className="text-sm font-bold text-ink">Clinical Note</label>
        <textarea
          className="w-full min-h-[160px] bg-paper rounded-xl border border-line p-4 text-sm text-ink placeholder:text-slate focus:outline-none focus:border-teal focus:ring-1 focus:ring-teal transition-colors resize-none"
          placeholder="Enter clinical observations here…"
          value={noteContent}
          onChange={(e) => setNoteContent(e.target.value)}
          data-testid="note-textarea"
        />
        <div className="flex items-center gap-3 mt-2">
          <button
            onClick={handleSave}
            disabled={saving || !noteContent.trim()}
            className="px-6 py-2 bg-teal text-white rounded-lg font-bold text-sm hover:shadow-md hover:-translate-y-[1px] disabled:opacity-50 disabled:shadow-none disabled:translate-y-0 disabled:cursor-not-allowed transition-all"
            data-testid="save-note-btn"
          >
            {saving ? "Saving…" : "Save Note"}
          </button>
        </div>
        {saveError && (
          <p className="text-danger text-sm mt-2 font-medium" data-testid="save-note-error">{saveError}</p>
        )}
        {savedNote && (
          <p className="text-success text-sm mt-2 font-medium" data-testid="save-note-success">
            Note saved at {new Date(savedNote.created_at).toLocaleTimeString()}.
          </p>
        )}
      </div>

      {notesList.length > 0 && (
        <div className="mt-4 pt-4 border-t border-line flex flex-col gap-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate">Saved Notes ({notesList.length})</h4>
          <div className="flex flex-col gap-3 max-h-48 overflow-y-auto custom-scrollbar">
            {notesList.map((n) => (
              <div key={n.id} className="p-3 rounded-lg bg-paper border border-line text-sm text-ink flex flex-col gap-1.5 shadow-sm">
                <div className="flex justify-between font-bold text-slate text-xs uppercase tracking-wider">
                  <span>{n.author_role}</span>
                  <span>{new Date(n.created_at).toLocaleString()}</span>
                </div>
                <p className="whitespace-pre-wrap leading-relaxed">{n.content}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
