import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity, BookOpen, BrainCircuit, Download, ExternalLink, Grid3x3, Lightbulb, Loader2, MapPin, Moon, Sparkles, Sun, TrendingUp, Users, Wind,
} from 'lucide-react';
import { AREAS, loadDataset, type Dataset } from './lib/data';
import { buildModel, type AreaFilter } from './lib/model';
import { fmtStamp } from './lib/time';
import { Overview } from './views/Overview';
import { MapTab } from './views/MapTab';
import { HeatmapTab } from './views/HeatmapTab';
import { TrendsTab } from './views/TrendsTab';
import { StationsTab } from './views/StationsTab';
import { ForecastTab } from './views/ForecastTab';
import { MlForecastTab } from './views/MlForecastTab';
import { InsightsTab } from './views/InsightsTab';
import { MethodTab } from './views/MethodTab';

const TABS = [
  { id: 'overview', label: 'Overview', icon: Activity },
  { id: 'map', label: 'Map', icon: MapPin },
  { id: 'heatmap', label: 'Heatmap', icon: Grid3x3 },
  { id: 'trends', label: 'Trends', icon: TrendingUp },
  { id: 'stations', label: 'Stations', icon: Users },
  { id: 'forecast', label: 'Forecast', icon: Sparkles },
  { id: 'mlforecast', label: 'ML Forecast', icon: BrainCircuit },
  { id: 'insights', label: 'Insights', icon: Lightbulb },
  { id: 'method', label: 'Method', icon: BookOpen },
] as const;
type TabId = (typeof TABS)[number]['id'];

const REPO = 'https://github.com/Divyanshukumar2005/delhi-aqi-pipeline';
const tabFromHash = (): TabId => {
  const h = window.location.hash.replace('#', '') as TabId;
  return TABS.some((t) => t.id === h) ? h : 'overview';
};

function initialTheme(): 'light' | 'dark' {
  try {
    const saved = localStorage.getItem('aqi-theme');
    if (saved === 'light' || saved === 'dark') return saved;
  } catch { /* storage unavailable */ }
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export default function App() {
  const [theme, setTheme] = useState<'light' | 'dark'>(initialTheme);
  const [data, setData] = useState<Dataset | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<TabId>(tabFromHash);
  const [area, setArea] = useState<AreaFilter>('All');
  const [compare, setCompare] = useState<string[]>([]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem('aqi-theme', theme); } catch { /* ignore */ }
  }, [theme]);

  const load = useCallback(() => {
    setError(null);
    loadDataset()
      .then((d) => {
        setData(d);
        setCompare((c) => (c.length ? c : d.stations.filter((s) => s.latest).slice(0, 3).map((s) => s.id)));
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Unknown error'));
  }, []);
  useEffect(load, [load]);

  useEffect(() => {
    const onHash = () => setTab(tabFromHash());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);
  const go = (t: TabId) => { window.location.hash = t; setTab(t); window.scrollTo({ top: 0 }); };

  const m = useMemo(() => (data ? buildModel(data.stations, area) : null), [data, area]);

  const downloadCsv = () => {
    if (!m) return;
    const q = (s: string) => `"${s.replace(/"/g, '""')}"`;
    const iso = (t: number) => new Date(t + 19800000).toISOString().slice(0, 19) + '+05:30';
    const lines = ['station,area,timestamp_ist,pm25,pm10,no2,o3,aqi_24h,category'];
    for (const s of m.stations) for (const r of s.readings)
      lines.push([q(s.name), s.area, iso(r.t), r.pm25 ?? '', r.pm10 ?? '', r.no2 ?? '', r.o3 ?? '', r.aqi ?? '', r.aqi === null ? '' : r.cat.name].join(','));
    const url = URL.createObjectURL(new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' }));
    const a = Object.assign(document.createElement('a'), { href: url, download: 'delhi_ncr_aqi.csv' });
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  };

  if (error) {
    return (
      <div className="grid min-h-screen place-items-center p-6">
        <div className="card max-w-md p-8 text-center">
          <h1 className="text-lg font-bold">Couldn’t load the air quality data</h1>
          <p className="mt-2 text-sm subtle">{error}. Check your connection and try again.</p>
          <button className="btn btn-solid mt-5" onClick={load}>Try again</button>
        </div>
      </div>
    );
  }

  if (!data || !m) {
    return (
      <div className="grid min-h-screen place-items-center p-6">
        <div className="text-center">
          <Loader2 className="mx-auto h-8 w-8 animate-spin subtle" />
          <p className="mt-4 font-semibold">Loading station readings</p>
          <p className="mt-1 text-sm muted">Computing the CPCB AQI for every monitor</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <header className="border-b" style={{ background: 'var(--surface)', borderColor: 'var(--line)' }}>
        <div className="mx-auto flex max-w-[1320px] flex-wrap items-center justify-between gap-4 px-4 py-4 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-xl" style={{ background: 'var(--ink)', color: 'var(--surface)' }}><Wind className="h-5 w-5" /></div>
            <div>
              <h1 className="text-[19px] font-bold leading-tight tracking-tight">Delhi-NCR Air Quality</h1>
              <p className="text-[13px] muted">{data.stations.length} government monitors · CPCB National AQI</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2 text-[13px] subtle" title={data.fromLive ? 'Fetched from the live data pipeline' : 'Live source unreachable, showing bundled snapshot'}>
              <span className={`h-2 w-2 rounded-full ${data.fromLive ? 'live-dot' : ''}`} style={{ background: data.fromLive ? 'var(--aqi-0)' : 'var(--aqi-3)' }} />
              {data.fromLive ? 'Updated' : 'Snapshot'} {fmtStamp(data.maxT)}
            </div>
            <button className="btn" onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')} aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}>
              {theme === 'light' ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
              {theme === 'light' ? 'Dark' : 'Light'}
            </button>
            <button className="btn btn-solid" onClick={downloadCsv}><Download className="h-4 w-4" />Export CSV</button>
          </div>
        </div>
      </header>

      <nav className="sticky top-0 z-40 border-b backdrop-blur" style={{ background: 'color-mix(in srgb, var(--surface) 92%, transparent)', borderColor: 'var(--line)' }} aria-label="Sections">
        <div role="tablist" className="no-scrollbar mx-auto flex max-w-[1320px] overflow-x-auto px-2 lg:px-6">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button key={id} role="tab" aria-selected={tab === id} className="tab" onClick={() => go(id)}>
              <Icon className="h-4 w-4" />{label}
            </button>
          ))}
        </div>
      </nav>

      <main className="mx-auto max-w-[1320px] px-4 pb-16 pt-6 lg:px-8">
        {tab !== 'method' && tab !== 'stations' && tab !== 'mlforecast' && (
          <div className="mb-5 flex flex-wrap items-center gap-2" role="group" aria-label="Filter by area">
            <span className="mr-1 text-[13px] muted">Area</span>
            {(['All', ...AREAS] as AreaFilter[]).map((a) => (
              <button key={a} className="chip" aria-pressed={area === a} onClick={() => setArea(a)}>{a}</button>
            ))}
          </div>
        )}

        {tab === 'overview' && <Overview m={m} onArea={(a) => setArea(a)} />}
        {tab === 'map' && <MapTab m={m} theme={theme} onCompare={(id) => { setCompare((c) => (c.includes(id) ? c : [id, ...c].slice(0, 4))); go('stations'); }} />}
        {tab === 'heatmap' && <HeatmapTab m={m} />}
        {tab === 'trends' && <TrendsTab m={m} />}
        {tab === 'stations' && <StationsTab m={buildModel(data.stations, 'All')} all={data.stations} ids={compare} setIds={setCompare} />}
        {tab === 'forecast' && <ForecastTab m={m} />}
        {tab === 'mlforecast' && <MlForecastTab />}
        {tab === 'insights' && <InsightsTab m={m} onCsv={downloadCsv} />}
        {tab === 'method' && <MethodTab />}
      </main>

      <footer className="border-t" style={{ borderColor: 'var(--line)' }}>
        <div className="mx-auto flex max-w-[1320px] flex-wrap items-center justify-between gap-3 px-4 py-6 text-[13px] muted lg:px-8">
          <p>Data: OpenAQ v3 (government monitors). Basemap © OpenStreetMap contributors, © CARTO. Index: CPCB NAQI 2014.</p>
          <a className="inline-flex items-center gap-1.5 font-semibold subtle hover:underline" href={REPO} target="_blank" rel="noreferrer">Source and data pipeline<ExternalLink className="h-3.5 w-3.5" /></a>
        </div>
      </footer>
    </div>
  );
}
