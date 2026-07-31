import axios from 'axios';

// Use the same origin in development and when FastAPI serves the built UI.
// A full URL can still be supplied for deployments with a separate API host.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Accept': 'application/json',
  },
});

export const uploadDocuments = async (files) => {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append('files', file);
  });

  const response = await apiClient.post('/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const fetchDocuments = async () => {
  const response = await apiClient.get('/documents');
  return response.data;
};

export const fetchDocumentById = async (documentId) => {
  const response = await apiClient.get(`/documents/${documentId}`);
  return response.data;
};

export const deleteDocument = async (documentId) => {
  const response = await apiClient.delete(`/documents/${documentId}`);
  return response.data;
};

export const deleteAllDocuments = async () => {
  const response = await apiClient.delete('/documents');
  return response.data;
};

export const fetchUploadLogs = async () => {
  const response = await apiClient.get('/documents/upload-logs');
  return response.data;
};

export default apiClient;

