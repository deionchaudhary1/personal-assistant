// Types mirroring the backend's JSON contract shapes.

export type Priority = "high" | "medium" | "low";
export type TaskStatus = "pending" | "completed";
export type TaskSource = "manual" | "llm_parsed";

export interface Task {
  id: number;
  title: string;
  description: string | null;
  priority: Priority;
  status: TaskStatus;
  due_date: string | null; // YYYY-MM-DD
  created_at: string; // ISO datetime
  source: TaskSource;
}

export interface TaskDraft {
  title: string;
  description: string | null;
  priority: Priority;
  due_date: string | null;
}

export interface HealthResult {
  ok: boolean;
  ollama: boolean;
}
