import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getWorkingHours,
  putWorkingHours,
  getCalendarStatus,
  getCalendarAuthUrl,
  syncCalendar,
} from "../api/client";
import type { WorkingHoursDay } from "../api/types";
import { WEEKDAY_LABELS } from "../utils/date";

export default function Settings() {
  const queryClient = useQueryClient();

  // ---- Working hours ----

  const {
    data: workingHours,
    isLoading: whLoading,
    isError: whIsError,
    error: whError,
  } = useQuery({
    queryKey: ["workingHours"],
    queryFn: getWorkingHours,
  });

  const [days, setDays] = useState<WorkingHoursDay[] | null>(null);
  const initializedRef = useRef(false);
  if (workingHours && !initializedRef.current) {
    initializedRef.current = true;
    setDays(workingHours);
  }

  const saveMutation = useMutation({
    mutationFn: (body: WorkingHoursDay[]) => putWorkingHours(body),
    onSuccess: (res) => {
      setDays(res);
      queryClient.invalidateQueries({ queryKey: ["workingHours"] });
    },
  });

  function updateDay(idx: number, patch: Partial<WorkingHoursDay>) {
    setDays((ds) =>
      ds ? ds.map((d, i) => (i === idx ? { ...d, ...patch } : d)) : ds
    );
  }

  function handleSave() {
    if (!days) return;
    saveMutation.mutate(days);
  }

  // ---- Google Calendar ----

  const {
    data: calStatus,
    isLoading: calLoading,
    isError: calIsError,
    error: calError,
  } = useQuery({
    queryKey: ["calendarStatus"],
    queryFn: getCalendarStatus,
  });

  const [connectError, setConnectError] = useState<string | null>(null);

  const connectMutation = useMutation({
    mutationFn: () => getCalendarAuthUrl(),
    onSuccess: (res) => {
      window.open(res.url, "_blank");
    },
    onError: (err) => {
      setConnectError((err as Error)?.message ?? "Failed to get auth URL");
    },
  });

  const syncMutation = useMutation({
    mutationFn: () => syncCalendar(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["calendarStatus"] });
    },
  });

  return (
    <div className="page settings-page">
      <div className="page-header">
        <h1>Settings</h1>
      </div>

      <section className="card">
        <h2>Working hours</h2>
        {whLoading && <p className="inline-status">Loading working hours…</p>}
        {whIsError && (
          <p className="inline-status error">
            Couldn't load working hours:{" "}
            {(whError as Error)?.message ?? "backend unreachable"}
          </p>
        )}
        {days && (
          <>
            <table className="tasks-table working-hours-table">
              <thead>
                <tr>
                  <th>Enabled</th>
                  <th>Day</th>
                  <th>Start</th>
                  <th>End</th>
                </tr>
              </thead>
              <tbody>
                {days.map((d, idx) => (
                  <tr key={d.day_of_week}>
                    <td>
                      <input
                        type="checkbox"
                        checked={d.enabled}
                        onChange={(e) =>
                          updateDay(idx, { enabled: e.target.checked })
                        }
                      />
                    </td>
                    <td>{WEEKDAY_LABELS[d.day_of_week]}</td>
                    <td>
                      <input
                        type="time"
                        value={d.start}
                        disabled={!d.enabled}
                        onChange={(e) =>
                          updateDay(idx, { start: e.target.value })
                        }
                      />
                    </td>
                    <td>
                      <input
                        type="time"
                        value={d.end}
                        disabled={!d.enabled}
                        onChange={(e) => updateDay(idx, { end: e.target.value })}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="form-actions">
              <button
                className="btn-primary"
                onClick={handleSave}
                disabled={saveMutation.isPending}
              >
                {saveMutation.isPending ? "Saving…" : "Save"}
              </button>
              {saveMutation.isSuccess && (
                <span className="inline-status">Saved.</span>
              )}
            </div>
            {saveMutation.isError && (
              <p className="inline-status error">
                {(saveMutation.error as Error)?.message ??
                  "Failed to save working hours"}
              </p>
            )}
          </>
        )}
      </section>

      <section className="card">
        <h2>Google Calendar</h2>
        {calLoading && <p className="inline-status">Loading calendar status…</p>}
        {calIsError && (
          <p className="inline-status error">
            Couldn't load calendar status:{" "}
            {(calError as Error)?.message ?? "backend unreachable"}
          </p>
        )}
        {calStatus && !calStatus.configured && (
          <p className="hint">
            Not configured — place <code>credentials.json</code> in{" "}
            <code>backend/</code> (see README) to enable Google Calendar sync.
          </p>
        )}
        {calStatus && calStatus.configured && !calStatus.connected && (
          <div className="form-actions">
            <button
              className="btn-primary"
              onClick={() => {
                setConnectError(null);
                connectMutation.mutate();
              }}
              disabled={connectMutation.isPending}
            >
              {connectMutation.isPending ? "Connecting…" : "Connect"}
            </button>
          </div>
        )}
        {connectError && <p className="inline-status error">{connectError}</p>}
        {calStatus && calStatus.connected && (
          <>
            <p className="muted">
              Last synced:{" "}
              {calStatus.last_synced_at ? calStatus.last_synced_at : "never"}
            </p>
            <div className="form-actions">
              <button
                className="btn-secondary"
                onClick={() => syncMutation.mutate()}
                disabled={syncMutation.isPending}
              >
                {syncMutation.isPending ? "Syncing…" : "Sync now"}
              </button>
              {syncMutation.isSuccess && (
                <span className="inline-status">
                  Synced {syncMutation.data?.synced ?? 0} events.
                </span>
              )}
            </div>
            {syncMutation.isError && (
              <p className="inline-status error">
                {(syncMutation.error as Error)?.message ??
                  "Failed to sync calendar"}
              </p>
            )}
          </>
        )}
      </section>
    </div>
  );
}
