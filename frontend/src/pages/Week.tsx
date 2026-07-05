import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getWeekSchedule, runSchedule } from "../api/client";
import type { ScheduleRunResult } from "../api/types";
import TimeBlockGrid from "../components/TimeBlockGrid";
import PriorityBadge from "../components/PriorityBadge";
import { startOfWeek, todayISODate } from "../utils/date";

export default function Week() {
  const start = startOfWeek(todayISODate());
  const queryClient = useQueryClient();
  const [runResult, setRunResult] = useState<ScheduleRunResult | null>(null);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["weekSchedule", start],
    queryFn: () => getWeekSchedule(start),
  });

  const runMutation = useMutation({
    mutationFn: () => runSchedule("week", start),
    onSuccess: (res) => {
      setRunResult(res);
      queryClient.invalidateQueries({ queryKey: ["weekSchedule"] });
      queryClient.invalidateQueries({ queryKey: ["daySchedule"] });
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });

  return (
    <div className="page week-page">
      <div className="page-header">
        <h1>Week of {start} (Mon–Sun)</h1>
        <div className="page-header-actions">
          <button
            className="btn-primary"
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending}
          >
            {runMutation.isPending ? "Running…" : "Run scheduler (week)"}
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
          <h3>Didn't fit this week</h3>
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

      {isLoading && <p className="inline-status">Loading week schedule…</p>}
      {isError && (
        <p className="inline-status error">
          Couldn't load week: {(error as Error)?.message ?? "backend unreachable"}
        </p>
      )}

      {data && (
        <div className="week-grid">
          {data.days.map((day) => (
            <div className="week-day-column" key={day.date}>
              <div className="week-day-header">
                {new Date(`${day.date}T00:00:00`).toLocaleDateString(undefined, {
                  weekday: "short",
                  month: "numeric",
                  day: "numeric",
                })}
              </div>
              <TimeBlockGrid
                date={day.date}
                workingHours={day.working_hours}
                timeBlocks={day.time_blocks}
                busyBlocks={day.busy_blocks}
                compact
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
