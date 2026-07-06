import { useState } from "react";
import type { Priority } from "../api/types";

export interface TaskFormValues {
  title: string;
  description: string;
  priority: Priority;
  due_date: string;
}

const EMPTY: TaskFormValues = {
  title: "",
  description: "",
  priority: "medium",
  due_date: "",
};

export default function TaskForm({
  initial,
  submitLabel = "new task",
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

  function set<K extends keyof TaskFormValues>(key: K, val: TaskFormValues[K]) {
    setValues((v) => ({ ...v, [key]: val }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!values.title.trim()) return;
    onSubmit(values);
    setValues(EMPTY);
  }

  return (
    <form className="task-form" onSubmit={handleSubmit}>
      <div className="form-row">
        <label className="prompt-label" htmlFor="task-title">
          &gt; title
        </label>
        <input
          id="task-title"
          className="prompt-input"
          type="text"
          value={values.title}
          onChange={(e) => set("title", e.target.value)}
          required
        />
      </div>
      <div className="form-row">
        <label className="prompt-label" htmlFor="task-description">
          &gt; description
        </label>
        <textarea
          id="task-description"
          value={values.description}
          onChange={(e) => set("description", e.target.value)}
          rows={2}
        />
      </div>
      <div className="form-row form-row-inline">
        <label className="prompt-label" htmlFor="task-priority">
          &gt; priority
          <select
            id="task-priority"
            value={values.priority}
            onChange={(e) => set("priority", e.target.value as Priority)}
          >
            <option value="high">high</option>
            <option value="medium">medium</option>
            <option value="low">low</option>
          </select>
        </label>
        <label className="prompt-label" htmlFor="task-due-date">
          &gt; due
          <input
            id="task-due-date"
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
            cancel
          </button>
        )}
      </div>
    </form>
  );
}
