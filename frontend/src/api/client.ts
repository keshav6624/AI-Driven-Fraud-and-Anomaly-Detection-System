const API_BASE = '';

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(opts.headers as Record<string, string> || {}),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, { ...opts, headers });
  if (res.status === 401) {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  login: (username: string, password: string) =>
    request<{ access_token: string; role: string; username: string }>('/auth/login', {
      method: 'POST', body: JSON.stringify({ username, password }),
    }),

  getProjects: (params: Record<string, string | number | boolean | undefined>) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') q.set(k, String(v)); });
    return request<{ items: any[]; total: number; page: number; page_size: number }>(`/projects?${q}`);
  },

  getProject: (id: number) => request<any>(`/projects/${id}`),

  getMapPoints: (state?: string) =>
    request<any[]>(`/map/projects${state ? `?state=${encodeURIComponent(state)}` : ''}`),

  getStates: () => request<string[]>('/projects/meta/states'),

  getOverview: () => request<any>('/analytics/overview'),
  getRiskDistribution: () => request<Record<string, number>>('/analytics/risk-distribution'),
  getAnomalyScatter: () => request<any[]>('/analytics/anomaly/scatter'),
  getAnomalyDistribution: () => request<{ bins: number[]; counts: number[] }>('/analytics/anomaly/distribution'),
  getDuplicateSummary: () => request<any>('/analytics/duplicates/summary'),
  getDuplicates: (params: Record<string, any>) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') q.set(k, String(v)); });
    return request<{ items: any[]; total: number }>(`/analytics/duplicates?${q}`);
  },

  getCases: (params: Record<string, any>) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') q.set(k, String(v)); });
    return request<{ items: any[]; total: number }>(`/investigations?${q}`);
  },
  createCase: (data: any) => request<any>('/investigations', { method: 'POST', body: JSON.stringify(data) }),
  updateCase: (id: number, data: any) => request<any>(`/investigations/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  addNote: (caseId: number, body: string) =>
    request<any>(`/investigations/${caseId}/notes`, { method: 'POST', body: JSON.stringify({ body }) }),

  // ML / AI endpoints
  scoreMember: (data: { mp_name: string; state: string; constituency: string; allocated_amount?: number | null }) =>
    request<any>('/ml/score', { method: 'POST', body: JSON.stringify(data) }),

  runBatchInference: () => request<any>('/ml/batch', { method: 'POST', body: '{}' }),

  askAssistant: (question: string) =>
    request<{ answer: string; sql: string; intent: string; result_count: number; data: any[] | null; visualization_hint: string | null }>(
      '/ml/ask', { method: 'POST', body: JSON.stringify({ question }) }
    ),

  retrainModels: () => request<any>('/ml/retrain', { method: 'POST', body: '{}' }),
};
