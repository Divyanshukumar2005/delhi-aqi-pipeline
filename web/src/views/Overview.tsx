import { ShieldAlert } from 'lucide-react';
import { Dial } from '../components/Dial';
import { CityTrend } from '../components/charts';
import { CatBadge, Section, Stat } from '../components/ui';
import { soft } from '../lib/aqi';
import { fmtHour } from '../lib/time';
import type { Model } from '../lib/model';
import type { AreaFilter } from '../lib/model';

export function Overview({ m, onArea }: { m: Model; onArea: (a: AreaFilter) => void }) {
  const { cat } = m;
  return (
    <div className="space-y-5">
      <div className="grid gap-5 lg:grid-cols-12">
        <section className="card flex flex-col items-center p-6 lg:col-span-5">
          <div className="mb-1 w-full">
            <h2 className="h-section">Delhi-NCR right now</h2>
            <p className="text-[13px] subtle">Average of {m.reporting.length} stations that reported in the last 3 hours</p>
          </div>
          <Dial value={m.cityAqi} cat={cat} />
          <CatBadge cat={cat} />
        </section>

        <div className="flex flex-col gap-5 lg:col-span-7">
          <section className="card flex-1 p-6" style={{ borderLeft: `6px solid ${cat.fill}` }}>
            <CatBadge cat={cat} label={`${cat.name} · AQI ${cat.min}–${cat.max}`} />
            <h2 className="mt-3 max-w-[22ch] text-[28px] font-bold leading-[1.15] tracking-tight sm:text-[34px]">{cat.headline}</h2>
            <p className="mt-3 max-w-[56ch] text-[15px] subtle">{cat.action}</p>
            <div className="mt-5 flex gap-3 rounded-xl p-3.5 text-[14px]" style={{ background: soft(cat, 10) }}>
              <ShieldAlert className="mt-0.5 h-[18px] w-[18px] shrink-0" style={{ color: cat.ink }} />
              <div>
                <span className="font-semibold">Sensitive groups. </span>
                <span className="subtle">{cat.sensitive}</span>
              </div>
            </div>
            <p className="mt-3 text-xs muted">General guidance based on the CPCB advisory bands. It is not medical advice.</p>
          </section>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {m.areaAvg.map((a) => (
              <button key={a.area} onClick={() => onArea(a.area)} className="card p-3.5 text-left transition-colors hover:border-[var(--ink-3)]" style={{ borderTop: `4px solid ${a.aqi === null ? 'var(--line)' : a.cat.fill}` }}>
                <div className="text-[13px] font-semibold">{a.area}</div>
                <div className="num mt-1 text-2xl font-semibold leading-none" style={{ color: a.aqi === null ? 'var(--ink-3)' : a.cat.ink }}>{a.aqi ?? '–'}</div>
                <div className="mt-1.5 text-xs muted">{a.count ? `${a.cat.name} · ${a.count} station${a.count > 1 ? 's' : ''}` : 'No live stations'}</div>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Most polluted now" value={m.worst ? m.worst.latest!.aqi : '–'} color={m.worst?.latest!.cat.ink} sub={m.worst ? `${m.worst.short}, ${m.worst.area}` : undefined} />
        <Stat label="Cleanest now" value={m.cleanest ? m.cleanest.latest!.aqi : '–'} color={m.cleanest?.latest!.cat.ink} sub={m.cleanest ? `${m.cleanest.short}, ${m.cleanest.area}` : undefined} />
        <Stat label="Station-hours Poor or worse" value={`${m.pctPoor.toFixed(1)}%`} sub={`${m.share.total.toLocaleString('en-IN')} hourly readings`} />
        <Stat label="Cleanest time of day" value={m.clean ? fmtHour(m.clean.hour) : '–'} sub={m.peak ? `PM2.5 peaks near ${fmtHour(m.peak.hour)} IST` : undefined} />
      </div>

      <Section title="The last two weeks" hint="Hourly city-wide AQI. Shaded bands mark the CPCB categories, from Good at the bottom to Severe at the top.">
        <CityTrend data={m.gapped} gaps={m.gaps} height={280} />
        {m.gaps.length > 0 && <p className="mt-3 text-xs muted">Grey bands are windows when fewer than five monitors reported, so no city average is shown.</p>}
      </Section>
    </div>
  );
}
