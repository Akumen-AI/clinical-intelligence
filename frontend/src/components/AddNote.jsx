import React, { useState, useEffect } from 'react';
import { saveNote, fetchNotes } from '../api/noteApi';

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
    <div className="flex flex-col gap-4 p-4 bg-surface rounded-xl border border-outline-variant/30">
      <div className="flex flex-col gap-2">
        <label className="text-sm font-semibold text-on-surface">Clinical Note</label>
        <textarea
          className="w-full min-h-[160px] bg-surface-container rounded-xl border border-outline-variant/30 p-4 text-sm text-on-surface placeholder:text-on-surface-variant/50 resize-none focus:outline-none focus:ring-2 focus:ring-primary/40"
          placeholder="Enter clinical observations here…"
          value={noteContent}
          onChange={(e) => setNoteContent(e.target.value)}
          data-testid="note-textarea"
        />
        <div className="flex items-center gap-3 mt-2">
          <button
            onClick={handleSave}
            disabled={saving || !noteContent.trim()}
            className="px-4 py-2 bg-blue-700 text-white rounded disabled:opacity-50 hover:bg-blue-800 transition-colors font-medium text-sm"
            data-testid="save-note-btn"
          >
            {saving ? "Saving…" : "Save Note"}
          </button>
        </div>
        {saveError && (
          <p className="text-red-600 text-sm mt-2" data-testid="save-note-error">{saveError}</p>
        )}
        {savedNote && (
          <p className="text-green-700 text-sm mt-2" data-testid="save-note-success">
            Note saved at {new Date(savedNote.created_at).toLocaleTimeString()}.
          </p>
        )}
      </div>

      {notesList.length > 0 && (
        <div className="mt-4 pt-4 border-t border-outline-variant/20 flex flex-col gap-2">
          <h4 className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">Saved Notes ({notesList.length})</h4>
          <div className="flex flex-col gap-2 max-h-48 overflow-y-auto">
            {notesList.map((n) => (
              <div key={n.id} className="p-3 rounded-lg bg-surface-variant/40 border border-outline-variant/10 text-xs text-on-surface flex flex-col gap-1">
                <div className="flex justify-between font-semibold text-on-surface-variant">
                  <span>{n.author_role}</span>
                  <span>{new Date(n.created_at).toLocaleString()}</span>
                </div>
                <p className="whitespace-pre-wrap">{n.content}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
