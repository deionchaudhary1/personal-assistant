import { useState } from "react";
import type { Priority } from "../api/types";
import { estimateTask } from "../api/client";

export interface TaskFormValues {
  title: string;
  description: string;
  priority: Priority;
  estimated_minutes: number;
  due_date: string;
}

const EMPTY: TaskFormValues = {
  title: "",
  description: "",
  priority: "medium",
  estimated_minutes: 30,
  due_date: "",
};

export default function TaskForm({
  initial,
  submitLabel = "New task",
  onSubmit,
  onCancel,
}: {
  initial?: Partial<TaskFormValues>;
  submitLabel?: string;
  onSubmit: (values: TaskFormValues) => void;
  onCancel?: () => void;
}) {
  const [values, setValues] = useState<TaskFormValues>({
    ...EMPTY,
    ...initial,
  });
  const [estimating, setEstimating] = useState(false);

  function set<K extends keyof TaskFormValues>(key: K, val: TaskFormValues[K]) {
    setValues((v) => ({ ...v, [key]: val }));
  }

  async function handleEstimate() {
    if (!values.title.trim()) return;
    setEstimating(true);
    try {
      const res = await estimateTask(values.title, values.description || null);
      set("estimated_minutes", res.estimated_minutes);
    } catch {
      // leave value as-is on failure
    } finally {
      setEstimating(false);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!values.title.trim()) return;
    onSubmit(values);
  }

  return (
    <form className="task-form" onSubmit={handleSubmit}>
      <div className="form-row">
        <label>
          Title
          <input
            type="text"
            value={values.title}
            onChange={(e) => set("title", e.target.value)}
            required
            placeholder="Task title"
          />
        </label>
      </div>
      <div className="form-row">
        <label>
          Description
          <textarea
            value={values.description}
            onChange={(e) => set("description", e.target.value)}
            placeholder="Optional details"
            rows={2}
          />
        </label>
      </div>
      <div className="form-row form-row-inline">
        <label>
          Priority
          <select
            value={values.priority}
            onChange={(e) => set("priority", e.target.value as Priority)}
          >
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </label>
        <label>
          Estimated minutes
          <div className="estimate-row">
            <input
              type="number"
              min={5}
              step={5}
              value={values.estimated_minutes}
              onChange={(e) => set("estimated_minutes", Number(e.target.value))}
            />
            <button
              type="button"
              className="btn-secondary btn-small"
              onClick={handleEstimate}
              disabled={estimating || !values.title.trim()}
            >
              {estimating ? "Estimating…" : "Estimate with AI"}
            </button>
          </div>
        </label>
        <label>
          Due date
          <input
            type="date"
            value={values.due_date}
            onChange={(e) => set("due_date", e.target.value)}
          />
        </label>
      </div>
      <div className="form-actions">
        <button type="submit" className="btn-primary">
          {submitLabel}
        </button>
        {onCancel && (
          <button type="button" className="btn-secondary" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}
