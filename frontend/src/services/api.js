/**
 * api.js - Every call from the React app to the SolarSaathi backend goes through here.
 *
 * - Browser: requests go to /api/... and Vite forwards them to the backend (vite.config.js).
 * - Android app (Capacitor): set VITE_API_URL in frontend/.env to the PC's Wi-Fi address.
 * - Staff login token is added automatically; customers never need one.
 */
import axios from 'axios';

const API_URL = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '');
const api = axios.create({ baseURL: API_URL, timeout: 90 * 1000 });

export const storage = {          // browser storage can be blocked (private mode): never crash because of it
  get(key, area = sessionStorage) { try { return area.getItem(key); } catch { return null; } },
  set(key, value, area = sessionStorage) { try { area.setItem(key, value); } catch { /* ignore */ } },
  remove(key, area = sessionStorage) { try { area.removeItem(key); } catch { /* ignore */ } },
};

api.interceptors.request.use((config) => {
  const token = storage.get('ss_token');
  if (token && !config.url.startsWith('/chat') && !config.url.startsWith('/quotes')) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const detail = error.response?.data?.detail;
    const url = error.config?.url || '';
    if (status === 401 && !url.includes('/auth/login') && window.location.pathname.startsWith('/staff')) {
      storage.remove('ss_token');
      storage.remove('ss_user');
      window.location.href = '/staff/login';
    }
    if (typeof detail === 'string') error.message = detail;
    else if (Array.isArray(detail)) error.message = detail.map((d) => d.msg).join(', ');
    else if (error.code === 'ECONNABORTED') error.message = 'The server is taking too long. Please try again.';
    else if (!error.response) error.message = 'Cannot reach the server. Check your internet / Wi-Fi.';
    return Promise.reject(error);
  }
);

export async function downloadFile(path, filename) {
  const res = await api.get(path, { responseType: 'blob' });
  const url = URL.createObjectURL(res.data);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

export { API_URL };
export default api;
