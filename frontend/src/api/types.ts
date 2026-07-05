// Types mirroring backend/app contract shapes exactly. See .frugal-fable/api-contract.md

export type Priority = "high" | "medium" | "low";
export type TaskStatus = "pending" | "scheduled" | "in_progress" | "completed";
export type TimeBlockStatus = "planned" | "active" | "done" | "skipped";
export type BusyBlockSource = "manual" | "gcal";
export type TaskSource = "manual" | "llm_parsed";

export interface Task {
  id: number;
  title: string;
  description: string | null;
  priority: Priority;
  estimated_minutes: number;
  status: TaskStatus;
  due_date: string | null; // YYYY-MM-DD
  created_at: string; // ISO datetime
  source: TaskSource;
}

export interface TaskDraft {
  title: string;
  description: string | null;
  priority: Priority;
  estimated_minutes: number;
  due_date: string | null;
}

export interface TimeBlock {
  id: number;
  task_id: number;
  task_title: string;
  task_priority: Priority;
  date: string; // YYYY-MM-DD
  start_time: string; // ISO datetime
  end_time: string; // ISO datetime
  status: TimeBlockStatus;
}

export interface BusyBlock {
  id: number;
  title: string;
  start_time: string;
  end_time: string;
  source: BusyBlockSource;
  gcal_event_id: string | null;
}

export interface WorkingHoursDay {
  day_of_week: number; // 0=Monday ... 6=Sunday
  start: string; // HH:MM
  end: string; // HH:MM
  enabled: boolean;
}

export interface DaySchedule {
  date: string;
  time_blocks: TimeBlock[];
  busy_blocks: BusyBlock[];
  working_hours: WorkingHoursDay | null;
}

export interface ScheduleRunResult {
  days: DaySchedule[];
  unplaceable: Task[];
}

export interface Document {
  id: number;
  name: string;
  created_at: string;
  num_chunks: number;
}

export interface CalendarStatus {
  connected: boolean;
  configured: boolean;
  last_synced_at: string | null;
}

export interface DocumentQuerySource {
  document_name: string;
  snippet: string;
}

export interface DocumentQueryResult {
  answer: string;
  sources: DocumentQuerySource[];
}

export interface HealthResult {
  ok: boolean;
  ollama: boolean;
}
