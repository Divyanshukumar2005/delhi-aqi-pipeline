import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
// Imported here as well as in index.css so the map never renders unstyled, whatever the CSS order.
import 'leaflet/dist/leaflet.css';
import type { Station } from '../lib/data';
import type { Category } from '../lib/aqi';

export type MapView = 'ncr' | 'india';

interface Props {
  stations: Station[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  theme: 'light' | 'dark';
  view: MapView;
  cityAqi: number | null;
  cityCat: Category;
}

interface Basemap { url: string; attr: string; subdomains: string }
const CARTO_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';
const OSM: Basemap = {
  url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  attr: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  subdomains: 'abc',
};
/** CARTO first (matches the theme); OpenStreetMap is the fallback if CARTO tiles are blocked or fail. */
const BASEMAPS: Record<'light' | 'dark', Basemap[]> = {
  light: [{ url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', attr: CARTO_ATTR, subdomains: 'abcd' }, OSM],
  dark: [{ url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', attr: CARTO_ATTR, subdomains: 'abcd' }, OSM],
};
const DELHI: [number, number] = [28.6139, 77.209];
const esc = (s: string) => s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);

function pin(aqi: number, cat: Category, size: number, extra = '') {
  return L.divIcon({
    className: '',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    html: `<div class="aqi-pin ${extra}" style="width:${size}px;height:${size}px;background:${cat.fill};color:${cat.on}">${aqi}</div>`,
  });
}

export function MapCanvas({ stations, selectedId, onSelect, theme, view, cityAqi, cityCat }: Props) {
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<L.Map | null>(null);
  const tiles = useRef<L.TileLayer | null>(null);
  const layer = useRef<L.LayerGroup | null>(null);
  const fitted = useRef(false);
  const [tilesFailed, setTilesFailed] = useState(false);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  // create the map once
  useEffect(() => {
    if (!el.current) return;
    const m = L.map(el.current, { zoomControl: false, scrollWheelZoom: false, minZoom: 4, maxZoom: 16 }).setView(DELHI, 10);
    L.control.zoom({ position: 'bottomright' }).addTo(m);
    layer.current = L.layerGroup().addTo(m);
    map.current = m;
    const ro = new ResizeObserver(() => m.invalidateSize());
    ro.observe(el.current);
    // the tab can mount before layout has settled; re-measure once it has
    const settle = window.setTimeout(() => m.invalidateSize(), 150);
    // wheel zoom only after the map has been clicked, so the page can still scroll
    m.on('click focus', () => m.scrollWheelZoom.enable());
    m.on('mouseout', () => m.scrollWheelZoom.disable());
    return () => { window.clearTimeout(settle); ro.disconnect(); m.remove(); map.current = null; fitted.current = false; };
  }, []);

  // basemap follows the theme; falls back to the next provider when most tiles fail to load
  useEffect(() => {
    const m = map.current;
    if (!m) return;
    let alive = true;
    let layerNow: L.TileLayer | null = null;
    const use = (i: number) => {
      layerNow?.remove();
      const b = BASEMAPS[theme][i];
      if (!b) { setTilesFailed(true); return; }
      let ok = 0, bad = 0;
      const tl = L.tileLayer(b.url, { attribution: b.attr, subdomains: b.subdomains, maxZoom: 19, crossOrigin: true });
      tl.on('tileload', () => { ok++; if (alive) setTilesFailed(false); });
      tl.on('tileerror', () => {
        bad++;
        if (alive && ok === 0 && bad >= 4) use(i + 1);
      });
      tl.addTo(m);
      layerNow = tl;
      tiles.current = tl;
    };
    setTilesFailed(false);
    use(0);
    return () => { alive = false; layerNow?.remove(); };
  }, [theme]);

  // markers
  useEffect(() => {
    const m = map.current, g = layer.current;
    if (!m || !g) return;
    g.clearLayers();

    if (view === 'india') {
      if (cityAqi !== null) {
        L.marker(DELHI, { icon: pin(cityAqi, cityCat, 46), keyboard: false })
          .bindTooltip('Delhi-NCR (network average)', { direction: 'top', offset: [0, -22], permanent: true })
          .addTo(g);
      }
      return;
    }

    const placed = stations.filter((s) => s.lat !== null && s.lon !== null && s.latest);
    for (const s of placed) {
      const sel = s.id === selectedId;
      const mk = L.marker([s.lat!, s.lon!], {
        icon: pin(s.latest!.aqi!, s.latest!.cat, sel ? 40 : 34, `${s.live ? '' : 'stale'} ${sel ? 'selected' : ''}`),
        zIndexOffset: sel ? 1000 : Math.round(s.latest!.aqi!),
        title: `${s.short}: AQI ${s.latest!.aqi}`,
      });
      mk.bindTooltip(`<strong>${esc(s.short)}</strong><br/>${esc(s.area)} · AQI ${s.latest!.aqi} · ${esc(s.latest!.cat.name)}${s.live ? '' : ' · offline'}`, { direction: 'top', offset: [0, -16] });
      mk.on('click', () => onSelectRef.current(s.id));
      mk.addTo(g);
    }

    if (!fitted.current && placed.length) {
      m.fitBounds(L.latLngBounds(placed.map((s) => [s.lat!, s.lon!] as [number, number])), { padding: [48, 48] });
      fitted.current = true;
    }
  }, [stations, selectedId, view, cityAqi, cityCat]);

  // camera
  useEffect(() => {
    const m = map.current;
    if (!m) return;
    if (view === 'india') {
      m.flyTo([23.2, 79.4], 5, { duration: 1.1 });
    } else {
      const placed = stations.filter((s) => s.lat !== null && s.lon !== null);
      if (placed.length) m.flyToBounds(L.latLngBounds(placed.map((s) => [s.lat!, s.lon!] as [number, number])), { padding: [48, 48], duration: 1.1 });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view]);

  useEffect(() => {
    const m = map.current;
    const s = stations.find((x) => x.id === selectedId);
    if (m && s && s.lat !== null && s.lon !== null && view === 'ncr') m.panTo([s.lat, s.lon], { animate: true, duration: 0.5 });
  }, [selectedId, stations, view]);

  return (
    <div className="relative h-full w-full">
      {/* explicit size: Leaflet draws nothing into a zero-height box */}
      <div ref={el} className="absolute inset-0" style={{ minHeight: 320 }} />
      {tilesFailed && (
        <div className="pointer-events-none absolute inset-x-3 bottom-3 z-[500] rounded-xl border px-3 py-2 text-xs subtle backdrop-blur" style={{ background: 'color-mix(in srgb, var(--surface) 90%, transparent)', borderColor: 'var(--line)' }}>
          The street basemap could not be loaded (network or an ad-blocker). Stations are still placed by their coordinates.
        </div>
      )}
    </div>
  );
}
