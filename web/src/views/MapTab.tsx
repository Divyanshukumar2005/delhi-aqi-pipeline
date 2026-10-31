import { useMemo, useState } from 'react';
import { Crosshair, Globe2, Search, GitCompareArrows } from 'lucide-react';
import { MapCanvas, type MapView } from '../components/MapCanvas';
import { Spark } from '../components/charts';
import { CatBadge, Section } from '../components/ui';
import { CATEGORIES, categoryOf } from '../lib/aqi';
import { fmtStamp } from '../lib/time';
import type { Model } from '../lib/model';

export function MapTab({ m, theme, onCompare }: { m: Model; theme: 'light' | 'dark'; onCompare: (id: string) => void }) {
  const [view, setView] = useState<MapView>('ncr');
  const [selected, setSelected] = useState<string | null>(null);
  const [q, setQ] = useState('');

  const list = useMemo(() => {
    const s = q.trim().toLowerCase();
    return m.stations
      .filter((st) => st.latest)
      .filter((st) => !s || st.short.toLowerCase().includes(s) || st.area.toLowerCase().includes(s))
      .sort((a, b) => b.latest!.aqi! - a.latest!.aqi!);
  }, [m.stations, q]);

  const sel = m.stations.find((s) => s.id === selected) ?? null;
  const unmapped = m.stations.filter((s) => s.lat === null).length;

  return (
    <div className="grid gap-5 lg:grid-cols-12">
      <Section
        className="lg:col-span-8"
        title="Monitoring stations"
        hint="Each pin shows a station's latest 24-hour AQI. Faded pins have not reported in the last 3 hours."
        right={
          <div className="flex gap-1.5" role="group" aria-label="Map extent">
            <button className="chip" aria-pressed={view === 'ncr'} onClick={() => setView('ncr')}><Crosshair className="h-3.5 w-3.5" />Delhi-NCR</button>
            <button className="chip" aria-pressed={view === 'india'} onClick={() => setView('india')}><Globe2 className="h-3.5 w-3.5" />India</button>
          </div>
        }
      >
        <div className="relative h-[560px] overflow-hidden rounded-xl border" style={{ borderColor: 'var(--line)' }}>
          <MapCanvas stations={m.stations} selectedId={selected} onSelect={setSelected} theme={theme} view={view} cityAqi={m.cityAqi} cityCat={m.cat} />
          <div className="pointer-events-none absolute left-3 top-3 z-[500] rounded-xl border p-2.5 text-xs backdrop-blur" style={{ background: 'color-mix(in srgb, var(--surface) 88%, transparent)', borderColor: 'var(--line)' }}>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1">
              {CATEGORIES.map((c) => (
                <div key={c.name} className="flex items-center gap-1.5 font-medium">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: c.fill }} />
                  {c.name}
                </div>
              ))}
            </div>
          </div>
        </div>
        {unmapped > 0 && <p className="mt-2 text-xs muted">{unmapped} station{unmapped > 1 ? 's have' : ' has'} no coordinates and appear only in the list.</p>}
      </Section>

      <div className="flex flex-col gap-5 lg:col-span-4 lg:h-0 lg:min-h-full">
        {sel && sel.latest && (
          <section className="card p-5">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h3 className="truncate text-[17px] font-bold tracking-tight">{sel.short}</h3>
                <p className="text-[13px] muted">{sel.area}{sel.agency ? ` · ${sel.agency}` : ''}</p>
              </div>
              <div className="num text-4xl font-semibold leading-none" style={{ color: sel.latest.cat.ink }}>{sel.latest.aqi}</div>
            </div>
            <div className="mt-2 flex items-center justify-between">
              <CatBadge cat={sel.latest.cat} />
              <span className="text-xs muted">{fmtStamp(sel.latest.t)}</span>
            </div>
            <div className="mt-3"><Spark values={sel.readings.slice(-72).map((r) => ({ t: r.t, aqi: r.aqi }))} /></div>
            <dl className="mt-1 grid grid-cols-4 gap-2 text-center">
              {([['PM2.5', sel.latest.pm25], ['PM10', sel.latest.pm10], ['NO2', sel.latest.no2], ['O3', sel.latest.o3]] as const).map(([k, v]) => (
                <div key={k} className="card-flat py-2">
                  <dt className="text-[11px] muted">{k}</dt>
                  <dd className="num text-[15px] font-semibold">{v === null ? '–' : Math.round(v)}</dd>
                </div>
              ))}
            </dl>
            <button className="btn mt-4 w-full justify-center" onClick={() => onCompare(sel.id)}><GitCompareArrows className="h-4 w-4" />Open in Stations</button>
          </section>
        )}

        <section className="card flex min-h-[420px] flex-1 flex-col p-5 lg:min-h-0">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="h-section">Ranking</h3>
            <span className="text-xs muted">Most to least polluted</span>
          </div>
          <label className="relative mb-3 block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 muted" />
            <input className="field w-full pl-9" placeholder="Search station or area" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search stations" />
          </label>
          <ul className="no-scrollbar -mr-1 flex-1 space-y-1.5 overflow-y-auto pr-1">
            {list.map((s, i) => {
              const cat = categoryOf(s.latest!.aqi);
              const active = s.id === selected;
              return (
                <li key={s.id}>
                  <button onClick={() => { setSelected(s.id); setView('ncr'); }} className="w-full rounded-xl border p-2.5 text-left transition-colors hover:bg-[var(--surface-2)]" style={{ borderColor: active ? 'var(--ink)' : 'var(--line-soft)', background: active ? 'var(--surface-2)' : undefined }}>
                    <div className="flex items-center justify-between gap-2 text-[13px]">
                      <span className="flex min-w-0 items-center gap-2">
                        <span className="num w-6 text-xs muted">{i + 1}</span>
                        <span className="truncate font-semibold">{s.short}</span>
                        <span className="shrink-0 text-xs muted">{s.area}</span>
                      </span>
                      <span className="num text-[15px] font-semibold" style={{ color: cat.ink }}>{s.latest!.aqi}</span>
                    </div>
                    <div className="mt-1.5 h-1.5 overflow-hidden rounded-full" style={{ background: 'var(--line-soft)' }}>
                      <div className="h-full rounded-full" style={{ width: `${Math.min(100, (s.latest!.aqi! / 500) * 100)}%`, background: cat.fill }} />
                    </div>
                  </button>
                </li>
              );
            })}
            {!list.length && <li className="py-6 text-center text-sm muted">No station matches “{q}”.</li>}
          </ul>
        </section>
      </div>
    </div>
  );
}
