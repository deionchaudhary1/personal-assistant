import { useEffect, useState } from "react";
import type { BusyBlock, TimeBlock, WorkingHoursDay } from "../api/types";
import { formatTime, minutesOfDay, minutesOfDayFromHHMM, todayISODate } from "../utils/date";

const FALLBACK_START = "08:00";
const FALLBACK_END = "18:00";
const PX_PER_MIN_FULL = 1.1;
const PX_PER_MIN_COMPACT = 0.55;

interface TimeBlockGridProps {
  date: string;
  workingHours: WorkingHoursDay | null | undefined;
  timeBlocks: TimeBlock[];
  busyBlocks: BusyBlock[];
  compact?: boolean;
  onDone?: (blockId: number) => void;
  onSkip?: (blockId: number) => void;
  onDeleteBusy?: (busyBlockId: number) => void;
}

export default function TimeBlockGrid({
  date,
  workingHours,
  timeBlocks,
  busyBlocks,
  compact = false,
  onDone,
  onSkip,
  onDeleteBusy,
}: TimeBlockGridProps) {
  const enabled = workingHours?.enabled ?? false;
  const startHHMM = enabled ? workingHours!.start : FALLBACK_START;
  const endHHMM = enabled ? workingHours!.end : FALLBACK_END;
  const startMin = minutesOfDayFromHHMM(startHHMM);
  const endMin = minutesOfDayFromHHMM(endHHMM);
  const totalMin = Math.max(endMin - startMin, 60);
  const pxPerMin = compact ? PX_PER_MIN_COMPACT : PX_PER_MIN_FULL;
  const heightPx = totalMin * pxPerMin;

  const isToday = date === todayISODate();
  const [nowMin, setNowMin] = useState<number | null>(
    isToday ? minutesOfDay(new Date().toISOString()) : null
  );

  useEffect(() => {
    if (!isToday) {
      setNowMin(null);
      return;
    }
    function update() {
      const now = new Date();
      setNowMin(now.getHours() * 60 + now.getMinutes());
    }
    update();
    const id = setInterval(update, 60000);
    return () => clearInterval(id);
  }, [isToday]);

  function topFor(minutes: number): number {
    return (Math.max(minutes, startMin) - startMin) * pxPerMin;
  }
  function heightFor(startMinutes: number, endMinutes: number): number {
    const clampedStart = Math.max(startMinutes, startMin);
    const clampedEnd = Math.min(endMinutes, endMin);
    return Math.max(clampedEnd - clampedStart, 0) * pxPerMin;
  }

  // Hour gridlines
  const hourMarks: number[] = [];
  for (let m = Math.ceil(startMin / 60) * 60; m <= endMin; m += 60) {
    hourMarks.push(m);
  }

  if (!enabled && !workingHours) {
    // no working hours info yet — still render fallback grid, just note it
  }

  return (
    <div className={`time-block-grid ${compact ? "compact" : ""}`}>
      {!enabled && (
        <div className="grid-note">
          Day off / no working hours set — showing {startHHMM}–{endHHMM} as fallback.
        </div>
      )}
      <div className="grid-body" style={{ height: `${heightPx}px` }}>
        {hourMarks.map((m) => (
          <div
            key={m}
            className="hour-line"
            style={{ top: `${topFor(m)}px` }}
          >
            {!compact && (
              <span className="hour-label">
                {formatTime(`T${String(Math.floor(m / 60)).padStart(2, "0")}:00`)}
              </span>
            )}
          </div>
        ))}

        {busyBlocks.map((b) => {
          const bs = minutesOfDay(b.start_time);
          const be = minutesOfDay(b.end_time);
          if (be <= startMin || bs >= endMin) return null;
          return (
            <div
              key={`busy-${b.id}`}
              className="grid-block busy-block"
              style={{ top: `${topFor(bs)}px`, height: `${heightFor(bs, be)}px` }}
              title={b.title}
            >
              <div className="block-title">{b.title}</div>
              {!compact && (
                <div className="block-meta">
                  <span className="source-tag">{b.source === "gcal" ? "calendar" : "manual"}</span>
                  {b.source === "manual" && onDeleteBusy && (
                    <button
                      className="btn-x"
                      aria-label="Delete busy block"
                      onClick={() => onDeleteBusy(b.id)}
                    >
                      ×
                    </button>
                  )}
                </div>
              )}
            </div>
          );
        })}

        {timeBlocks.map((tb) => {
          const bs = minutesOfDay(tb.start_time);
          const be = minutesOfDay(tb.end_time);
          if (be <= startMin || bs >= endMin) return null;
          return (
            <div
              key={`tb-${tb.id}`}
              className={`grid-block time-block priority-border-${tb.task_priority} status-${tb.status}`}
              style={{ top: `${topFor(bs)}px`, height: `${heightFor(bs, be)}px` }}
            >
              <div className="block-title">{tb.task_title}</div>
              <div className="block-meta">
                <span className="block-time">
                  {formatTime(tb.start_time)}–{formatTime(tb.end_time)}
                </span>
                <span className={`status-chip status-${tb.status}`}>{tb.status}</span>
              </div>
              {!compact && (onDone || onSkip) && tb.status === "planned" && (
                <div className="block-actions">
                  {onDone && (
                    <button className="btn-small btn-secondary" onClick={() => onDone(tb.id)}>
                      Done
                    </button>
                  )}
                  {onSkip && (
                    <button className="btn-small btn-secondary" onClick={() => onSkip(tb.id)}>
                      Skip
                    </button>
                  )}
                </div>
              )}
            </div>
          );
        })}

        {nowMin !== null && nowMin >= startMin && nowMin <= endMin && (
          <div className="now-line" style={{ top: `${topFor(nowMin)}px` }} />
        )}
      </div>
    </div>
  );
}
