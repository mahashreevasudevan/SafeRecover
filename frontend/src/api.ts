import type { Metrics, RecoveryEvent } from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json();
}

export const api = {
  events: () => request<RecoveryEvent[]>("/api/v1/events"),
  metrics: () => request<Metrics>("/api/v1/metrics"),
  approve: (id: string, approved: boolean) => request<RecoveryEvent>(`/api/v1/events/${id}/approval`, {
    method: "POST",
    body: JSON.stringify({ approved, reviewer: "dashboard-operator" }),
  }),
};
