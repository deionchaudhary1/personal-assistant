import type { Task, TaskDraft, HealthResult, Priority, TaskStatus, NewsDigestResponse } from "./types";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      if (data && typeof data.detail === "string") {
        detail = data.detail;
      }
    } catch {
      // ignore parse errors, keep statusText
    }
    const err = new Error(detail) as Error & { status?: number };
    err.status = res.status;
    throw err;
  }
  if (res.status === 204) {
    return undefined as unknown as T;
  }
  return (await res.json()) as T;
}

// ---- Tasks ----

export function getTasks(status?: TaskStatus): Promise<Task[]> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  return request<Task[]>(`/tasks${qs}`);
}

export interface CreateTaskBody {
  title: string;
  description?: string | null;
  priority?: Priority;
  due_date?: string | null;
  source?: string;
}

export function createTask(body: CreateTaskBody): Promise<Task> {
  return request<Task>(`/tasks`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateTask(id: number, patch: Partial<Task>): Promise<Task> {
  return request<Task>(`/tasks/${id}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export function deleteTask(id: number): Promise<void> {
  return request<void>(`/tasks/${id}`, { method: "DELETE" });
}

export function parseTasks(text: string): Promise<{ drafts: TaskDraft[] }> {
  return request<{ drafts: TaskDraft[] }>(`/tasks/parse`, {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

// ---- Health ----

export function getHealth(): Promise<HealthResult> {
  return request<HealthResult>(`/health`);
}

// ---- News ----

export function getNews(): Promise<NewsDigestResponse> {
  return request<NewsDigestResponse>(`/news`);
}

export function markNewsRead(id: number): Promise<NewsDigestResponse> {
  return request<NewsDigestResponse>(`/news/${id}/read`, { method: "POST" });
}

export function markAllNewsRead(): Promise<NewsDigestResponse> {
  return request<NewsDigestResponse>(`/news/read-all`, { method: "POST" });
}

// ---- Push ----

export function getPushPublicKey(): Promise<{ public_key: string }> {
  return request<{ public_key: string }>(`/push/public-key`);
}

export function subscribePush(sub: {
  endpoint: string;
  keys: { p256dh: string; auth: string };
}): Promise<void> {
  return request<void>(`/push/subscribe`, {
    method: "POST",
    body: JSON.stringify(sub),
  });
}

export function unsubscribePush(endpoint: string): Promise<void> {
  return request<void>(`/push/unsubscribe`, {
    method: "POST",
    body: JSON.stringify({ endpoint }),
  });
}

export { request };
