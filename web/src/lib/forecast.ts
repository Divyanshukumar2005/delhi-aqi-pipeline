import { calculateAqi } from './aqi';
import { istHour } from './time';

/**
 * 24-hour AQI outlook.
 *
 * The published CPCB AQI is a 24-hour rolling mean, so the forecast works the same way:
 *   1. forecast hourly PM2.5 and PM10 for the next 24 h,
 *   2. at every future hour average the previous 24 h (observed + forecast),
 *   3. convert that mean to an AQI with the CPCB breakpoints.
 *
 * Hourly concentrations are modelled in log space as
 *      log y(t) = level + daily_cycle[hour(t)] + e(t),     e(t) = phi * e(t-1) + noise
 * - level        : mean of log y over the last 24 h
 * - daily_cycle  : average deviation of log y from its centred 24 h mean, per hour of day
 * - phi, sigma   : AR(1) coefficient and innovation spread of what is left over
 * The 80% band comes from 400 simulated noise paths pushed through the same rolling-mean AQI maths.
 * The generator is seeded, so the chart is identical on every render.
 */

const H = 3600000;
const WIN = 24;
const SIMS = 400;

export interface CityPoint { t: number; pm25: number | null; pm10: number | null }

export interface ForecastPoint { t: number; hour: number; aqi: number; lo: number; hi: number }
export interface BacktestRow { horizon: number; mae: number; baseline: number; skill: number }
export interface Forecast {
  /** Last observed hour the forecast starts from. */
  origin: number;
  /** Observed city AQI over the previous 24 h, for context on the chart. */
  recent: { t: number; aqi: number }[];
  points: ForecastPoint[];
  phi: number;
  sigma: number;
  hoursFitted: number;
  backtest: { origins: number; rows: BacktestRow[] } | null;
}

interface Grid { t: number[]; pm25: (number | null)[]; pm10: (number | null)[] }

function toGrid(pts: CityPoint[]): Grid {
  const sorted = [...pts].sort((a, b) => a.t - b.t);
  const out: Grid = { t: [], pm25: [], pm10: [] };
  if (!sorted.length) return out;
  const byT = new Map(sorted.map((p) => [Math.round(p.t / H), p]));
  const a = Math.round(sorted[0].t / H), b = Math.round(sorted[sorted.length - 1].t / H);
  for (let k = a; k <= b; k++) {
    const p = byT.get(k);
    out.t.push(k * H);
    out.pm25.push(p?.pm25 ?? null);
    out.pm10.push(p?.pm10 ?? null);
  }
  return out;
}

const mean = (v: number[]) => v.reduce((a, b) => a + b, 0) / v.length;
const std = (v: number[]) => { const m = mean(v); return Math.sqrt(v.reduce((a, b) => a + (b - m) ** 2, 0) / Math.max(1, v.length - 1)); };

/** Linear interpolation across holes, nearest value at the edges. */
function fill(v: (number | null)[]): number[] {
  const out = v.map((x) => x as number);
  const idx = v.map((x, i) => (x === null ? -1 : i)).filter((i) => i >= 0);
  if (!idx.length) return v.map(() => 0);
  for (let i = 0; i < v.length; i++) {
    if (v[i] !== null) continue;
    const lo = [...idx].reverse().find((j) => j < i);
    const hi = idx.find((j) => j > i);
    if (lo === undefined) out[i] = v[hi!]!;
    else if (hi === undefined) out[i] = v[lo]!;
    else out[i] = v[lo]! + ((v[hi]! - v[lo]!) * (i - lo)) / (hi - lo);
  }
  return out;
}

/** Observed AQI at index i from the rolling 24 h means (needs >= 16 valid hours per pollutant, as CPCB does). */
function observedAqi(g: Grid, i: number): number | null {
  if (i < WIN - 1) return null;
  const m = (arr: (number | null)[]) => {
    const w = arr.slice(i - WIN + 1, i + 1).filter((x): x is number => x !== null);
    return w.length >= 16 ? mean(w) : null;
  };
  return calculateAqi(m(g.pm25), m(g.pm10));
}

interface Fit { level: number; cycle: number[]; phi: number; sigma: number; e0: number; n: number }

/** Fit using only grid indices <= upto. Returns null if there is too little history. */
function fitSeries(t: number[], v: (number | null)[], upto: number): Fit | null {
  const logs = v.slice(0, upto + 1).map((x) => (x === null || x <= 0 ? null : Math.log(Math.max(x, 1))));
  const n = logs.length;
  // centred 24 h mean of the log series
  const dev: (number | null)[] = new Array(n).fill(null);
  for (let i = 12; i < n - 12; i++) {
    if (logs[i] === null) continue;
    const w = logs.slice(i - 12, i + 13).filter((x): x is number => x !== null);
    if (w.length >= 18) dev[i] = logs[i]! - mean(w);
  }
  const sums = Array.from({ length: 24 }, () => ({ s: 0, n: 0 }));
  dev.forEach((d, i) => { if (d !== null) { const h = istHour(t[i]); sums[h].s += d; sums[h].n++; } });
  if (sums.some((x) => x.n < 3)) return null;
  const raw = sums.map((x) => x.s / x.n);
  const c0 = mean(raw);
  const cycle = raw.map((x) => x - c0);

  // residual after removing the daily cycle, relative to the centred mean
  const e: (number | null)[] = dev.map((d, i) => (d === null ? null : d - cycle[istHour(t[i])]));
  const pairs: [number, number][] = [];
  for (let i = 1; i < n; i++) if (e[i] !== null && e[i - 1] !== null) pairs.push([e[i - 1]!, e[i]!]);
  if (pairs.length < 24) return null;
  const num = pairs.reduce((a, [x, y]) => a + x * y, 0);
  const den = pairs.reduce((a, [x]) => a + x * x, 0);
  const phi = Math.min(0.97, Math.max(0.3, den ? num / den : 0.8));
  const sigma = std(pairs.map(([x, y]) => y - phi * x));

  // state at the origin
  const tail = logs.slice(Math.max(0, n - WIN)).filter((x): x is number => x !== null);
  if (tail.length < 16) return null;
  const level = mean(tail);
  let last = n - 1;
  while (last >= 0 && logs[last] === null) last--;
  if (last < 0 || n - 1 - last > 3) return null;
  const e0 = logs[last]! - level - cycle[istHour(t[last])];
  return { level, cycle, phi, sigma, e0: e0 * Math.pow(phi, n - 1 - last), n: tail.length };
}

function mulberry32(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let x = Math.imul(a ^ (a >>> 15), 1 | a);
    x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x;
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
  };
}
function gauss(rnd: () => number) {
  const u = Math.max(1e-12, rnd()), v = rnd();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

/** Forecast AQI for k = 1..horizon after grid index `o`. `shocks` (standardised) adds noise; omit for the central path. */
function path(g: Grid, o: number, f25: Fit, f10: Fit | null, horizon: number, shocks?: number[]): number[] {
  const h25 = fill(g.pm25.slice(0, o + 1).slice(-WIN));
  const h10 = f10 ? fill(g.pm10.slice(0, o + 1).slice(-WIN)) : null;
  // keep a rolling window of the latest 24 hourly values
  const w25 = [...h25], w10 = h10 ? [...h10] : null;
  let e25 = f25.e0, e10 = f10 ? f10.e0 : 0;
  const out: number[] = [];
  for (let k = 1; k <= horizon; k++) {
    const hour = istHour(g.t[o] + k * H);
    const z = shocks ? shocks[k - 1] : 0;
    e25 = f25.phi * e25 + f25.sigma * z;
    w25.push(Math.exp(f25.level + f25.cycle[hour] + (shocks ? e25 : f25.e0 * Math.pow(f25.phi, k))));
    if (w10 && f10) {
      e10 = f10.phi * e10 + f10.sigma * z;
      w10.push(Math.exp(f10.level + f10.cycle[hour] + (shocks ? e10 : f10.e0 * Math.pow(f10.phi, k))));
    }
    const a = calculateAqi(mean(w25.slice(-WIN)), w10 ? mean(w10.slice(-WIN)) : null);
    out.push(a ?? 0);
  }
  return out;
}

function backtest(g: Grid): Forecast['backtest'] {
  const horizons = [6, 12, 24];
  const err: Record<number, { m: number; b: number }[]> = { 6: [], 12: [], 24: [] };
  let origins = 0;
  for (let o = 24 * 4; o < g.t.length - 6; o += 3) {
    const a0 = observedAqi(g, o);
    if (a0 === null) continue;
    if (g.pm25.slice(o - WIN + 1, o + 1).filter((x) => x !== null).length < 20) continue;
    const f25 = fitSeries(g.t, g.pm25, o);
    if (!f25) continue;
    const f10 = fitSeries(g.t, g.pm10, o);
    const p = path(g, o, f25, f10, 24);
    let used = false;
    for (const h of horizons) {
      if (o + h >= g.t.length) continue;
      const act = observedAqi(g, o + h);
      if (act === null) continue;
      err[h].push({ m: Math.abs(p[h - 1] - act), b: Math.abs(a0 - act) });
      used = true;
    }
    if (used) origins++;
  }
  const rows = horizons
    .filter((h) => err[h].length >= 8)
    .map((h) => {
      const mae = mean(err[h].map((x) => x.m)), baseline = mean(err[h].map((x) => x.b));
      return { horizon: h, mae, baseline, skill: baseline > 0 ? 1 - mae / baseline : 0 };
    });
  return rows.length ? { origins, rows } : null;
}

export function buildForecast(pts: CityPoint[]): Forecast | null {
  const g = toGrid(pts);
  if (g.t.length < 24 * 3) return null;
  // last hour that actually has a city value
  let o = g.t.length - 1;
  while (o > 0 && g.pm25[o] === null) o--;
  const f25 = fitSeries(g.t, g.pm25, o);
  if (!f25) return null;
  const f10 = fitSeries(g.t, g.pm10, o);

  const central = path(g, o, f25, f10, 24);
  const rnd = mulberry32(20261031);
  const sims: number[][] = [];
  for (let s = 0; s < SIMS; s++) sims.push(path(g, o, f25, f10, 24, Array.from({ length: 24 }, () => gauss(rnd))));

  const points: ForecastPoint[] = central.map((aqi, i) => {
    const col = sims.map((s) => s[i]).sort((a, b) => a - b);
    const q = (p: number) => col[Math.min(col.length - 1, Math.max(0, Math.round(p * (col.length - 1))))];
    const t = g.t[o] + (i + 1) * H;
    return { t, hour: istHour(t), aqi: Math.round(aqi), lo: Math.round(Math.min(q(0.1), aqi)), hi: Math.round(Math.max(q(0.9), aqi)) };
  });

  const recent: { t: number; aqi: number }[] = [];
  for (let i = Math.max(WIN - 1, o - WIN + 1); i <= o; i++) {
    const a = observedAqi(g, i);
    if (a !== null) recent.push({ t: g.t[i], aqi: a });
  }
  return { origin: g.t[o], recent, points, phi: f25.phi, sigma: f25.sigma, hoursFitted: f25.n, backtest: backtest(g) };
}

