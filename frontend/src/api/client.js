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

// Request interceptor to attach JWT token to all requests
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

// Response interceptor to handle 401 Unauthorized errors and token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // Prevent infinite loops if refresh itself fails
    if (error.response && error.response.status === 401 && !originalRequest._retry && !originalRequest.url.includes('/auth/refresh')) {
      originalRequest._retry = true;
      const refresh_token = localStorage.getItem('refresh_token');
      
      if (refresh_token) {
        try {
          // Use a fresh axios instance to avoid interceptor loops if something goes wrong
          const res = await axios.post(`${API_BASE_URL}/auth/refresh`, { refresh_token });
          const new_token = res.data.access_token;
          localStorage.setItem('token', new_token);
          if (res.data.refresh_token) {
             localStorage.setItem('refresh_token', res.data.refresh_token);
          }
          
          originalRequest.headers.Authorization = `Bearer ${new_token}`;
          return apiClient(originalRequest); // retry the original request
        } catch (refreshError) {
          // Refresh failed, clear tokens and redirect
          localStorage.removeItem('token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      } else {
        // No refresh token available
        localStorage.removeItem('token');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;
