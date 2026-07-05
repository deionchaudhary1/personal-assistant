import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createTask,
  deleteTask,
  getTasks,
  parseTasks,
  updateTask,
} from "../api/client";
import type { Priority, Task, TaskDraft } from "../api/types";
import PriorityBadge from "../components/PriorityBadge";
import TaskForm, { type TaskFormValues } from "../components/TaskForm";

interface DraftRow extends TaskDraft {
  checked: boolean;
}

export default function Tasks() {
  const queryClient = useQueryClient();
  const { data: tasks, isLoading, isError, error } = useQuery({
    queryKey: ["tasks"],
    queryFn: () => getTasks(),
  });

  const [editingId, setEditingId] = useState<number | null>(null);
  const [pasteText, setPasteText] = useState("");
  const [drafts, setDrafts] = useState<DraftRow[] | null>(null);

  function invalidateTasks() {
    queryClient.invalidateQueries({ queryKey: ["tasks"] });
  }

  const createMutation = useMutation({
    mutationFn: (values: TaskFormValues) =>
      createTask({
        title: values.title,
        description: values.description || null,
        priority: values.priority,
        estimated_minutes: values.estimated_minutes,
        due_date: values.due_date || null,
      }),
    onSuccess: invalidateTasks,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, values }: { id: number; values: TaskFormValues }) =>
      updateTask(id, {
        title: values.title,
        description: values.description || null,
        priority: values.priority,
        estimated_minutes: values.estimated_minutes,
        due_date: values.due_date || null,
      }),
    onSuccess: () => {
      invalidateTasks();
      setEditingId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteTask(id),
    onSuccess: invalidateTasks,
  });

  const parseMutation = useMutation({
    mutationFn: (text: string) => parseTasks(text),
    onSuccess: (res) => {
      setDrafts(res.drafts.map((d) => ({ ...d, checked: true })));
    },
  });

  const addDraftsMutation = useMutation({
    mutationFn: async (rows: DraftRow[]) => {
      for (const row of rows) {
        await createTask({
          title: row.title,
          description: row.description,
          priority: row.priority,
          estimated_minutes: row.estimated_minutes,
          due_date: row.due_date,
          source: "llm_parsed",
        });
      }
    },
    onSuccess: () => {
      invalidateTasks();
      setDrafts(null);
      setPasteText("");
    },
  });

  function handleParse(e: React.FormEvent) {
    e.preventDefault();
    if (!pasteText.trim()) return;
    parseMutation.mutate(pasteText);
  }

  function updateDraft(idx: number, patch: Partial<DraftRow>) {
    setDrafts((ds) =>
      ds ? ds.map((d, i) => (i === idx ? { ...d, ...patch } : d)) : ds
    );
  }

  const checkedCount = drafts?.filter((d) => d.checked).length ?? 0;

  return (
    <div className="page tasks-page">
      <div className="page-header">
        <h1>Tasks</h1>
      </div>

      <section className="card">
        <h2>New task</h2>
        <TaskForm
          submitLabel="Add task"
          onSubmit={(values) => createMutation.mutate(values)}
        />
        {createMutation.isError && (
          <p className="inline-status error">
            {(createMutation.error as Error)?.message ?? "Failed to add task"}
          </p>
        )}
      </section>

      <section className="card">
        <h2>All tasks</h2>
        {isLoading && <p className="inline-status">Loading tasks…</p>}
        {isError && (
          <p className="inline-status error">
            Couldn't load tasks: {(error as Error)?.message ?? "backend unreachable"}
          </p>
        )}
        {tasks && tasks.length === 0 && (
          <p className="empty-state">No tasks yet — add one above.</p>
        )}
        {tasks && tasks.length > 0 && (
          <table className="tasks-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Priority</th>
                <th>Est. min</th>
                <th>Due</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((t) => (
                <TaskRow
                  key={t.id}
                  task={t}
                  isEditing={editingId === t.id}
                  onEdit={() => setEditingId(t.id)}
                  onCancelEdit={() => setEditingId(null)}
                  onSave={(values) => updateMutation.mutate({ id: t.id, values })}
                  onDelete={() => {
                    if (window.confirm(`Delete task "${t.title}"?`)) {
                      deleteMutation.mutate(t.id);
                    }
                  }}
                />
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="card">
        <h2>Paste to-do list</h2>
        <form onSubmit={handleParse}>
          <textarea
            rows={6}
            placeholder={"Paste a messy to-do list, one item per line…"}
            value={pasteText}
            onChange={(e) => setPasteText(e.target.value)}
          />
          <div className="form-actions">
            <button
              type="submit"
              className="btn-primary"
              disabled={parseMutation.isPending || !pasteText.trim()}
            >
              {parseMutation.isPending ? "Asking local AI…" : "Parse with AI"}
            </button>
          </div>
        </form>
        {parseMutation.isError && (
          <p className="inline-status error">
            {(parseMutation.error as Error)?.message ?? "Failed to parse text"}
          </p>
        )}

        {drafts && drafts.length === 0 && (
          <p className="empty-state">No tasks found in that text.</p>
        )}

        {drafts && drafts.length > 0 && (
          <div className="drafts-panel">
            <table className="tasks-table">
              <thead>
                <tr>
                  <th></th>
                  <th>Title</th>
                  <th>Description</th>
                  <th>Priority</th>
                  <th>Est. min</th>
                  <th>Due</th>
                </tr>
              </thead>
              <tbody>
                {drafts.map((d, idx) => (
                  <tr key={idx}>
                    <td>
                      <input
                        type="checkbox"
                        checked={d.checked}
                        onChange={(e) => updateDraft(idx, { checked: e.target.checked })}
                      />
                    </td>
                    <td>
                      <input
                        type="text"
                        value={d.title}
                        onChange={(e) => updateDraft(idx, { title: e.target.value })}
                      />
                    </td>
                    <td>
                      <input
                        type="text"
                        value={d.description ?? ""}
                        onChange={(e) =>
                          updateDraft(idx, { description: e.target.value || null })
                        }
                      />
                    </td>
                    <td>
                      <select
                        value={d.priority}
                        onChange={(e) =>
                          updateDraft(idx, { priority: e.target.value as Priority })
                        }
                      >
                        <option value="high">High</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                      </select>
                    </td>
                    <td>
                      <input
                        type="number"
                        min={5}
                        step={5}
                        value={d.estimated_minutes}
                        onChange={(e) =>
                          updateDraft(idx, { estimated_minutes: Number(e.target.value) })
                        }
                      />
                    </td>
                    <td>
                      <input
                        type="date"
                        value={d.due_date ?? ""}
                        onChange={(e) =>
                          updateDraft(idx, { due_date: e.target.value || null })
                        }
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="form-actions">
              <button
                className="btn-primary"
                disabled={checkedCount === 0 || addDraftsMutation.isPending}
                onClick={() =>
                  addDraftsMutation.mutate(drafts.filter((d) => d.checked))
                }
              >
                {addDraftsMutation.isPending
                  ? "Adding…"
                  : `Add ${checkedCount} task${checkedCount === 1 ? "" : "s"}`}
              </button>
              <button className="btn-secondary" onClick={() => setDrafts(null)}>
                Discard
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

function TaskRow({
  task,
  isEditing,
  onEdit,
  onCancelEdit,
  onSave,
  onDelete,
}: {
  task: Task;
  isEditing: boolean;
  onEdit: () => void;
  onCancelEdit: () => void;
  onSave: (values: TaskFormValues) => void;
  onDelete: () => void;
}) {
  if (isEditing) {
    return (
      <tr>
        <td colSpan={6}>
          <TaskForm
            submitLabel="Save"
            initial={{
              title: task.title,
              description: task.description ?? "",
              priority: task.priority,
              estimated_minutes: task.estimated_minutes,
              due_date: task.due_date ?? "",
            }}
            onSubmit={onSave}
            onCancel={onCancelEdit}
          />
        </td>
      </tr>
    );
  }
  return (
    <tr>
      <td>{task.title}</td>
      <td>
        <PriorityBadge priority={task.priority} />
      </td>
      <td>{task.estimated_minutes}</td>
      <td>{task.due_date ?? "—"}</td>
      <td>
        <span className={`status-chip status-${task.status}`}>{task.status}</span>
      </td>
      <td className="row-actions">
        <button className="btn-small btn-secondary" onClick={onEdit}>
          Edit
        </button>
        <button className="btn-small btn-danger" onClick={onDelete}>
          Delete
        </button>
      </td>
    </tr>
  );
}
