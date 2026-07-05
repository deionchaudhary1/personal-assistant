// Small naive-local-time date helpers. No timezone conversions — the backend
// works entirely in naive local datetimes, so we just format/parse strings directly.

export function todayISODate(): string {
  const d = new Date();
  return toISODate(d);
}

export function toISODate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function addDays(dateStr: string, days: number): string {
  const [y, m, d] = dateStr.split("-").map(Number);
  const dt = new Date(y, m - 1, d);
  dt.setDate(dt.getDate() + days);
  return toISODate(dt);
}

export function startOfWeek(dateStr: string): string {
  // Monday-start week containing dateStr.
  const [y, m, d] = dateStr.split("-").map(Number);
  const dt = new Date(y, m - 1, d);
  const dow = (dt.getDay() + 6) % 7; // 0=Monday
  dt.setDate(dt.getDate() - dow);
  return toISODate(dt);
}

// Format an ISO datetime string ("2026-07-04T09:30:00") as "9:30 AM"
export function formatTime(iso: string): string {
  const timePart = iso.split("T")[1] ?? iso;
  const [hStr, mStr] = timePart.split(":");
  let h = parseInt(hStr, 10);
  const m = mStr ?? "00";
  const suffix = h >= 12 ? "PM" : "AM";
  h = h % 12;
  if (h === 0) h = 12;
  return `${h}:${m} ${suffix}`;
}

// Format an HH:MM string as "9:30 AM"
export function formatHHMM(hhmm: string): string {
  return formatTime(`T${hhmm}`);
}

// Minutes since midnight for an ISO datetime string.
export function minutesOfDay(iso: string): number {
  const timePart = iso.split("T")[1] ?? iso;
  const [hStr, mStr] = timePart.split(":");
  return parseInt(hStr, 10) * 60 + parseInt(mStr, 10);
}

export function minutesOfDayFromHHMM(hhmm: string): number {
  const [hStr, mStr] = hhmm.split(":");
  return parseInt(hStr, 10) * 60 + parseInt(mStr, 10);
}

export function formatDateHeader(dateStr: string): string {
  const [y, m, d] = dateStr.split("-").map(Number);
  const dt = new Date(y, m - 1, d);
  return dt.toLocaleDateString(undefined, {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export const WEEKDAY_LABELS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];
