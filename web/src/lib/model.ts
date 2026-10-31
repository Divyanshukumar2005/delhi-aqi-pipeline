import { categoryOf, type Category } from './aqi';
import {
  AREAS, categoryShare, cityDaily, cityHourly, diurnal, type Area, type Station,
} from './data';

export type AreaFilter = 'All' | Area;

export function buildModel(all: Station[], area: AreaFilter) {
  const stations = area === 'All' ? all : all.filter((s) => s.area === area);
  const reporting = stations.filter((s) => s.live && s.latest);

  const cityAqi = reporting.length ? Math.round(reporting.reduce((a, s) => a + s.latest!.aqi!, 0) / reporting.length) : null;
  const cat: Category = categoryOf(cityAqi);
  const ranked = [...reporting].sort((a, b) => b.latest!.aqi! - a.latest!.aqi!);

  const areaAvg = AREAS.map((a) => {
    const sub = all.filter((s) => s.area === a && s.live && s.latest);
    const aqi = sub.length ? Math.round(sub.reduce((x, s) => x + s.latest!.aqi!, 0) / sub.length) : null;
    return { area: a, aqi, count: sub.length, cat: categoryOf(aqi) };
  });

  const ticks = cityHourly(stations);
  // Where the network went quiet (> 3 h without enough stations), break the line and shade the window.
  const gaps: { from: number; to: number }[] = [];
  const gapped: { t: number; aqi: number | null; pm25: number | null; pm10: number | null; no2: number | null; o3: number | null }[] = [];
  ticks.forEach((t, i) => {
    const prev = ticks[i - 1];
    if (prev && t.t - prev.t > 3 * 3600000) {
      gaps.push({ from: prev.t, to: t.t });
      gapped.push({ t: prev.t + 3600000, aqi: null, pm25: null, pm10: null, no2: null, o3: null });
    }
    gapped.push(t);
  });
  const daily = cityDaily(ticks);
  const dProfile = diurnal(stations);
  const withVal = dProfile.filter((d) => d.pm25 !== null) as { hour: number; pm25: number }[];
  const peak = withVal.length ? withVal.reduce((m, d) => (d.pm25 > m.pm25 ? d : m)) : null;
  const clean = withVal.length ? withVal.reduce((m, d) => (d.pm25 < m.pm25 ? d : m)) : null;
  const pm25Mean = withVal.length ? withVal.reduce((a, d) => a + d.pm25, 0) / withVal.length : null;
  const share = categoryShare(stations);
  const pctPoor = share.total ? (share.counts.slice(3).reduce((a, b) => a + b, 0) / share.total) * 100 : 0;

  return {
    stations, reporting, ranked, cityAqi, cat, areaAvg, ticks, gaps, gapped, daily, dProfile, peak, clean, pm25Mean, share, pctPoor,
    worst: ranked[0] ?? null,
    cleanest: ranked[ranked.length - 1] ?? null,
  };
}
export type Model = ReturnType<typeof buildModel>;
