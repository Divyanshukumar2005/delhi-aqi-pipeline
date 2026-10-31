/**
 * Monitors sometimes go quiet for hours or days (sensor downtime, a missed pipeline run).
 * Instead of leaving a hole, charts keep the real data solid and draw the missing stretch as a
 * dashed straight line between the last reading before it and the first reading after it.
 */
export const HOUR = 3600000;
export const GAP_MS = 3 * HOUR;

type Row = Record<string, number | null | undefined> & { t: number };
export interface Bridge { dataKey: string; of: string }

const isNum = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);

/**
 * For every key, finds stretches longer than `gapMs` between two real values and
 *  - adds a `<key>~<n>` field on the two boundary rows, so a dashed <Line connectNulls> can join them,
 *  - makes sure the solid line is cut inside the stretch (inserts a blank row if no row sits there).
 */
export function bridgeRows<T extends { t: number }>(input: T[], keys: string[], gapMs = GAP_MS): { rows: Row[]; bridges: Bridge[] } {
  const rows: Row[] = input.map((r) => ({ ...(r as unknown as Row) })).sort((a, b) => a.t - b.t);
  const bridges: Bridge[] = [];
  const inserts: Row[] = [];
  for (const key of keys) {
    let prev = -1;
    let n = 0;
    for (let i = 0; i < rows.length; i++) {
      if (!isNum(rows[i][key])) continue;
      if (prev !== -1 && rows[i].t - rows[prev].t > gapMs) {
        const name = `${key}~${n++}`;
        rows[prev][name] = rows[prev][key];
        rows[i][name] = rows[i][key];
        bridges.push({ dataKey: name, of: key });
        if (i === prev + 1) inserts.push({ t: rows[prev].t + HOUR });
      }
      prev = i;
    }
  }
  return { rows: [...rows, ...inserts].sort((a, b) => a.t - b.t), bridges };
}
