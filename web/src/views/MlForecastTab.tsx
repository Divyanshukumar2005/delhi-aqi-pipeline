import { useEffect, useState } from 'react';
import { CatBadge, Section } from '../components/ui';
import { categoryOf } from '../lib/aqi';
import { loadMlForecast, type MlForecast } from '../lib/data';
import { fmtShort, fmtStamp } from '../lib/time';

const BACKTEST = '28-day back-test (4 rolling 7-day windows)';

function Kpi({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div className="card p-4">
      <div className="text-[13px] muted">{label}</div>
      <div className="num mt-1.5 text-[28px] font-semibold leading-tight" style={{ color: color ?? 'var(--ink)' }}>{value}</div>
      {sub && <div className="mt-0.5 text-[13px] subtle">{sub}</div>}
    </div>
  );
}

const NOT_YET = (
  <Section title="ML forecast">
    <p className="py-10 text-center text-sm muted">Not available yet. The model forecast appears here once the data pipeline has produced it.</p>
  </Section>
);

export function MlForecastTab() {
  const [fc, setFc] = useState<MlForecast | null | undefined>(undefined); // undefined = loading, null = no file

  useEffect(() => {
    let alive = true;
    loadMlForecast().then((f) => { if (alive) setFc(f); });
    return () => { alive = false; };
  }, []);

  if (fc === undefined) {
    return <Section title="ML forecast"><p className="py-10 text-center text-sm muted">Loading the model forecast</p></Section>;
  }
  if (fc === null) return NOT_YET;
  if (!fc.available) {
    return (
      <Section title="ML forecast">
        <p className="py-10 text-center text-sm muted">
          Not available right now. {fc.reason ?? 'The saved models or the recent data could not be used.'}
          {fc.generated_at && <span className="mt-1 block text-xs">Checked {fmtStamp(Date.parse(fc.generated_at))}</span>}
        </p>
      </Section>
    );
  }

  const origin = Date.parse(fc.origin_ts);
  const now = fc.current_aqi;
  const horizons = [...fc.horizons].sort((a, b) => a.h - b.h);
  const withBaseline = horizons.filter((r) => typeof r.persistence_mae === 'number');

  return (
    <div className="space-y-5">
      <Section
        title="Next 6, 12 and 24 hours"
        hint={`City-mean AQI predicted by a trained model from the reading at ${fmtStamp(origin)}. Each card shows the predicted value, its CPCB category and the model's average miss on the ${BACKTEST}.`}
        right={<CatBadge cat={categoryOf(now)} label={`Now ${categoryOf(now).name}`} />}
      >
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <Kpi label="Now" value={now} color={categoryOf(now).ink} sub={categoryOf(now).name} />
          {horizons.map((r) => {
            const cat = categoryOf(r.predicted_aqi);
            return (
              <div key={r.h} className="card p-4">
                <div className="text-[13px] muted">In {r.h} hours</div>
                <div className="num mt-1.5 text-[28px] font-semibold leading-tight" style={{ color: cat.ink }}>{r.predicted_aqi}</div>
                <div className="mt-1.5"><CatBadge cat={cat} /></div>
                <div className="mt-2 text-[13px] subtle">{fmtShort(origin + r.h * 3600 * 1000)} IST</div>
                <div className="text-[13px] muted">{r.model.replace('_', ' ')}, typical miss ±{r.backtest_mae.toFixed(0)}</div>
              </div>
            );
          })}
        </div>
        <p className="mt-4 text-xs muted">Generated {fmtStamp(Date.parse(fc.generated_at))}. Predictions are for the city-wide mean, not for one monitor, and are not a health advisory.</p>
      </Section>

      <Section
        title="How well it did in the back-test"
        hint={`Mean absolute error in AQI points (lower is better), replayed on the ${BACKTEST}. “Same as now” predicts that the AQI stays where it is.`}
      >
        {withBaseline.length ? (
          <div className="scroll-x">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Look-ahead</th>
                  <th className="text-right">“Same as now”</th>
                  <th className="text-right">Best model</th>
                  <th className="text-right">Model error vs “same as now”</th>
                </tr>
              </thead>
              <tbody>
                {withBaseline.map((r) => {
                  const base = r.persistence_mae as number;
                  const change = base > 0 ? (r.backtest_mae / base - 1) * 100 : 0;
                  return (
                    <tr key={r.h}>
                      <td className="font-medium">{r.h} hours</td>
                      <td className="num text-right muted">±{base.toFixed(1)}</td>
                      <td className="num text-right font-semibold">±{r.backtest_mae.toFixed(1)} <span className="font-sans text-xs font-normal muted">{r.model.replace('_', ' ')}</span></td>
                      <td className="num text-right">{change > 0 ? '+' : ''}{change.toFixed(0)}%</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm muted">The back-test comparison is not in this file yet.</p>
        )}
        <p className="mt-3 text-xs muted">Back-test on 28 days; small differences are within noise. A negative percentage means a smaller error than “same as now”.</p>
      </Section>
    </div>
  );
}
