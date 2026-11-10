import { AlertTriangle } from 'lucide-react';
import { Section, Stat } from './ui';
import type { LensRow } from '../lib/data';

const fmt = (v: number | null) => (v === null ? '–' : Math.round(v).toLocaleString('en-IN'));
const when = (t: number) =>
  new Date(t).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false });

/** Shows what the 24 h, 500-capped CPCB AQI hides: raw PM2.5 peaks, hourly AQI, the uncapped AQI and station coverage. */
export function PeakLens({ lens }: { lens: LensRow[] }) {
  const rows = lens.filter((r) => r.pm25Max !== null);
  if (!rows.length) return null;
  const peak = rows.reduce((m, r) => (r.pm25Max! > m.pm25Max! ? r : m));
  const typical = [...rows].map((r) => r.n).sort((a, b) => a - b)[Math.floor(rows.length / 2)];
  const worst = [...rows].sort((a, b) => b.pm25Max! - a.pm25Max!).slice(0, 8);
  const maxN = Math.max(...rows.map((r) => r.n), 1);

  return (
    <Section title="Peak and live lens" hint="The CPCB AQI averages 24 hours and stops at 500, so a short spike barely moves it. This is the same data hour by hour.">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Peak PM2.5, one station" value={`${fmt(peak.pm25Max)} µg/m³`} sub={when(peak.t)} />
        <Stat label="CPCB AQI (24h avg)" value={fmt(peak.h24)} sub="city mean, capped at 500" />
        <Stat label="Hourly AQI (cap 500)" value={fmt(peak.hourly)} sub="city mean, 1-hour PM" />
        <Stat label="Uncapped AQI" value={fmt(peak.extMax)} sub="worst station, no 500 cap" />
      </div>

      <div className="mt-4 flex gap-3 rounded-xl p-3.5 text-[14px]" style={{ background: 'var(--surface-2, rgba(0,0,0,0.04))' }}>
        <AlertTriangle className="mt-0.5 h-[18px] w-[18px] shrink-0" />
        <p className="subtle">
          At the peak hour only <b>{peak.n}</b> stations reported PM2.5 (a normal hour has {typical}). Stations that miss
          16 valid hours get no CPCB AQI, so the worst-hit sites can be absent from the city number. Uncapped AQI
          continues the CPCB Severe slope past 500, where CPCB itself stops. Use it to compare spike size, not as a CPCB category.
        </p>
      </div>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-left text-[13px]">
          <thead className="muted">
            <tr><th className="py-1.5 pr-3">Hour (IST)</th><th className="pr-3">PM2.5 max</th><th className="pr-3">CPCB 24h</th><th className="pr-3">Hourly</th><th className="pr-3">Uncapped</th><th>Stations</th></tr>
          </thead>
          <tbody>
            {worst.map((r) => (
              <tr key={r.t} className="border-t" style={{ borderColor: 'var(--line)' }}>
                <td className="py-1.5 pr-3">{when(r.t)}</td>
                <td className="num pr-3">{fmt(r.pm25Max)}</td>
                <td className="num pr-3">{fmt(r.h24)}</td>
                <td className="num pr-3">{fmt(r.hourly)}</td>
                <td className="num pr-3">{fmt(r.extMax)}</td>
                <td>
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-20 rounded" style={{ background: 'var(--line)' }}>
                      <div className="h-2 rounded" style={{ width: `${(r.n / maxN) * 100}%`, background: 'var(--ink-3)' }} />
                    </div>
                    <span className="num">{r.n}</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  );
}
