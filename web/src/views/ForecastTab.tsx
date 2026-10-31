import { useMemo } from 'react';
import { Info } from 'lucide-react';
import { ForecastChart } from '../components/charts';
import { Section, Stat } from '../components/ui';
import { categoryOf, subIndex } from '../lib/aqi';
import { fmtHour, istHour } from '../lib/time';
import type { Model } from '../lib/model';

/** Persistence that decays (12 h half-life) toward the empirical hour-of-day pattern. */
export function useForecast(m: Model, lastT: number) {
  return useMemo(() => {
    if (m.cityAqi === null) return [];
    const now = m.cityAqi;
    const idx = (pm: number | null) => (pm === null ? null : subIndex(pm, 'pm25'));
    const base = idx(m.pm25Mean) ?? now;
    return Array.from({ length: 24 }, (_, i) => {
      const k = i + 1;
      const hour = istHour(lastT + k * 3600000);
      // hour-of-day swing, expressed as an AQI offset from the day's average PM2.5 level
      const offset = (idx(m.dProfile[hour].pm25) ?? base) - base;
      const decay = Math.pow(0.5, k / 12);
      const predicted = Math.round(now + (1 - decay) * 0.7 * offset);
      const unc = Math.round(18 * Math.sqrt(k / 12));
      const p = Math.min(500, Math.max(0, predicted));
      return { label: fmtHour(hour), hour, predicted: p, band: [Math.max(0, p - unc), Math.min(500, p + unc)] as [number, number] };
    });
  }, [m.cityAqi, m.dProfile, m.pm25Mean, lastT]);
}

export function ForecastTab({ m, lastT }: { m: Model; lastT: number }) {
  const rows = useForecast(m, lastT);
  const avg = rows.length ? Math.round(rows.reduce((a, r) => a + r.predicted, 0) / rows.length) : null;
  const hi = rows.length ? rows.reduce((a, r) => (r.predicted > a.predicted ? r : a)) : null;
  const lo = rows.length ? rows.reduce((a, r) => (r.predicted < a.predicted ? r : a)) : null;

  return (
    <div className="space-y-5">
      <Section title="Next 24 hours" hint="A transparent statistical baseline: persistence blended with the typical daily PM2.5 cycle.">
        <div className="mb-5 flex gap-3 rounded-xl border p-3.5 text-[13.5px]" style={{ background: 'var(--surface-2)', borderColor: 'var(--line-soft)' }}>
          <Info className="mt-0.5 h-[18px] w-[18px] shrink-0 subtle" />
          <p className="subtle">
            The current level carries forward, and its memory fades with a 12-hour half-life as the usual hour-of-day PM2.5 swing takes over. It ignores wind, temperature inversions and
            stubble-burning, so treat it as a baseline trajectory. The shaded range is a heuristic that widens with time, not a fitted confidence interval.
          </p>
        </div>
        {rows.length ? <ForecastChart rows={rows} /> : <p className="py-10 text-center text-sm muted">Not enough live stations to forecast.</p>}
      </Section>

      <div className="grid gap-4 sm:grid-cols-3">
        <Stat label="Expected 24-hour average" value={avg ?? '–'} color={avg !== null ? categoryOf(avg).ink : undefined} sub={avg !== null ? categoryOf(avg).name : undefined} />
        <Stat label="Projected peak" value={hi?.predicted ?? '–'} color={hi ? categoryOf(hi.predicted).ink : undefined} sub={hi ? `around ${hi.label} IST` : undefined} />
        <Stat label="Projected low" value={lo?.predicted ?? '–'} color={lo ? categoryOf(lo.predicted).ink : undefined} sub={lo ? `around ${lo.label} IST` : undefined} />
      </div>
    </div>
  );
}
