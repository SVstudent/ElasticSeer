/// <reference types="vite/client" />
import axios from 'axios';

// Use relative paths to allow server-side proxying (Vite in dev, Vercel in prod)
const API_BASE_URL = '';

const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 300000, // 5 minutes - matches backend timeouts
});

export default api;
