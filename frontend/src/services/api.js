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

export const fetchDocumentStatus = async (documentId) => {
  const response = await apiClient.get(`/documents/${documentId}/status`);
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

export const fetchDocumentFields = async (documentId) => {
  const response = await apiClient.get(`/documents/${documentId}/fields`);
  return response.data;
};

export const extractDocumentFields = async (documentId) => {
  const response = await apiClient.post(`/documents/${documentId}/extract`);
  return response.data;
};

// ── Review Queue (Story 3.1) ───────────────────────────────────────────────

/**
 * Fetch paginated pending review items.
 * @param {string|null} documentId - optional filter
 * @param {number} page - 1-indexed
 * @param {number} pageSize
 */
export const fetchPendingReviews = async (documentId = null, page = 1, pageSize = 50) => {
  const params = { page, page_size: pageSize };
  if (documentId) params.document_id = documentId;
  const response = await apiClient.get('/review/pending', { params });
  return response.data;
};

/**
 * Fetch enriched context for one pending review item (joins document + bounding box).
 */
export const fetchReviewContext = async (reviewId) => {
  const response = await apiClient.get(`/review/pending/${reviewId}/context`);
  return response.data;
};

/**
 * Submit an accept / reject decision.
 * @param {string} reviewId
 * @param {'approve'|'reject'} action
 * @param {string|null} correctedValue - if set, writes this value to the canonical record
 * @param {string|null} reviewerId
 */
export const submitReviewAction = async (reviewId, action, correctedValue = null, reviewerId = null) => {
  const payload = { action };
  if (correctedValue !== null) payload.corrected_value = correctedValue;
  if (reviewerId) payload.reviewer_id = reviewerId;
  const response = await apiClient.patch(`/review/pending/${reviewId}`, payload);
  return response.data;
};

/**
 * Returns the URL to stream the document image for a given review item.
 * @param {string} reviewId
 * @param {boolean} fullPage - request the full page instead of cropped region
 */
export const getReviewImageUrl = (reviewId, fullPage = false) => {
  const base = API_BASE_URL.replace(/\/$/, '');
  return `${base}/review/pending/${reviewId}/image${fullPage ? '?full_page=true' : ''}`;
};

/**
 * Returns the static URL for a document upload given its raw_uri.
 * raw_uri is typically  'uploads/<filename>'
 */
export const getDocumentStaticUrl = (rawUri) => {
  if (!rawUri) return null;
  // raw_uri = 'uploads/xyz.png' → served at /uploads/xyz.png by FastAPI StaticFiles
  const relative = rawUri.startsWith('/') ? rawUri : `/${rawUri}`;
  const apiOrigin = API_BASE_URL.startsWith('http')
    ? new URL(API_BASE_URL).origin
    : window.location.origin.replace('5173', '8000'); // dev proxy
  return `${apiOrigin}${relative}`;
};

/** Returns the browser-accessible URL for the original uploaded document. */
export const getDocumentFileUrl = (documentId) => {
  if (!documentId) return null;
  const base = API_BASE_URL.replace(/\/$/, '');
  return `${base}/documents/${documentId}/file`;
};

export const fetchThresholdConfig = async () => {
  const response = await apiClient.get('/review/config/threshold');
  return response.data;
};

export const updateThresholdConfig = async (threshold) => {
  const response = await apiClient.put('/review/config/threshold', { threshold });
  return response.data;
};

// ── Patient Timeline (Story 4.2) ───────────────────────────────────────────

export const fetchTimeline = async (patientId = null) => {
  const params = {};
  if (patientId) params.patient_id = patientId;
  const response = await apiClient.get('/timeline', { params });
  return response.data;
};

export const fetchTimelineEvent = async (documentId) => {
  const response = await apiClient.get(`/timeline/${documentId}`);
  return response.data;
};

// ── Canonical Patient Records ──────────────────────────────────────────────

/**
 * Fetch paginated canonical patient records.
 * @param {Object} params - Query filters
 * @param {string|null} params.document_id
 * @param {string|null} params.patient_id
 * @param {string|null} params.field_name
 * @param {string|null} params.search
 * @param {number} params.page - 1-indexed
 * @param {number} params.page_size
 */
export const fetchCanonicalRecords = async ({
  document_id = null,
  patient_id = null,
  field_name = null,
  search = null,
  page = 1,
  page_size = 50,
} = {}) => {
  const params = { page, page_size };
  if (document_id) params.document_id = document_id;
  if (patient_id) params.patient_id = patient_id;
  if (field_name) params.field_name = field_name;
  if (search) params.search = search;
  const response = await apiClient.get('/canonical-records', { params });
  return response.data;
};

/**
 * Fetch a single canonical record by ID.
 * @param {string} recordId
 */
export const fetchCanonicalRecord = async (recordId) => {
  const response = await apiClient.get(`/canonical-records/${recordId}`);
  return response.data;
};

export default apiClient;

