import { useMemo } from 'react';
import { HeatGrid, type HeatRow } from '../components/HeatGrid';
import { DiurnalChart } from '../components/charts';
import { Section } from '../components/ui';
import { CATEGORIES } from '../lib/aqi';
import { dateHourGrid, stationHourGrid } from '../lib/data';
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

export function HeatmapTab({ m }: { m: Model }) {
  const cityRows = useMemo<HeatRow[]>(
    () => dateHourGrid(m.stations).reverse().map((r) => ({ key: r.date, label: fmtDay(r.date), sub: fmtWeekday(r.date), cells: r.cells })),
    [m.stations],
  );
  const stationRows = useMemo<HeatRow[]>(
    () => stationHourGrid(m.stations).map((r) => ({ key: r.station.id, label: r.station.short, sub: r.station.area, cells: r.cells })),
    [m.stations],
  );

  return (
    <div className="space-y-5">
      <Section title="City AQI by day and hour" hint="Each cell averages the stations reporting in that hour (IST). Blank cells had fewer than five stations. Newest day first." right={<Scale />}>
        <HeatGrid rows={cityRows} rowHeader="Date" readout={(r, h, v) => `${r.label} (${r.sub}), ${fmtHour(h)} IST: ${v === null ? 'no data' : `AQI ${v}`}`} />
      </Section>

      <Section title="Which stations are worst, and when" hint="Mean AQI by hour of day over the whole period, one row per station, most polluted at the top." right={<Scale />}>
        <HeatGrid rows={stationRows} rowHeader="Station" readout={(r, h, v) => `${r.label}, ${fmtHour(h)} IST: ${v === null ? 'no data' : `mean AQI ${v}`}`} />
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
