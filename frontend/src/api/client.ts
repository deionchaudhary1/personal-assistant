import type {
  Task,
  TaskDraft,
  TimeBlock,
  BusyBlock,
  WorkingHoursDay,
  DaySchedule,
  ScheduleRunResult,
  Document,
  CalendarStatus,
  DocumentQueryResult,
  HealthResult,
  Priority,
  TaskStatus,
} from "./types";

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
  estimated_minutes?: number;
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

export function estimateTask(
  title: string,
  description?: string | null
): Promise<{ estimated_minutes: number }> {
  return request<{ estimated_minutes: number }>(`/tasks/estimate`, {
    method: "POST",
    body: JSON.stringify({ title, description }),
  });
}

// ---- Schedule ----

export function getDaySchedule(date?: string): Promise<DaySchedule> {
  const qs = date ? `?date=${encodeURIComponent(date)}` : "";
  return request<DaySchedule>(`/schedule/day${qs}`);
}

export function getWeekSchedule(
  start?: string
): Promise<{ days: DaySchedule[] }> {
  const qs = start ? `?start=${encodeURIComponent(start)}` : "";
  return request<{ days: DaySchedule[] }>(`/schedule/week${qs}`);
}

export function runSchedule(
  scope: "day" | "week",
  start_date?: string
): Promise<ScheduleRunResult> {
  return request<ScheduleRunResult>(`/schedule/run`, {
    method: "POST",
    body: JSON.stringify({ scope, ...(start_date ? { start_date } : {}) }),
  });
}

export function endOfDay(
  completed_task_ids: number[],
  date?: string
): Promise<ScheduleRunResult> {
  return request<ScheduleRunResult>(`/schedule/end-of-day`, {
    method: "POST",
    body: JSON.stringify({ completed_task_ids, ...(date ? { date } : {}) }),
  });
}

export function patchBlock(
  id: number,
  status: TimeBlock["status"]
): Promise<TimeBlock> {
  return request<TimeBlock>(`/schedule/blocks/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

// ---- Busy blocks ----

export function getBusyBlocks(date?: string): Promise<BusyBlock[]> {
  const qs = date ? `?date=${encodeURIComponent(date)}` : "";
  return request<BusyBlock[]>(`/busy-blocks${qs}`);
}

export function createBusyBlock(body: {
  title: string;
  start_time: string;
  end_time: string;
}): Promise<BusyBlock> {
  return request<BusyBlock>(`/busy-blocks`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function deleteBusyBlock(id: number): Promise<void> {
  return request<void>(`/busy-blocks/${id}`, { method: "DELETE" });
}

// ---- Calendar ----

export function getCalendarStatus(): Promise<CalendarStatus> {
  return request<CalendarStatus>(`/calendar/status`);
}

export function getCalendarAuthUrl(): Promise<{ url: string }> {
  return request<{ url: string }>(`/calendar/auth-url`);
}

export function syncCalendar(): Promise<{ synced: number }> {
  return request<{ synced: number }>(`/calendar/sync`, { method: "POST" });
}

// ---- Documents ----

export function getDocuments(): Promise<Document[]> {
  return request<Document[]>(`/documents`);
}

export function createDocument(name: string, text: string): Promise<Document> {
  return request<Document>(`/documents`, {
    method: "POST",
    body: JSON.stringify({ name, text }),
  });
}

export function deleteDocument(id: number): Promise<void> {
  return request<void>(`/documents/${id}`, { method: "DELETE" });
}

export function queryDocuments(question: string): Promise<DocumentQueryResult> {
  return request<DocumentQueryResult>(`/documents/query`, {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

// ---- Settings ----

export function getWorkingHours(): Promise<WorkingHoursDay[]> {
  return request<WorkingHoursDay[]>(`/settings/working-hours`);
}

export function putWorkingHours(
  days: WorkingHoursDay[]
): Promise<WorkingHoursDay[]> {
  return request<WorkingHoursDay[]>(`/settings/working-hours`, {
    method: "PUT",
    body: JSON.stringify(days),
  });
}

// ---- Health ----

export function getHealth(): Promise<HealthResult> {
  return request<HealthResult>(`/health`);
}

export { request };
