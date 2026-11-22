// API client talking to the Python FastAPI backend.
// Locally, Vite proxies `/api/*` -> http://127.0.0.1:8000.
// In production, set VITE_API_BASE in Vercel to your Render FastAPI URL.

const API_BASE = import.meta.env.VITE_API_BASE || '';

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data?.detail?.en || data?.detail?.message || `HTTP ${res.status}`);
    err.detail = data?.detail;
    throw err;
  }
  return data;
}

export const api = {
  health: () => request('/api/health'),
  getMarket: (mode, seed, day) =>
    request(`/api/market?mode=${encodeURIComponent(mode)}&seed=${seed}&day=${day}`),
  previewOrder: (body) =>
    request('/api/order/preview', { method: 'POST', body: JSON.stringify(body) }),
  validateOrder: (body) =>
    request('/api/order/validate', { method: 'POST', body: JSON.stringify(body) }),
  evaluateAlerts: (body) =>
    request('/api/alerts/evaluate', { method: 'POST', body: JSON.stringify(body) }),
  checkReason: (body) =>
    request('/api/ai/reason', { method: 'POST', body: JSON.stringify(body) }),
  getCoach: (body) =>
    request('/api/ai/coach', { method: 'POST', body: JSON.stringify(body) }),
  askGuide: (body) =>
    request('/api/ai/ask', { method: 'POST', body: JSON.stringify(body) }),
  getScore: (body) =>
    request('/api/report/score', { method: 'POST', body: JSON.stringify(body) }),
  getReport: (body) =>
    request('/api/ai/report', { method: 'POST', body: JSON.stringify(body) }),
  tts: (text, lang) =>
    request('/api/voice/tts', { method: 'POST', body: JSON.stringify({ text, lang }) }),
  stt: async (audioBlob, lang = 'hi') => {
    const form = new FormData();
    form.append('file', audioBlob, 'voice.webm');
    form.append('lang', lang);
    const res = await fetch(`${API_BASE}/api/voice/stt`, { method: 'POST', body: form });
    return res.json().catch(() => ({ transcript: '' }));
  },
};
