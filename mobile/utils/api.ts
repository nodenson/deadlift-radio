const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://100.70.51.50:8000';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API ${res.status}: ${err}`);
  }
  return res.json();
}

export interface Session {
  id: number;
  date: string;
  bodyweight: number | null;
  notes: string | null;
}

export interface Set {
  load: number;
  reps: number;
}

export interface Exercise {
  id: number;
  name: string;
  sets: Set[];
  e1rm: number | null;
}

export interface SessionDetail extends Session {
  exercises: Exercise[];
}

export interface TonnageWeek {
  week: string;
  tonnage: number;
  sessions: number;
}

export interface NewSession {
  date: string;
  bodyweight?: number;
  notes?: string;
  exercises: { name: string; sets: { load: number; reps: number }[] }[];
}

export const api = {
  getSessions: (limit = 20) =>
    apiFetch<Session[]>(`/api/sessions?limit=${limit}`),

  getLatestSession: () =>
    apiFetch<SessionDetail>('/api/sessions/latest'),

  getSession: (id: number) =>
    apiFetch<SessionDetail>(`/api/sessions/${id}`),

  getSessionsByDate: (date: string) =>
    apiFetch<Session[]>(`/api/sessions/date/${date}`),

  getTonnage: (weeks = 4) =>
    apiFetch<TonnageWeek[]>(`/api/analytics/tonnage?weeks=${weeks}`),

  logRaw: (raw_text: string) =>
    apiFetch<SessionDetail>("/api/log", { method: "POST", body: JSON.stringify({ raw_text }) }),
  postSession: (data: NewSession) =>
    apiFetch<SessionDetail>('/api/sessions', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};
