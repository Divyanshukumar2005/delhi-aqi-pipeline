import { ArrowRight } from 'lucide-react';
import { Section } from '../components/ui';
import { BREAKPOINTS, CATEGORIES } from '../lib/aqi';

const STEPS = [
  { t: 'OpenAQ v3 API', d: 'Hourly PM2.5, PM10, NO2 and O3 from government monitors across Delhi-NCR.' },
  { t: 'GitHub Actions', d: 'A scheduled pipeline fetches and cleans the data three times a day and commits JSON to the repo.' },
  { t: 'Static JSON', d: 'The dashboard reads the newest files straight from GitHub, so it updates without a redeploy. A bundled copy is the fallback.' },
  { t: 'React + Vite on Vercel', d: 'AQI is computed in the browser from the raw concentrations, so every number can be traced back.' },
];

export function MethodTab() {
  return (
    <div className="space-y-5">
      <Section title="Data pipeline" hint="Four stages, each one simple enough to debug on its own.">
        <ol className="grid gap-3 md:grid-cols-4">
          {STEPS.map((s, i) => (
            <li key={s.t} className="card-flat relative p-4">
              <div className="num text-xs muted">Stage {i + 1}</div>
              <div className="mt-1 font-semibold">{s.t}</div>
              <p className="mt-1 text-[13px] subtle">{s.d}</p>
              {i < STEPS.length - 1 && <ArrowRight className="absolute -right-[11px] top-1/2 z-10 hidden h-4 w-4 -translate-y-1/2 rounded-full p-0.5 md:block" style={{ background: 'var(--surface)', color: 'var(--ink-3)' }} />}
            </li>
          ))}
        </ol>
      </Section>

      <div className="grid gap-5 lg:grid-cols-2">
        <Section title="How AQI is calculated" hint="India’s National AQI (CPCB, 2014), applied to PM2.5 and PM10.">
          <ul className="space-y-2.5 text-[14px] leading-relaxed subtle">
            <li>Take the rolling 24-hour mean of each pollutant. A mean needs at least 16 valid hourly values, as CPCB requires.</li>
            <li>Convert each mean to a sub-index by linear interpolation between the breakpoints in the table.</li>
            <li>The AQI is the highest sub-index, capped at 500. The city figure is the mean of stations that reported in the last 3 hours.</li>
          </ul>
        </Section>
        <Section title="Known limits">
          <ul className="list-disc space-y-2.5 pl-5 text-[14px] leading-relaxed subtle">
            <li>Only PM2.5 and PM10 feed the AQI here. NO2, O3, CO, SO2 and NH3 sub-indices are not included.</li>
            <li>Some monitors are missing from the station list, so their map positions are approximate.</li>
            <li>When monitors stop reporting for hours or days, charts draw a dashed interpolated line across the stretch. Heatmaps leave out days with no coverage. Nothing in the tables or statistics is interpolated.</li>
            <li>The 24-hour forecast uses past readings only (no weather inputs). Its accuracy against a “stays the same” baseline is shown on the Forecast tab.</li>
            <li>The ML Forecast tab shows a trained model’s 6, 12 and 24 hour predictions. Its error figures come from a 28-day back-test (4 rolling 7-day windows), which is short, so small differences between models are within noise.</li>
            <li>The history covers about two weeks, which is short for seasonal conclusions.</li>
          </ul>
        </Section>
      </div>

      <Section title="CPCB breakpoints" hint="Concentrations in µg/m³ mapped to AQI.">
        <div className="scroll-x">
          <table className="tbl">
            <thead><tr><th>Category</th><th className="text-right">AQI</th><th className="text-right">PM2.5 (24h)</th><th className="text-right">PM10 (24h)</th></tr></thead>
            <tbody>
              {CATEGORIES.map((c, i) => (
                <tr key={c.name}>
                  <td className="font-semibold"><span className="mr-2 inline-block h-2.5 w-2.5 rounded-full" style={{ background: c.fill }} />{c.name}</td>
                  <td className="num text-right">{c.min}–{c.max}</td>
                  <td className="num text-right">{BREAKPOINTS.pm25[i][0]}–{BREAKPOINTS.pm25[i][1]}</td>
                  <td className="num text-right">{BREAKPOINTS.pm10[i][0]}–{BREAKPOINTS.pm10[i][1]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
    </div>
  );
}
