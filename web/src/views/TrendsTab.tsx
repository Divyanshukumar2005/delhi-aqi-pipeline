import { useMemo, useState } from 'react';
import { CityTrend, PollutantChart } from '../components/charts';
import { CatBadge, Section } from '../components/ui';
import { POLLUTANTS, categoryOf, type Pollutant } from '../lib/aqi';
import { fmtDay, fmtWeekday } from '../lib/time';
import type { Model } from '../lib/model';

export function TrendsTab({ m }: { m: Model }) {
  const [p, setP] = useState<Pollutant>('pm25');
  const info = POLLUTANTS[p];
  const series = useMemo(() => m.gapped.map((t) => ({ t: t.t, v: t[p] })), [m.gapped, p]);
  const daily = [...m.daily].filter((d) => d.hours >= 6).reverse();

  return (
    <div className="space-y-5">
      <Section title="City AQI over time" hint="Hourly average across stations, computed from the rolling 24-hour PM2.5 and PM10 means.">
        <CityTrend data={m.gapped} gaps={m.gaps} />
      </Section>

      <Section
        title={`${info.label} concentration`}
        hint={`Hourly city average in µg/m³ against the ${info.limitNote} of ${info.limit} µg/m³.`}
        right={
          <div className="flex flex-wrap gap-1.5" role="group" aria-label="Pollutant">
            {(Object.keys(POLLUTANTS) as Pollutant[]).map((k) => (
              <button key={k} className="chip" aria-pressed={p === k} onClick={() => setP(k)}>{POLLUTANTS[k].label}</button>
            ))}
          </div>
        }
      >
        <PollutantChart data={series} gaps={m.gaps} k={p} label={`${info.label} (µg/m³)`} limit={info.limit} />
      </Section>

      <Section title="Day by day" hint="Daily average of the hourly city AQI. Days with under 6 hours of city-wide data are left out; the latest day is still in progress.">
        <div className="scroll-x max-h-[420px] overflow-y-auto">
          <table className="tbl">
            <thead><tr><th>Date</th><th>Day</th><th className="text-right">Mean AQI</th><th>Category</th><th className="text-right">Hours</th></tr></thead>
            <tbody>
              {daily.map((d) => (
                <tr key={d.date}>
                  <td className="font-medium">{fmtDay(d.date)}</td>
                  <td className="muted">{fmtWeekday(d.date)}</td>
                  <td className="num text-right font-semibold" style={{ color: categoryOf(d.aqi).ink }}>{d.aqi}</td>
                  <td><CatBadge cat={categoryOf(d.aqi)} /></td>
                  <td className="num text-right muted">{d.hours}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
    </div>
  );
}
