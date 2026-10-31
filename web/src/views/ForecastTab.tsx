import { useMemo } from 'react';
import { CatBadge, Section } from '../components/ui';
import { ForecastChart, type ForecastRow } from '../components/charts';
import { categoryOf } from '../lib/aqi';
import { buildForecast } from '../lib/forecast';
import { fmtHour, fmtShort, fmtStamp } from '../lib/time';
import type { Model } from '../lib/model';

function Kpi({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div className="card p-4">
      <div className="text-[13px] muted">{label}</div>
      <div className="num mt-1.5 text-[28px] font-semibold leading-tight" style={{ color: color ?? 'var(--ink)' }}>{value}</div>
      {sub && <div className="mt-0.5 text-[13px] subtle">{sub}</div>}
    </div>
  );
}

export function ForecastTab({ m }: { m: Model }) {
  const fc = useMemo(
    () => buildForecast(m.ticks.map((t) => ({ t: t.t, pm25: t.pm25, pm10: t.pm10 }))),
    [m.ticks],
  );

  const view = useMemo(() => {
    if (!fc) return null;
    // Anchor to the AQI shown on the Overview dial, so the two pages never disagree about "now".
    const last = fc.recent[fc.recent.length - 1];
    const shift = m.cityAqi !== null && last ? m.cityAqi - last.aqi : 0;
    const clamp = (v: number) => Math.min(500, Math.max(0, Math.round(v + shift)));
    const points = fc.points.map((p) => ({ ...p, aqi: clamp(p.aqi), lo: clamp(p.lo), hi: clamp(p.hi) }));
    const recent = fc.recent.map((r) => ({ t: r.t, aqi: clamp(r.aqi) }));
    const now = recent.length ? recent[recent.length - 1].aqi : points[0].aqi;

    const rows: ForecastRow[] = [
      ...recent.map((r, i) => (i === recent.length - 1 ? { t: r.t, observed: r.aqi, predicted: r.aqi, band: [r.aqi, r.aqi] as [number, number] } : { t: r.t, observed: r.aqi })),
      ...points.map((p) => ({ t: p.t, predicted: p.aqi, band: [p.lo, p.hi] as [number, number] })),
    ];
    const avg = Math.round(points.reduce((a, p) => a + p.aqi, 0) / points.length);
    const hi = points.reduce((a, p) => (p.aqi > a.aqi ? p : a));
    const lo = points.reduce((a, p) => (p.aqi < a.aqi ? p : a));
    const dir = points[points.length - 1].aqi - now;
    return { points, rows, now, avg, hi, lo, dir };
  }, [fc, m.cityAqi]);

  if (!fc || !view) {
    return (
      <Section title="Next 24 hours">
        <p className="py-10 text-center text-sm muted">There is not enough continuous history yet to fit the forecast model. It needs about three days of hourly readings.</p>
      </Section>
    );
  }

  const { points, rows, now, avg, hi, lo } = view;
  const trend = view.dir > 12 ? 'rising' : view.dir < -12 ? 'falling' : 'roughly steady';
  const sixHourly = points.filter((_, i) => i % 3 === 2);

  return (
    <div className="space-y-5">
      <Section
        title="Next 24 hours"
        hint={`Hourly outlook for the city AQI, starting from the latest reading at ${fmtStamp(fc.origin)}. The solid line is what was measured, the dashed line is the forecast and the shaded band is the 80% range.`}
        right={<CatBadge cat={categoryOf(avg)} label={`Expected ${categoryOf(avg).name}`} />}
      >
        <ForecastChart rows={rows} origin={fc.origin} />
      </Section>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Kpi label="Now" value={now} color={categoryOf(now).ink} sub={categoryOf(now).name} />
        <Kpi label="24-hour average" value={avg} color={categoryOf(avg).ink} sub={`${categoryOf(avg).name}, ${trend}`} />
        <Kpi label="Expected peak" value={hi.aqi} color={categoryOf(hi.aqi).ink} sub={`${fmtHour(hi.hour)} IST, range ${hi.lo}–${hi.hi}`} />
        <Kpi label="Expected low" value={lo.aqi} color={categoryOf(lo.aqi).ink} sub={`${fmtHour(lo.hour)} IST, range ${lo.lo}–${lo.hi}`} />
      </div>

      <Section title="Hour by hour" hint="Every third hour of the forecast with its 80% range. Times are IST.">
        <div className="scroll-x">
          <table className="tbl">
            <thead>
              <tr><th>Time</th><th className="text-right">Forecast AQI</th><th className="text-right">80% range</th><th>Category</th></tr>
            </thead>
            <tbody>
              {sixHourly.map((p) => (
                <tr key={p.t}>
                  <td className="num font-medium">{fmtShort(p.t)}</td>
                  <td className="num text-right font-semibold" style={{ color: categoryOf(p.aqi).ink }}>{p.aqi}</td>
                  <td className="num text-right muted">{p.lo}–{p.hi}</td>
                  <td><CatBadge cat={categoryOf(p.aqi)} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <div className="grid gap-5 lg:grid-cols-2">
        <Section title="How the forecast works">
          <ol className="space-y-3 text-[14px] leading-relaxed subtle">
            <li>
              <span className="font-semibold" style={{ color: 'var(--ink)' }}>Hourly PM2.5 and PM10.</span>{' '}
              Each is modelled in log space as a recent 24-hour level, plus the typical hour-of-day cycle learned from this data, plus a leftover that fades
              with a persistence of {fc.phi.toFixed(2)} per hour.
            </li>
            <li>
              <span className="font-semibold" style={{ color: 'var(--ink)' }}>Same maths as the published AQI.</span>{' '}
              At each future hour the previous 24 hours (measured and forecast) are averaged and converted with the CPCB breakpoints. That is why the
              line moves smoothly instead of jumping.
            </li>
            <li>
              <span className="font-semibold" style={{ color: 'var(--ink)' }}>Uncertainty.</span>{' '}
              400 simulated futures, each with random hourly shocks sized from past errors (spread {fc.sigma.toFixed(2)} in log units), give the 80% band.
            </li>
          </ol>
          <p className="mt-4 text-xs muted">
            It uses only past readings. Wind, mixing height, crop-residue burning and festival emissions are not inputs, so sudden changes in weather
            will fall outside the band. Use it as a baseline, not as an advisory.
          </p>
        </Section>

        <Section title="How well it has done" hint="Replayed on this dataset: for each past hour the model saw only earlier data, then its forecast was compared with what was measured.">
          {fc.backtest ? (
            <>
              <table className="tbl">
                <thead>
                  <tr><th>Look-ahead</th><th className="text-right">This model</th><th className="text-right">“Stays the same”</th><th className="text-right">Improvement</th></tr>
                </thead>
                <tbody>
                  {fc.backtest.rows.map((r) => (
                    <tr key={r.horizon}>
                      <td className="font-medium">{r.horizon} hours</td>
                      <td className="num text-right font-semibold">±{r.mae.toFixed(0)}</td>
                      <td className="num text-right muted">±{r.baseline.toFixed(0)}</td>
                      <td className="num text-right" style={{ color: r.skill > 0 ? 'var(--aqi-0-ink)' : 'var(--aqi-4-ink)' }}>{r.skill > 0 ? '+' : ''}{(r.skill * 100).toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mt-3 text-xs muted">
                Mean absolute error in AQI points over {fc.backtest.origins} forecast start times. The comparison column simply repeats the latest value.
                Accuracy falls with look-ahead, as it should: a day ahead the weather matters more than the pattern.
              </p>
            </>
          ) : (
            <p className="text-sm muted">Not enough history to replay yet. This panel fills in once there are several days of continuous readings.</p>
          )}
        </Section>
      </div>
    </div>
  );
}
