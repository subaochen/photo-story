const API_BASE = 'http://localhost:8000/api/v1';
const WS_BASE = 'ws://localhost:8000';

export async function api(method, path, body, token) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  return res.json();
}

export function connectWS(taskId, onMessage) {
  const ws = new WebSocket(`${WS_BASE}/ws/task/${taskId}`);
  ws.onmessage = (e) => onMessage(JSON.parse(e.data));
  return ws;
}
