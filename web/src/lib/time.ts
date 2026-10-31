/** All dashboard times are shown in IST (UTC+05:30), regardless of the viewer's timezone. */
const IST_OFFSET = 5.5 * 3600 * 1000;

const shifted = (t: number) => new Date(t + IST_OFFSET);

export const istHour = (t: number) => shifted(t).getUTCHours();
export const istDate = (t: number) => shifted(t).toISOString().slice(0, 10);
export const istDow = (t: number) => shifted(t).getUTCDay(); // 0 = Sunday

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

export function fmtDay(dateStr: string): string {
  const [, m, d] = dateStr.split('-').map(Number);
  return `${d} ${MONTHS[m - 1]}`;
}
export function fmtWeekday(dateStr: string): string {
  return DAYS[new Date(`${dateStr}T00:00:00Z`).getUTCDay()];
}
export const pad2 = (n: number) => n.toString().padStart(2, '0');
export const fmtHour = (h: number) => `${pad2(h)}:00`;
export function fmtStamp(t: number): string {
  const d = shifted(t);
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}, ${pad2(d.getUTCHours())}:${pad2(d.getUTCMinutes())} IST`;
}
export function fmtShort(t: number): string {
  const d = shifted(t);
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${pad2(d.getUTCHours())}:00`;
}
/** Whole days from now (IST) to a calendar date such as "2026-11-08". */
export function daysUntil(dateStr: string, now = Date.now()): number {
  const target = Date.parse(`${dateStr}T00:00:00Z`);
  const today = Date.parse(`${istDate(now)}T00:00:00Z`);
  return Math.round((target - today) / 86400000);
}
