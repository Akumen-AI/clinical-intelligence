import axios from "./axiosInstance"; // reuse existing authenticated axios

export interface NotePayload {
  patient_id: string;
  complaint_type?: string;
  content: string;
}

export interface NoteRecord {
  id: string;
  patient_id: string;
  author_id: string;
  author_role: string;
  complaint_type: string | null;
  content: string;
  created_at: string;
  updated_at: string;
}

export const saveNote = async (payload: NotePayload): Promise<NoteRecord> => {
  const { data } = await axios.post<NoteRecord>("/api/v1/notes", payload);
  return data;
};

export const fetchNotes = async (patientId: string): Promise<NoteRecord[]> => {
  const { data } = await axios.get<NoteRecord[]>(`/api/v1/notes/${patientId}`);
  return data;
};
