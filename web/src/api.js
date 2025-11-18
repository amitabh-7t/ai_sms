import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8001';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auth
export const login = (email, password) => 
  api.post('/auth/login', { email, password });

export const signup = (email, password, full_name) => 
  api.post('/auth/signup', { email, password, full_name });

export const getCurrentUser = () => 
  api.get('/auth/me');

// Students
export const getStudents = () => 
  api.get('/students');

export const getStudentMetrics = (studentId, from, to, granularity = 'minute') => 
  api.get(`/students/${studentId}/metrics`, { 
    params: { from, to, granularity } 
  });

// Classes
export const getClassOverview = (deviceId, from, to) => 
  api.get(`/classes/${deviceId}/overview`, { 
    params: { from, to } 
  });

// Dashboard
export const getDashboardSummary = () => 
  api.get('/dashboard/summary');

// Ingest (for testing)
export const ingestEvent = (event, apiKey) => 
  axios.post(`${API_BASE}/ingest`, event, {
    headers: {
      'X-API-KEY': apiKey,
      'Content-Type': 'application/json',
    },
  });

// Device Management
export const getDevices = () => api.get('/devices');

export const createDevice = (deviceData) =>
  api.post('/devices', deviceData);

export const getDevice = (deviceId) =>
  api.get(`/devices/${deviceId}`);

export const updateDevice = (deviceId, deviceData) =>
  api.put(`/devices/${deviceId}`, deviceData);

export const deleteDevice = (deviceId) =>
  api.delete(`/devices/${deviceId}`);

export const getDeviceStatus = (deviceId) =>
  api.get(`/devices/${deviceId}/status`);

// Capture Sessions
export const createCaptureSession = (sessionData) =>
  api.post('/capture/sessions', sessionData);

export const getCaptureSessions = () =>
  api.get('/capture/sessions');

export const getCaptureSession = (id) =>
  api.get(`/capture/sessions/${id}`);

export const stopCaptureSession = (id) =>
  api.put(`/capture/sessions/${id}/stop`);

export const getCaptureStatus = (deviceId) =>
  api.get(`/capture/status/${deviceId}`);

export default api;