import {
  Area, CartesianGrid, ComposedChart, Line, LineChart, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { CATEGORIES, categoryOf } from '../lib/aqi';
import { fmtDay, fmtShort, fmtHour, pad2 } from '../lib/time';

const tick = { fill: 'var(--ink-3)', fontSize: 11.5 };
const axisLine = { stroke: 'var(--line)' };

/** Midnight-IST timestamps inside [min, max] for day-level x ticks. */
export function dayTicks(min: number, max: number): number[] {
  const out: number[] = [];
  const IST = 5.5 * 3600000;
  let d = Math.ceil((min + IST) / 86400000) * 86400000 - IST;
  for (; d <= max; d += 86400000) out.push(d);
  return out.length > 9 ? out.filter((_, i) => i % 2 === 0) : out;
}

const BANDS = CATEGORIES.map((c, i) => ({ c, y1: i === 0 ? 0 : c.min - 1, y2: c.max }));
function Bands() {
  return (
    <>
      {BANDS.map(({ c, y1, y2 }) => (
        <ReferenceArea key={c.name} y1={y1} y2={y2} fill={c.fill} fillOpacity={0.1} stroke="none" ifOverflow="hidden" />
      ))}
    </>
  );
}

const yTop = (max: number) => Math.max(100, Math.ceil((max + 20) / 50) * 50);

interface TipRow { color?: string; name?: string; value?: number | string | null; cat?: boolean }
function Tip({ active, title, rows }: { active?: boolean; title: string; rows: TipRow[] }) {
  if (!active) return null;
  return (
    <div className="card min-w-[150px] p-3 text-[13px]" style={{ boxShadow: 'var(--shadow)' }}>
      <div className="mb-1.5 font-semibold">{title}</div>
      {rows.map((r, i) => (
        <div key={i} className="flex items-center justify-between gap-4">
          <span className="flex items-center gap-1.5 subtle">
            {r.color && <span className="h-2 w-2 rounded-full" style={{ background: r.color }} />}
            {r.name}
          </span>
          <span className="num font-semibold" style={{ color: r.cat && typeof r.value === 'number' ? categoryOf(r.value).ink : undefined }}>
            {r.value ?? '–'}
            {r.cat && typeof r.value === 'number' && <span className="ml-1.5 font-sans text-xs font-medium muted">{categoryOf(r.value).name}</span>}
          </span>
        </div>
      ))}
    </div>
  );
}

type Gap = { from: number; to: number };
function Gaps({ gaps }: { gaps: Gap[] }) {
  return (
    <>
      {gaps.map((g) => (
        <ReferenceArea key={g.from} x1={g.from} x2={g.to} fill="var(--ink-3)" fillOpacity={0.16} stroke="var(--ink-3)" strokeOpacity={0.35} strokeDasharray="3 3" ifOverflow="hidden" label={{ value: 'No network data', position: 'insideTop', fill: 'var(--ink-2)', fontSize: 11.5 }} />
      ))}
    </>
  );
}

export function CityTrend({ data, gaps = [], height = 300 }: { data: { t: number; aqi: number | null }[]; gaps?: Gap[]; height?: number }) {
  if (!data.length) return null;
  const top = yTop(Math.max(...data.map((d) => d.aqi ?? 0)));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
        <defs>
          <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--ink)" stopOpacity={0.16} />
            <stop offset="100%" stopColor="var(--ink)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <Bands />
        <Gaps gaps={gaps} />
        <CartesianGrid stroke="var(--line-soft)" vertical={false} />
        <XAxis dataKey="t" type="number" scale="time" domain={['dataMin', 'dataMax']} ticks={dayTicks(data[0].t, data[data.length - 1].t)} tickFormatter={(t) => fmtDay(new Date(t + 19800000).toISOString().slice(0, 10))} tick={tick} axisLine={axisLine} tickLine={false} />
        <YAxis domain={[0, top]} tick={tick} axisLine={false} tickLine={false} width={44} />
        <Tooltip cursor={{ stroke: 'var(--ink-3)', strokeDasharray: '3 3' }} content={({ active, payload }) => active && payload?.length && payload[0].payload.aqi !== null ? <Tip active title={fmtShort(payload[0].payload.t) + ' IST'} rows={[{ name: 'City AQI', value: payload[0].payload.aqi, cat: true }]} /> : null} />
        <Area type="monotone" dataKey="aqi" stroke="var(--ink)" strokeWidth={2} fill="url(#trendFill)" dot={false} activeDot={{ r: 4, fill: 'var(--ink)', stroke: 'var(--surface)', strokeWidth: 2 }} isAnimationActive={false} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

export function PollutantChart({ data, gaps = [], k, label, limit, height = 280 }: { data: { t: number; v: number | null }[]; gaps?: Gap[]; k: string; label: string; limit: number; height?: number }) {
  const rows = data;
  if (!rows.some((d) => d.v !== null)) return null;
  const top = Math.max(limit * 1.25, Math.max(...rows.map((d) => d.v ?? 0)) * 1.1);
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: -12 }} key={k}>
        <Gaps gaps={gaps} />
        <CartesianGrid stroke="var(--line-soft)" vertical={false} />
        <XAxis dataKey="t" type="number" scale="time" domain={['dataMin', 'dataMax']} ticks={dayTicks(rows[0].t, rows[rows.length - 1].t)} tickFormatter={(t) => fmtDay(new Date(t + 19800000).toISOString().slice(0, 10))} tick={tick} axisLine={axisLine} tickLine={false} />
        <YAxis domain={[0, Math.ceil(top / 50) * 50]} tick={tick} axisLine={false} tickLine={false} width={44} />
        <ReferenceLine y={limit} stroke="var(--aqi-4-ink)" strokeDasharray="5 4" label={{ value: `CPCB limit ${limit}`, position: 'insideTopRight', fill: 'var(--aqi-4-ink)', fontSize: 11.5 }} />
        <Tooltip cursor={{ stroke: 'var(--ink-3)', strokeDasharray: '3 3' }} content={({ active, payload }) => active && payload?.length && payload[0].payload.v !== null ? <Tip active title={fmtShort(payload[0].payload.t) + ' IST'} rows={[{ name: label, value: Math.round(payload[0].payload.v * 10) / 10 }]} /> : null} />
        <Line type="monotone" dataKey="v" stroke="var(--s1)" strokeWidth={2} dot={false} activeDot={{ r: 4, fill: 'var(--s1)', stroke: 'var(--surface)', strokeWidth: 2 }} isAnimationActive={false} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

export function DiurnalChart({ data, peak, clean, height = 260 }: { data: { hour: number; pm25: number | null }[]; peak: number | null; clean: number | null; height?: number }) {
  const limit = 60;
  const top = Math.ceil(Math.max(limit * 1.2, ...data.map((d) => (d.pm25 ?? 0) * 1.15)) / 10) * 10;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data} margin={{ top: 12, right: 12, bottom: 0, left: -12 }}>
        <CartesianGrid stroke="var(--line-soft)" vertical={false} />
        <XAxis dataKey="hour" tickFormatter={pad2} interval={2} tick={tick} axisLine={axisLine} tickLine={false} />
        <YAxis domain={[0, top]} tick={tick} axisLine={false} tickLine={false} width={44} />
        <ReferenceLine y={limit} stroke="var(--aqi-4-ink)" strokeDasharray="5 4" label={{ value: `CPCB 24h limit ${limit}`, position: 'insideTopRight', fill: 'var(--aqi-4-ink)', fontSize: 11.5 }} />
        {peak !== null && <ReferenceLine x={peak} stroke="var(--aqi-4-ink)" strokeDasharray="4 3" />}
        {clean !== null && <ReferenceLine x={clean} stroke="var(--aqi-0-ink)" strokeDasharray="4 3" />}
        <Tooltip cursor={{ stroke: 'var(--ink-3)', strokeDasharray: '3 3' }} content={({ active, payload }) => active && payload?.length ? <Tip active title={`${fmtHour(payload[0].payload.hour)} IST`} rows={[{ name: 'Mean PM2.5 (µg/m³)', value: payload[0].payload.pm25 }]} /> : null} />
        <Line type="monotone" dataKey="pm25" stroke="var(--s1)" strokeWidth={2.25} dot={false} activeDot={{ r: 4, fill: 'var(--s1)', stroke: 'var(--surface)', strokeWidth: 2 }} isAnimationActive={false} connectNulls />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

export function StationLines({ rows, series, height = 320 }: { rows: Record<string, number | null>[]; series: { key: string; name: string; color: string }[]; height?: number }) {
  if (!rows.length) return null;
  const t0 = rows[0].t as number, t1 = rows[rows.length - 1].t as number;
  const top = yTop(Math.max(...rows.flatMap((r) => series.map((s) => (r[s.key] as number | null) ?? 0))));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
        <Bands />
        <CartesianGrid stroke="var(--line-soft)" vertical={false} />
        <XAxis dataKey="t" type="number" scale="time" domain={[t0, t1]} ticks={dayTicks(t0, t1)} tickFormatter={(t) => fmtDay(new Date(t + 19800000).toISOString().slice(0, 10))} tick={tick} axisLine={axisLine} tickLine={false} />
        <YAxis domain={[0, top]} tick={tick} axisLine={false} tickLine={false} width={44} />
        <Tooltip cursor={{ stroke: 'var(--ink-3)', strokeDasharray: '3 3' }} content={({ active, payload }) => active && payload?.length ? <Tip active title={fmtShort(payload[0].payload.t as number) + ' IST'} rows={series.map((s) => ({ color: s.color, name: s.name, value: payload[0].payload[s.key] as number | null }))} /> : null} />
        {series.map((s) => (
          <Line key={s.key} type="monotone" dataKey={s.key} stroke={s.color} strokeWidth={2} dot={false} connectNulls={false} activeDot={{ r: 4, stroke: 'var(--surface)', strokeWidth: 2 }} isAnimationActive={false} />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

export function ForecastChart({ rows, height = 300 }: { rows: { label: string; predicted: number; band: [number, number] }[]; height?: number }) {
  const top = yTop(Math.max(...rows.map((r) => r.band[1])));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
        <Bands />
        <CartesianGrid stroke="var(--line-soft)" vertical={false} />
        <XAxis dataKey="label" interval={2} tick={tick} axisLine={axisLine} tickLine={false} />
        <YAxis domain={[0, top]} tick={tick} axisLine={false} tickLine={false} width={44} />
        <Tooltip cursor={{ stroke: 'var(--ink-3)', strokeDasharray: '3 3' }} content={({ active, payload }) => active && payload?.length ? <Tip active title={`${payload[0].payload.label} IST`} rows={[{ name: 'Forecast', value: payload[0].payload.predicted, cat: true }, { name: 'Range', value: `${payload[0].payload.band[0]}–${payload[0].payload.band[1]}` }]} /> : null} />
        <Area type="monotone" dataKey="band" stroke="none" fill="var(--s1)" fillOpacity={0.16} isAnimationActive={false} />
        <Line type="monotone" dataKey="predicted" stroke="var(--s1)" strokeWidth={2.25} strokeDasharray="6 4" dot={false} activeDot={{ r: 4, fill: 'var(--s1)', stroke: 'var(--surface)', strokeWidth: 2 }} isAnimationActive={false} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

export function Spark({ values, height = 56 }: { values: { t: number; aqi: number | null }[]; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={values} margin={{ top: 4, right: 2, bottom: 4, left: 2 }}>
        <YAxis hide domain={[0, 'dataMax + 30']} />
        <Line type="monotone" dataKey="aqi" stroke="var(--ink)" strokeWidth={1.75} dot={false} isAnimationActive={false} connectNulls />
      </LineChart>
    </ResponsiveContainer>
  );
}
