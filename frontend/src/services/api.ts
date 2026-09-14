import axios from 'axios';
import { useAuthStore } from '../store/authStore';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const apiClient: any = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

apiClient.interceptors.request.use(
  (config: any) => {
    const nextConfig = config;
    const token = useAuthStore.getState().token;
    nextConfig.headers = nextConfig.headers || {};
    if (token) {
      nextConfig.headers.Authorization = 'Bearer ' + token;
    }
    return nextConfig;
  },
  (error: unknown) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response: any) => response.data,
  (error: any) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
      window.location.href = '/login';
    }
    return Promise.reject(error.response?.data || error.message);
  }
);

export default apiClient;
