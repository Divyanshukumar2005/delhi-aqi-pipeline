import { useMemo } from 'react';
import { Download } from 'lucide-react';
import { CatBadge, Section } from '../components/ui';
import { diwaliNight } from '../lib/data';
import { welch } from '../lib/stats';
import { daysUntil, fmtDay, fmtHour, fmtShort } from '../lib/time';
import { categoryOf } from '../lib/aqi';
import type { Model } from '../lib/model';

const DIWALI = '2026-11-08';

export function InsightsTab({ m, onCsv }: { m: Model; onCsv: () => void }) {
  const test = useMemo(() => {
    const complete = m.daily.filter((d) => d.hours >= 12);
    const isWeekend = (date: string) => [0, 6].includes(new Date(`${date}T00:00:00Z`).getUTCDay());
    return welch(complete.filter((d) => !isWeekend(d.date)).map((d) => d.aqi), complete.filter((d) => isWeekend(d.date)).map((d) => d.aqi));
  }, [m.daily]);

  const rows = useMemo(() => m.stations.flatMap((s) => s.readings.map((r) => ({ s, r }))).sort((a, b) => b.r.t - a.r.t).slice(0, 15), [m.stations]);
  const toDiwali = daysUntil(DIWALI);
  const night = useMemo(() => diwaliNight(m.stations, DIWALI), [m.stations]);
  const spread = m.worst && m.cleanest ? m.worst.latest!.aqi! - m.cleanest.latest!.aqi! : null;

  return (
    <div className="space-y-5">
      <div className="grid gap-5 md:grid-cols-2">
        <Section title="Daily rhythm">
          {m.peak && m.clean ? (
            <p className="text-[14.5px] leading-relaxed subtle">
              Fine-particle pollution (PM2.5) is highest near <b className="num">{fmtHour(m.peak.hour)} IST</b> (about {Math.round(m.peak.pm25)} µg/m³), a time of cool, still air that
              usually traps emissions near the ground. It is lowest near <b className="num">{fmtHour(m.clean.hour)} IST</b> ({Math.round(m.clean.pm25)} µg/m³), when daytime heating mixes the air upward.
            </p>
          ) : <p className="text-sm muted">Not enough data.</p>}
        </Section>

        <Section title="How much stations differ">
          {m.worst && m.cleanest && spread !== null ? (
            <p className="text-[14.5px] leading-relaxed subtle">
              Right now <b>{m.worst.short}</b> reads <b className="num" style={{ color: m.worst.latest!.cat.ink }}>{m.worst.latest!.aqi}</b> while <b>{m.cleanest.short}</b> reads{' '}
              <b className="num" style={{ color: m.cleanest.latest!.cat.ink }}>{m.cleanest.latest!.aqi}</b>, a gap of <b className="num">{spread}</b> points inside one metro region. A single “Delhi AQI” hides that spread.
            </p>
          ) : <p className="text-sm muted">Not enough live stations.</p>}
        </Section>

        <Section title="Weekday vs weekend" hint="Welch’s two-sample t-test on daily city means, using days with at least 12 hours of city-wide data.">
          {test ? (
            <div className="text-[14.5px] leading-relaxed subtle">
              <div className="flex gap-6">
                <div><div className="text-xs muted">Weekdays (n={test.nA})</div><div className="num text-2xl font-semibold" style={{ color: 'var(--ink)' }}>{Math.round(test.meanA)}</div></div>
                <div><div className="text-xs muted">Weekends (n={test.nB})</div><div className="num text-2xl font-semibold" style={{ color: 'var(--ink)' }}>{Math.round(test.meanB)}</div></div>
                <div><div className="text-xs muted">p-value</div><div className="num text-2xl font-semibold" style={{ color: 'var(--ink)' }}>{test.p < 0.001 ? '<0.001' : test.p.toFixed(3)}</div></div>
              </div>
              <p className="mt-3">
                t = {test.t.toFixed(2)}, df = {test.df.toFixed(1)}. {test.p < 0.05
                  ? `The difference is statistically significant at the 5% level.`
                  : `This is not significant at the 5% level: with so few days we cannot tell a real weekday effect from normal day-to-day swings.`}
              </p>
            </div>
          ) : <p className="text-sm muted">Not enough days yet: the test needs at least two weekdays and two weekend days with 12 or more hours of data each.</p>}
        </Section>

        <Section title="Diwali night benchmark" hint="Raw hourly PM2.5, 8 Nov 18:00 to 9 Nov 12:00 IST, against the same hours on the 7 days before.">
          {night ? (
            <>
              <div className="flex items-baseline gap-3">
                <span className="num text-4xl font-semibold">{night.changePct >= 0 ? '+' : ''}{Math.round(night.changePct)}%</span>
                <span className="text-sm subtle">{Math.round(night.baselineMean)} to {Math.round(night.eventMean)} µg/m³ (city mean)</span>
              </div>
              <p className="mt-2 text-[14px] leading-relaxed subtle">
                The worst hour reached a city mean of <b className="num">{Math.round(night.peakCityMean)}</b> µg/m³ and the worst single station <b className="num">{Math.round(night.peakStation)}</b> µg/m³.
                The baseline uses {night.baselineDays} nights{night.skippedDays.length ? ` (${night.skippedDays.map(fmtDay).join(', ')} skipped for missing data)` : ''}.
                Only {night.minStations} stations reported in the thinnest hour. Descriptive only: wind and weather also change from night to night.
              </p>
            </>
          ) : (
            <>
              <div className="flex items-baseline gap-3">
                <span className="num text-4xl font-semibold">{toDiwali > 0 ? toDiwali : '–'}</span>
                <span className="text-sm subtle">{toDiwali > 0 ? `days until Diwali on ${fmtDay(DIWALI)}` : toDiwali === 0 ? 'Diwali is today' : 'Diwali has passed'}</span>
              </div>
              <p className="mt-2 text-[14px] subtle">The comparison appears once the festival night and at least four earlier nights have enough readings.</p>
            </>
          )}
        </Section>
      </div>

      <Section
        title="Latest readings"
        hint="The 15 most recent hourly rows across the selected stations."
        right={<button className="btn btn-solid" onClick={onCsv}><Download className="h-4 w-4" />Download CSV</button>}
      >
        <div className="scroll-x">
          <table className="tbl">
            <thead><tr><th>Station</th><th>Area</th><th>Time (IST)</th><th className="text-right">PM2.5</th><th className="text-right">PM10</th><th className="text-right">AQI</th><th>Category</th></tr></thead>
            <tbody>
              {rows.map(({ s, r }, i) => (
                <tr key={i}>
                  <td className="max-w-[220px] truncate font-semibold">{s.short}</td>
                  <td className="muted">{s.area}</td>
                  <td className="num">{fmtShort(r.t)}</td>
                  <td className="num text-right">{r.pm25 ?? '–'}</td>
                  <td className="num text-right">{r.pm10 ?? '–'}</td>
                  <td className="num text-right font-semibold" style={{ color: r.cat.ink }}>{r.aqi ?? '–'}</td>
                  <td>{r.aqi !== null && <CatBadge cat={r.cat} />}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
    </div>
  );
}
