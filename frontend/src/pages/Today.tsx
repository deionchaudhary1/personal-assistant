import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createBusyBlock,
  deleteBusyBlock,
  getDaySchedule,
  patchBlock,
  runSchedule,
} from "../api/client";
import type { ScheduleRunResult } from "../api/types";
import TimeBlockGrid from "../components/TimeBlockGrid";
import EndOfDayReview from "../components/EndOfDayReview";
import PriorityBadge from "../components/PriorityBadge";
import { formatDateHeader, todayISODate } from "../utils/date";

export default function Today() {
  const date = todayISODate();
  const queryClient = useQueryClient();
  const [showReview, setShowReview] = useState(false);
  const [runResult, setRunResult] = useState<ScheduleRunResult | null>(null);
  const [busyForm, setBusyForm] = useState({ title: "", start: "", end: "" });

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["daySchedule", date],
    queryFn: () => getDaySchedule(date),
  });

  function invalidateAll() {
    queryClient.invalidateQueries({ queryKey: ["daySchedule"] });
    queryClient.invalidateQueries({ queryKey: ["weekSchedule"] });
    queryClient.invalidateQueries({ queryKey: ["tasks"] });
  }

  const runMutation = useMutation({
    mutationFn: () => runSchedule("day", date),
    onSuccess: (res) => {
      setRunResult(res);
      invalidateAll();
    },
  });

  const patchMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: "done" | "skipped" }) =>
      patchBlock(id, status),
    onSuccess: invalidateAll,
  });

  const addBusyMutation = useMutation({
    mutationFn: () =>
      createBusyBlock({
        title: busyForm.title,
        start_time: `${date}T${busyForm.start}:00`,
        end_time: `${date}T${busyForm.end}:00`,
      }),
    onSuccess: () => {
      setBusyForm({ title: "", start: "", end: "" });
      invalidateAll();
    },
  });

  const deleteBusyMutation = useMutation({
    mutationFn: (id: number) => deleteBusyBlock(id),
    onSuccess: invalidateAll,
  });

  function handleAddBusy(e: React.FormEvent) {
    e.preventDefault();
    if (!busyForm.title.trim() || !busyForm.start || !busyForm.end) return;
    addBusyMutation.mutate();
  }

  return (
    <div className="page today-page">
      <div className="page-header">
        <h1>{formatDateHeader(date)}</h1>
        <div className="page-header-actions">
          <button
            className="btn-primary"
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending}
          >
            {runMutation.isPending ? "Running…" : "Run scheduler (day)"}
          </button>
          <button className="btn-secondary" onClick={() => setShowReview(true)}>
            End of Day Review
          </button>
        </div>
      </div>

      {runMutation.isError && (
        <p className="inline-status error">
          {(runMutation.error as Error)?.message ?? "Failed to run scheduler"}
        </p>
      )}

      {runResult && runResult.unplaceable.length > 0 && (
        <div className="unplaceable-panel">
          <h3>Didn't fit today</h3>
          <ul>
            {runResult.unplaceable.map((t) => (
              <li key={t.id}>
                <span>{t.title}</span>
                <PriorityBadge priority={t.priority} />
                <span className="muted">{t.estimated_minutes} min</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {isLoading && <p className="inline-status">Loading today's schedule…</p>}
      {isError && (
        <p className="inline-status error">
          Couldn't load schedule: {(error as Error)?.message ?? "backend unreachable"}
        </p>
      )}

      {data && (
        <TimeBlockGrid
          date={date}
          workingHours={data.working_hours}
          timeBlocks={data.time_blocks}
          busyBlocks={data.busy_blocks}
          onDone={(id) => patchMutation.mutate({ id, status: "done" })}
          onSkip={(id) => patchMutation.mutate({ id, status: "skipped" })}
          onDeleteBusy={(id) => deleteBusyMutation.mutate(id)}
        />
      )}

      <div className="add-busy-form">
        <h3>Add busy block</h3>
        <form onSubmit={handleAddBusy} className="inline-form">
          <input
            type="text"
            placeholder="Title"
            value={busyForm.title}
            onChange={(e) => setBusyForm((f) => ({ ...f, title: e.target.value }))}
            required
          />
          <input
            type="time"
            value={busyForm.start}
            onChange={(e) => setBusyForm((f) => ({ ...f, start: e.target.value }))}
            required
          />
          <span className="muted">to</span>
          <input
            type="time"
            value={busyForm.end}
            onChange={(e) => setBusyForm((f) => ({ ...f, end: e.target.value }))}
            required
          />
          <button type="submit" className="btn-secondary" disabled={addBusyMutation.isPending}>
            Add
          </button>
        </form>
        {addBusyMutation.isError && (
          <p className="inline-status error">
            {(addBusyMutation.error as Error)?.message ?? "Failed to add busy block"}
          </p>
        )}
      </div>

      {showReview && (
        <EndOfDayReview date={date} onClose={() => setShowReview(false)} />
      )}
    </div>
  );
}
