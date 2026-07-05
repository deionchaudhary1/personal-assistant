import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { endOfDay, getDaySchedule } from "../api/client";
import type { ScheduleRunResult } from "../api/types";
import { formatTime } from "../utils/date";

export default function EndOfDayReview({
  date,
  onClose,
}: {
  date: string;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["daySchedule", date],
    queryFn: () => getDaySchedule(date),
  });

  const [checked, setChecked] = useState<Record<number, boolean>>({});
  const [result, setResult] = useState<ScheduleRunResult | null>(null);

  // Initialize checked state once data arrives, pre-checking already-done blocks.
  const initializedRef = useRef(false);
  if (data && !initializedRef.current) {
    initializedRef.current = true;
    const initial: Record<number, boolean> = {};
    for (const tb of data.time_blocks) {
      initial[tb.task_id] = tb.status === "done";
    }
    setChecked(initial);
  }

  const finishMutation = useMutation({
    mutationFn: () =>
      endOfDay(
        Object.entries(checked)
          .filter(([, v]) => v)
          .map(([k]) => Number(k)),
        date
      ),
    onSuccess: (res) => {
      setResult(res);
      queryClient.invalidateQueries({ queryKey: ["daySchedule"] });
      queryClient.invalidateQueries({ queryKey: ["weekSchedule"] });
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });

  function toggle(taskId: number) {
    setChecked((c) => ({ ...c, [taskId]: !c[taskId] }));
  }

  if (result) {
    const completed = result.days
      .flatMap((d) => d.time_blocks)
      .filter((tb) => tb.status === "done").length;
    const rolled = result.unplaceable.length;
    return (
      <div className="modal-backdrop" onClick={onClose}>
        <div className="modal" onClick={(e) => e.stopPropagation()}>
          <h2>Day complete</h2>
          <p>
            {completed} completed, {rolled} rolled forward to tomorrow.
          </p>
          <div className="form-actions">
            <button className="btn-primary" onClick={onClose}>
              Close
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>End of Day Review — {date}</h2>
        {isLoading && <p className="inline-status">Loading today's schedule…</p>}
        {isError && (
          <p className="inline-status error">
            Couldn't load schedule: {(error as Error)?.message ?? "unknown error"}
          </p>
        )}
        {data && data.time_blocks.length === 0 && (
          <p className="empty-state">No time blocks scheduled today.</p>
        )}
        {data && data.time_blocks.length > 0 && (
          <ul className="review-list">
            {data.time_blocks.map((tb) => (
              <li key={tb.id}>
                <label>
                  <input
                    type="checkbox"
                    checked={!!checked[tb.task_id]}
                    onChange={() => toggle(tb.task_id)}
                  />
                  {tb.task_title}{" "}
                  <span className="muted">
                    ({formatTime(tb.start_time)}–{formatTime(tb.end_time)})
                  </span>
                </label>
              </li>
            ))}
          </ul>
        )}
        {finishMutation.isError && (
          <p className="inline-status error">
            {(finishMutation.error as Error)?.message ?? "Failed to finish day"}
          </p>
        )}
        <div className="form-actions">
          <button
            className="btn-primary"
            onClick={() => finishMutation.mutate()}
            disabled={finishMutation.isPending || isLoading}
          >
            {finishMutation.isPending ? "Finishing…" : "Finish day"}
          </button>
          <button className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
