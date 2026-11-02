import { calculateAqi, categoryOf, POOR_OR_WORSE, type Category } from './aqi';
import { istDate, istHour } from './time';

export type Area = 'Delhi' | 'Gurugram' | 'Noida' | 'Faridabad' | 'Bahadurgarh';
export const AREAS: Area[] = ['Delhi', 'Gurugram', 'Noida', 'Faridabad', 'Bahadurgarh'];

interface RawReading {
  station_id: string;
  station: string;
  ts: string;
  pm25: number | string | null;
  pm10: number | string | null;
  no2: number | string | null;
  o3: number | string | null;
  source: string;
}
interface RawStation { id: number | string; name: string; lat: number; lon: number }

export interface Reading {
  sid: string;
  t: number;
  date: string;
  hour: number;
  pm25: number | null;
  pm10: number | null;
  no2: number | null;
  o3: number | null;
  aqi: number | null;
  cat: Category;
}

export interface Station {
  id: string;
  name: string;
  short: string;
  agency: string;
  area: Area;
  lat: number | null;
  lon: number | null;
  readings: Reading[];
  latest: Reading | null; // newest reading that has a valid AQI
  live: boolean; // reported within 3h of the newest data point in the network
  mean: number;
  max: number;
  pctPoor: number;
}

// Where the live data lives. A GitHub Actions pipeline commits fresh JSON a few times a day;
// raw.githubusercontent.com serves it with CORS, so the site updates without a rebuild.
const LIVE_BASE: string =
  import.meta.env.VITE_DATA_BASE_URL ||
  'https://raw.githubusercontent.com/Divyanshukumar2005/delhi-aqi-pipeline/main/data';

// A few monitors are missing from stations.json. Approximate public locations keep them on the map.
const FALLBACK_COORDS: Record<string, [number, number]> = {
  '6358': [28.6366, 77.2011], // Mandir Marg
  '5610': [28.6573, 77.1585], // North Campus, DU
  '5630': [28.6515, 77.1473], // Shadipur
  '5613': [28.6316, 77.241], // ITO
  '11607': [28.5918, 77.2273], // Lodhi Road
};

const toNum = (v: number | string | null | undefined): number | null => {
  if (v === null || v === undefined || v === '') return null;
  const n = typeof v === 'number' ? v : parseFloat(v);
  return Number.isFinite(n) && n >= 0 ? n : null;
};

async function fetchJson<T>(file: string): Promise<{ data: T; live: boolean }> {
  try {
    const res = await fetch(`${LIVE_BASE}/${file}`, { cache: 'no-cache' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return { data: (await res.json()) as T, live: true };
  } catch (err) {
    console.warn(`Live ${file} unavailable, using bundled copy`, err);
    const res = await fetch(`${import.meta.env.BASE_URL}data/${file}`);
    if (!res.ok) throw new Error(`Bundled ${file} failed: HTTP ${res.status}`);
    return { data: (await res.json()) as T, live: false };
  }
}

export function classifyArea(name: string): Area {
  const s = name.toLowerCase();
  if (s.includes('gurugram') || s.includes('gurgaon')) return 'Gurugram';
  if (s.includes('noida')) return 'Noida';
  if (s.includes('faridabad')) return 'Faridabad';
  if (s.includes('bahadurgarh')) return 'Bahadurgarh';
  return 'Delhi';
}

/** "Sector-51, Gurugram - HSPCB" -> { short: "Sector-51", agency: "HSPCB" } */
function parseName(name: string): { short: string; agency: string } {
  const dash = name.lastIndexOf(' - ');
  const agency = dash > -1 ? name.slice(dash + 3).trim() : '';
  const base = dash > -1 ? name.slice(0, dash) : name;
  const short = base
    .replace(/,\s*(New Delhi|Delhi|Gurugram|Noida|Faridabad|Bahadurgarh)(,\s*UP)?\s*$/i, '')
    .replace(/\s+/g, ' ')
    .replace(/\s*-\s*/g, '-')
    .trim();
  return { short: short || name, agency };
}

/** The one place where "24-hour rolling mean -> CPCB AQI" happens. Needs >= 16 valid hours (CPCB rule). */
function buildReadings(raw: RawReading[]): Reading[] {
  const sorted = [...raw].sort((a, b) => Date.parse(a.ts) - Date.parse(b.ts));
  const out: Reading[] = [];
  const H24 = 24 * 3600 * 1000;
  let lo = 0;
  let s25 = 0, n25 = 0, s10 = 0, n10 = 0;
  const pm25s = sorted.map((r) => toNum(r.pm25));
  const pm10s = sorted.map((r) => toNum(r.pm10));
  const times = sorted.map((r) => Date.parse(r.ts));

  for (let i = 0; i < sorted.length; i++) {
    if (pm25s[i] !== null) { s25 += pm25s[i]!; n25++; }
    if (pm10s[i] !== null) { s10 += pm10s[i]!; n10++; }
    while (times[i] - times[lo] >= H24) {
      if (pm25s[lo] !== null) { s25 -= pm25s[lo]!; n25--; }
      if (pm10s[lo] !== null) { s10 -= pm10s[lo]!; n10--; }
      lo++;
    }
    const m25 = n25 >= 16 ? s25 / n25 : null;
    const m10 = n10 >= 16 ? s10 / n10 : null;
    const aqi = calculateAqi(m25, m10);
    out.push({
      sid: sorted[i].station_id,
      t: times[i],
      date: istDate(times[i]),
      hour: istHour(times[i]),
      pm25: pm25s[i],
      pm10: pm10s[i],
      no2: toNum(sorted[i].no2),
      o3: toNum(sorted[i].o3),
      aqi,
      cat: categoryOf(aqi),
    });
  }
  return out;
}

export interface Dataset {
  stations: Station[];
  readings: Reading[];
  maxT: number;
  minT: number;
  fromLive: boolean;
}

export async function loadDataset(): Promise<Dataset> {
  const [st, rd] = await Promise.all([fetchJson<RawStation[]>('stations.json'), fetchJson<RawReading[]>('readings.json')]);
  const coords = new Map(st.data.map((s) => [String(s.id), s]));

  const grouped = new Map<string, RawReading[]>();
  for (const r of rd.data) {
    const k = String(r.station_id);
    if (!grouped.has(k)) grouped.set(k, []);
    grouped.get(k)!.push({ ...r, station_id: k });
  }

  const all: Reading[] = [];
  const stations: Station[] = [];
  grouped.forEach((list, id) => {
    const readings = buildReadings(list);
    if (!readings.length) return;
    const full = list[list.length - 1].station;
    const { short, agency } = parseName(full);
    const meta = coords.get(id);
    const fb = FALLBACK_COORDS[id];
    const valid = readings.filter((r) => r.aqi !== null);
    const latest = valid.length ? valid[valid.length - 1] : null;
    all.push(...readings);
    stations.push({
      id,
      name: full,
      short,
      agency,
      area: classifyArea(full),
      lat: meta?.lat ?? fb?.[0] ?? null,
      lon: meta?.lon ?? fb?.[1] ?? null,
      readings,
      latest,
      live: false,
      mean: valid.length ? valid.reduce((a, r) => a + r.aqi!, 0) / valid.length : 0,
      max: valid.length ? Math.max(...valid.map((r) => r.aqi!)) : 0,
      pctPoor: valid.length ? (valid.filter((r) => r.cat.id >= POOR_OR_WORSE).length / valid.length) * 100 : 0,
    });
  });

  // two monitors can share a place name (e.g. Pusa DPCC and Pusa IMD): tell them apart by agency
  const seen = new Map<string, number>();
  stations.forEach((s) => seen.set(s.short, (seen.get(s.short) ?? 0) + 1));
  stations.forEach((s) => { if (seen.get(s.short)! > 1 && s.agency) s.short = `${s.short} (${s.agency})`; });

  const maxT = Math.max(...all.map((r) => r.t));
  const minT = Math.min(...all.map((r) => r.t));
  for (const s of stations) s.live = !!s.latest && maxT - s.latest.t <= 3 * 3600 * 1000;
  stations.sort((a, b) => (b.latest?.aqi ?? -1) - (a.latest?.aqi ?? -1));
  return { stations, readings: all, maxT, minT, fromLive: rd.live };
}

// ---------- derived views ----------

const avg = (v: number[]) => (v.length ? v.reduce((a, b) => a + b, 0) / v.length : null);

export interface CityTick { t: number; aqi: number; pm25: number | null; pm10: number | null; no2: number | null; o3: number | null; n: number }

/** City-wide mean per timestamp (needs >= 5 stations reporting so a lone sensor can't swing the line). */
export function cityHourly(stations: Station[]): CityTick[] {
  const buckets = new Map<number, Reading[]>();
  for (const s of stations) for (const r of s.readings) {
    if (!buckets.has(r.t)) buckets.set(r.t, []);
    buckets.get(r.t)!.push(r);
  }
  const mean = (rs: Reading[], k: 'pm25' | 'pm10' | 'no2' | 'o3') => avg(rs.map((r) => r[k]).filter((v): v is number => v !== null));
  return [...buckets.entries()]
    .map(([t, rs]) => ({ t, rs, aqis: rs.map((r) => r.aqi).filter((v): v is number => v !== null) }))
    .filter((b) => b.aqis.length >= Math.min(5, Math.max(1, Math.floor(stations.length / 2))))
    .sort((a, b) => a.t - b.t)
    .map((b) => ({
      t: b.t,
      aqi: Math.round(avg(b.aqis)!),
      pm25: mean(b.rs, 'pm25'), pm10: mean(b.rs, 'pm10'), no2: mean(b.rs, 'no2'), o3: mean(b.rs, 'o3'),
      n: b.aqis.length,
    }));
}

export interface DailyPoint { date: string; aqi: number; n: number; hours: number }
export function cityDaily(ticks: CityTick[]): DailyPoint[] {
  const m = new Map<string, number[]>();
  for (const t of ticks) {
    const d = istDate(t.t);
    if (!m.has(d)) m.set(d, []);
    m.get(d)!.push(t.aqi);
  }
  return [...m.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([date, v]) => ({ date, aqi: Math.round(avg(v)!), n: v.length, hours: v.length }));
}

/** Hour-of-day mean PM2.5 (µg/m³). Uses raw hourly values: the 24 h rolling AQI is smoothed and hides the daily cycle. */
export function diurnal(stations: Station[]) {
  const sums = Array.from({ length: 24 }, () => ({ s: 0, n: 0 }));
  for (const st of stations) for (const r of st.readings) if (r.pm25 !== null) { sums[r.hour].s += r.pm25; sums[r.hour].n++; }
  return sums.map((x, hour) => ({ hour, pm25: x.n ? Math.round((x.s / x.n) * 10) / 10 : (null as number | null) }));
}

export type HeatMetric = 'pm25' | 'aqi';

/**
 * Value behind one heatmap cell. Hourly PM2.5 keeps the real daily cycle; the 24 h rolling AQI is
 * smoothed over a whole day, so every hour of a day would look almost the same.
 */
const cellValue = (r: Reading, metric: HeatMetric) => (metric === 'pm25' ? r.pm25 : r.aqi);

/** date x hour grid of city-mean values. Days with (almost) no coverage are dropped and reported back. */
export function dateHourGrid(stations: Station[], metric: HeatMetric = 'pm25') {
  const cell = new Map<string, { s: number; n: number }>();
  const dates = new Set<string>();
  let lo = Infinity, hi = -Infinity;
  for (const st of stations) for (const r of st.readings) {
    lo = Math.min(lo, r.t); hi = Math.max(hi, r.t);
    const v = cellValue(r, metric);
    if (v === null) continue;
    dates.add(r.date);
    const k = `${r.date}|${r.hour}`;
    const c = cell.get(k) ?? { s: 0, n: 0 };
    c.s += v; c.n++;
    cell.set(k, c);
  }
  // a city cell needs several stations behind it, otherwise one sensor would pose as "the city"
  const minN = Math.min(5, Math.max(1, Math.floor(stations.length / 2)));
  const all = [...dates].sort().map((date) => ({
    date,
    cells: Array.from({ length: 24 }, (_, h) => {
      const c = cell.get(`${date}|${h}`);
      return c && c.n >= minN ? Math.round(c.s / c.n) : null;
    }),
  }));
  const rows = all.filter((r) => r.cells.filter((v) => v !== null).length >= 6);
  // calendar days inside the period that have no usable row
  const kept = new Set(rows.map((r) => r.date));
  const skipped: string[] = [];
  if (Number.isFinite(lo)) {
    for (let t = lo; t <= hi + 86400000; t += 86400000) {
      const d = istDate(t);
      if (!kept.has(d) && !skipped.includes(d) && d >= rows[0]?.date && d <= rows[rows.length - 1]?.date) skipped.push(d);
    }
  }
  return { rows, skipped };
}

/** station x hour-of-day grid of mean values */
export function stationHourGrid(stations: Station[], metric: HeatMetric = 'pm25') {
  return stations
    .map((s) => {
      const sums = Array.from({ length: 24 }, () => ({ s: 0, n: 0 }));
      let tot = 0, cnt = 0;
      for (const r of s.readings) {
        const v = cellValue(r, metric);
        if (v === null) continue;
        sums[r.hour].s += v; sums[r.hour].n++;
        tot += v; cnt++;
      }
      return { station: s, mean: cnt ? tot / cnt : -1, cells: sums.map((x) => (x.n ? Math.round(x.s / x.n) : null)) };
    })
    .filter((r) => r.mean >= 0)
    .sort((a, b) => b.mean - a.mean);
}

export function categoryShare(stations: Station[]) {
  const counts = [0, 0, 0, 0, 0, 0];
  let total = 0;
  for (const s of stations) for (const r of s.readings) if (r.aqi !== null) { counts[r.cat.id]++; total++; }
  return { counts, total };
}

// ---------- ML forecast (data/ml_forecast.json, written by src/export_json.py) ----------

export interface MlHorizon {
  h: number;
  predicted_aqi: number;
  category: string;
  model: string;
  /** Mean absolute error of this model on the back-test (AQI points). */
  backtest_mae: number;
  /** Same back-test, for "same as now". Missing in files written before this field existed. */
  persistence_mae?: number;
}
export type MlForecast =
  | { available: true; generated_at: string; origin_ts: string; current_aqi: number; backtest?: string; horizons: MlHorizon[] }
  | { available: false; generated_at?: string; reason?: string };

/** Latest ML forecast, or null when the file does not exist yet or cannot be read. Never throws. */
export async function loadMlForecast(): Promise<MlForecast | null> {
  try {
    const { data } = await fetchJson<MlForecast>('ml_forecast.json');
    if (!data || typeof data !== 'object' || typeof data.available !== 'boolean') return null;
    if (data.available && !Array.isArray(data.horizons)) return null;
    return data;
  } catch {
    return null;
  }
}
