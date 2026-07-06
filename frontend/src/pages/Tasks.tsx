import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createTask, deleteTask, getTasks, parseTasks, updateTask } from "../api/client";
import type { Priority, Task, TaskDraft } from "../api/types";
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
        due_date: values.due_date || null,
      }),
    onSuccess: invalidateTasks,
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, done }: { id: number; done: boolean }) =>
      updateTask(id, { status: done ? "completed" : "pending" }),
    onSuccess: invalidateTasks,
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
      <section className="card">
        <h2>&gt; new_task</h2>
        <TaskForm
          submitLabel="add"
          onSubmit={(values) => createMutation.mutate(values)}
        />
        {createMutation.isError && (
          <p className="inline-status error">
            {(createMutation.error as Error)?.message ?? "failed to add task"}
          </p>
        )}
      </section>

      <section className="card">
        <h2>&gt; tasks</h2>
        {isLoading && <p className="inline-status">loading tasks…</p>}
        {isError && (
          <p className="inline-status error">
            couldn't load tasks: {(error as Error)?.message ?? "backend unreachable"}
          </p>
        )}
        {tasks && tasks.length === 0 && (
          <p className="empty-state">no tasks yet — add one above.</p>
        )}
        {tasks && tasks.length > 0 && (
          <ul className="task-log">
            {tasks.map((t) => (
              <TaskRow
                key={t.id}
                task={t}
                onToggle={(done) => toggleMutation.mutate({ id: t.id, done })}
                onDelete={() => deleteMutation.mutate(t.id)}
              />
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <h2>&gt; paste_list</h2>
        <form onSubmit={handleParse}>
          <label className="prompt-label" htmlFor="paste-textarea">
            &gt; paste a messy to-do list, one item per line
          </label>
          <textarea
            id="paste-textarea"
            rows={6}
            value={pasteText}
            onChange={(e) => setPasteText(e.target.value)}
          />
          <div className="form-actions">
            <button
              type="submit"
              className="btn-primary"
              disabled={parseMutation.isPending || !pasteText.trim()}
            >
              {parseMutation.isPending ? "asking local ai…" : "parse with ai"}
            </button>
          </div>
        </form>
        {parseMutation.isError && (
          <p className="inline-status error">
            {(parseMutation.error as Error)?.message ?? "failed to parse text"}
          </p>
        )}

        {drafts && drafts.length === 0 && (
          <p className="empty-state">no tasks found in that text.</p>
        )}

        {drafts && drafts.length > 0 && (
          <div className="drafts-panel">
            <table className="tasks-table">
              <thead>
                <tr>
                  <th></th>
                  <th>title</th>
                  <th>description</th>
                  <th>priority</th>
                  <th>due</th>
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
                        <option value="high">high</option>
                        <option value="medium">medium</option>
                        <option value="low">low</option>
                      </select>
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
                  ? "adding…"
                  : `add ${checkedCount} task${checkedCount === 1 ? "" : "s"}`}
              </button>
              <button className="btn-secondary" onClick={() => setDrafts(null)}>
                discard
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
  onToggle,
  onDelete,
}: {
  task: Task;
  onToggle: (done: boolean) => void;
  onDelete: () => void;
}) {
  const done = task.status === "completed";
  return (
    <li className={`task-row priority-${task.priority}`}>
      <button
        type="button"
        className="task-checkbox"
        role="checkbox"
        aria-checked={done}
        aria-label={done ? "mark pending" : "mark completed"}
        onClick={() => onToggle(!done)}
      >
        [{done ? "x" : " "}]
      </button>
      <span className={done ? "task-title done" : "task-title"}>{task.title}</span>
      <span className="task-tag">[{task.priority}]</span>
      {task.due_date && <span className="task-due">due {task.due_date}</span>}
      <button
        type="button"
        className="task-rm"
        aria-label={`delete ${task.title}`}
        onClick={onDelete}
      >
        [rm]
      </button>
    </li>
  );
}
