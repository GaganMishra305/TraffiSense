/* Thin fetch wrapper around the TraffiSense API. */
const API = {
  async _get(path) {
    const r = await fetch(path);
    if (!r.ok) throw new Error(`${path} -> ${r.status}`);
    return r.json();
  },
  async _post(path, body) {
    const r = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`${path} -> ${r.status}`);
    return r.json();
  },
  config: () => API._get('/api/config'),
  venues: () => API._get('/api/venues'),
  overview: () => API._get('/api/overview'),
  heatmap: () => API._get('/api/heatmap'),
  examples: () => API._get('/api/assistant/examples'),
  predict: (ev) => API._post('/api/predict', ev),
  optimize: (ev) => API._post('/api/optimize', ev),
  scenarios: (ev) => API._post('/api/scenarios', ev),
  diversions: (ev) => API._post('/api/diversions', ev),
  emergency: (ev) => API._post('/api/emergency', ev),
  assistant: (question, event) => API._post('/api/assistant', { question, event }),
};

/* Colour helpers shared across modules. */
function congestionColor(pct) {
  if (pct >= 85) return '#ef4444';
  if (pct >= 70) return '#fb923c';
  if (pct >= 50) return '#fbbf24';
  if (pct >= 30) return '#34d399';
  return '#22d3ee';
}
function sevClass(sev) { return 'sev-' + sev; }
