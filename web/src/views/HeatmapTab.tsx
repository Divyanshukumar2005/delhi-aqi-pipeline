import { useMemo, useState } from 'react';
import { HeatGrid, type HeatRow } from '../components/HeatGrid';
import { DiurnalChart } from '../components/charts';
import { Section } from '../components/ui';
import { CATEGORIES } from '../lib/aqi';
import { dateHourGrid, stationHourGrid, type HeatMetric } from '../lib/data';
import { fmtDay, fmtHour, fmtWeekday } from '../lib/time';
import type { Model } from '../lib/model';

function Scale() {
  return (
    <div className="flex items-center gap-3 text-xs subtle">
      {CATEGORIES.map((c) => (
        <span key={c.name} className="flex items-center gap-1.5">
          <span className="h-3 w-3 rounded-[3px]" style={{ background: c.fill }} />
          <span className="hidden sm:inline">{c.name}</span>
        </span>
      ))}
    </div>
  );
}

const METRICS: { id: HeatMetric; label: string; unit: string; desc: string }[] = [
  { id: 'pm25', label: 'PM2.5 (hourly)', unit: 'µg/m³', desc: 'Raw hourly PM2.5, coloured by the CPCB category it falls in. This shows the real daily cycle.' },
  { id: 'aqi', label: 'AQI (24 h rolling)', unit: 'AQI', desc: 'The published 24-hour rolling AQI. It is smoothed over a day, so it moves slowly from hour to hour.' },
];

const fmtList = (days: string[]) => {
  if (!days.length) return '';
  const ranges: string[] = [];
  let start = days[0], prev = days[0];
  const next = (d: string) => new Date(Date.parse(`${d}T00:00:00Z`) + 86400000).toISOString().slice(0, 10);
  const push = () => ranges.push(start === prev ? fmtDay(start) : `${fmtDay(start)} to ${fmtDay(prev)}`);
  for (const d of days.slice(1)) { if (d === next(prev)) { prev = d; } else { push(); start = d; prev = d; } }
  push();
  return ranges.join(', ');
};

export function HeatmapTab({ m }: { m: Model }) {
  const [metric, setMetric] = useState<HeatMetric>('pm25');
  const info = METRICS.find((x) => x.id === metric)!;
  const grid = useMemo(() => dateHourGrid(m.stations, metric), [m.stations, metric]);
  const cityRows = useMemo<HeatRow[]>(
    () => [...grid.rows].reverse().map((r) => ({ key: r.date, label: fmtDay(r.date), sub: fmtWeekday(r.date), cells: r.cells })),
    [grid],
  );
  const stationRows = useMemo<HeatRow[]>(
    () => stationHourGrid(m.stations, metric).map((r) => ({ key: r.station.id, label: r.station.short, sub: r.station.area, cells: r.cells })),
    [m.stations, metric],
  );
  const val = (v: number | null) => (v === null ? 'no data' : metric === 'pm25' ? `${v} µg/m³` : `AQI ${v}`);

  return (
    <div className="space-y-5">
      <div className="card flex flex-wrap items-center justify-between gap-3 p-4 sm:px-6">
        <p className="max-w-[62ch] text-[13px] subtle">{info.desc}</p>
        <div className="flex gap-1.5" role="group" aria-label="Heatmap measure">
          {METRICS.map((x) => (
            <button key={x.id} className="chip" aria-pressed={metric === x.id} onClick={() => setMetric(x.id)}>{x.label}</button>
          ))}
        </div>
      </div>

      <Section title="City by day and hour" hint="Each cell averages the stations reporting in that hour (IST), shown in the unit chosen above. Newest day first." right={<Scale />}>
        <HeatGrid rows={cityRows} rowHeader="Date" metric={metric} readout={(r, h, v) => `${r.label} (${r.sub}), ${fmtHour(h)} IST: ${val(v)}`} />
        {grid.skipped.length > 0 && <p className="mt-3 text-xs muted">No monitor coverage on {fmtList(grid.skipped)}, so those days are not shown.</p>}
      </Section>

      <Section title="Which stations are worst, and when" hint="Mean value by hour of day over the whole period, one row per station, most polluted at the top." right={<Scale />}>
        <HeatGrid rows={stationRows} rowHeader="Station" metric={metric} readout={(r, h, v) => `${r.label}, ${fmtHour(h)} IST: ${v === null ? 'no data' : `mean ${val(v)}`}`} />
      </Section>

      <div className="grid gap-5 lg:grid-cols-2">
        <Section
          title="A typical day"
          hint={m.peak && m.clean ? `Hourly PM2.5 averaged by time of day. Highest near ${fmtHour(m.peak.hour)} IST (${Math.round(m.peak.pm25)} µg/m³), lowest near ${fmtHour(m.clean.hour)} IST (${Math.round(m.clean.pm25)} µg/m³).` : undefined}
        >
          <DiurnalChart data={m.dProfile} peak={m.peak?.hour ?? null} clean={m.clean?.hour ?? null} />
        </Section>

        <Section title="Time spent in each category" hint="Share of all station-hours in the selected area.">
          <div className="space-y-3.5">
            {CATEGORIES.map((c, i) => {
              const n = m.share.counts[i];
              const pct = m.share.total ? (n / m.share.total) * 100 : 0;
              return (
                <div key={c.name}>
                  <div className="mb-1 flex items-center justify-between text-[13px]">
                    <span className="flex items-center gap-2 font-medium"><span className="h-2.5 w-2.5 rounded-full" style={{ background: c.fill }} />{c.name}</span>
                    <span className="num subtle">{n.toLocaleString('en-IN')} h · {pct.toFixed(1)}%</span>
                  </div>
                  <div className="h-2.5 overflow-hidden rounded-full" style={{ background: 'var(--line-soft)' }}>
                    <div className="h-full rounded-full transition-[width] duration-500" style={{ width: `${pct}%`, background: c.fill }} />
                  </div>
                </div>
              );
            })}
          </div>
        </Section>
      </div>
    </div>
  );
}
