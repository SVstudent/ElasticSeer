/// <reference types="vite/client" />
import axios from 'axios';

// In development, Vite proxy handles /api -> localhost:8001
// In production, we need the full backend URL
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 300000, // 5 minutes - matches backend timeouts
});

export default api;
