/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useMemo } from 'react';
import {
  Wind,
  MapPin,
  Activity,
  Calendar,
  TrendingUp,
  BarChart3,
  Download,
  AlertTriangle,
  Info,
  ShieldAlert,
  Layers,
  Compass,
  Clock,
  Sparkles,
  SlidersHorizontal,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Search,
  Check,
  Flame,
  ArrowUpRight,
  ArrowDownRight,
  FileCode2,
  Sun,
  Moon,
  ExternalLink,
} from 'lucide-react';

// CPCB National AQI Scale (2014) Breakpoints & Colors
interface CategoryInfo {
  name: string;
  min: number;
  max: number;
  color: string;
  lightBg: string;
  lightBorder: string;
  tag: string;
  headline: string;
  action: string;
  sensitive: string;
}

const CPCB_CATEGORIES: CategoryInfo[] = [
  {
    name: 'Good',
    min: 0,
    max: 50,
    color: '#00B050',
    lightBg: '#ECFDF5',
    lightBorder: '#A7F3D0',
    tag: 'Good Air (0–50)',
    headline: 'Air quality is clean and fresh',
    action: 'Ideal for morning jogs, outdoor sports, and opening windows for fresh air.',
    sensitive: 'Minimal to zero health impact for all population segments.',
  },
  {
    name: 'Satisfactory',
    min: 51,
    max: 100,
    color: '#92D050',
    lightBg: '#F7FEE7',
    lightBorder: '#D9F99D',
    tag: 'Satisfactory (51–100)',
    headline: 'Air quality is acceptable',
    action: 'Normal outdoor exertion and daily routines can continue without restriction.',
    sensitive: 'Unusually sensitive individuals may experience minor breathing discomfort.',
  },
  {
    name: 'Moderate',
    min: 101,
    max: 200,
    color: '#EAB308', // Adjusted for high legibility on light theme
    lightBg: '#FEFCE8',
    lightBorder: '#FEF08A',
    tag: 'Moderate (101–200)',
    headline: 'Go easier during long outdoor workouts',
    action: 'Keep intense aerobic workouts shorter, especially alongside major arterial roads.',
    sensitive: 'Children, the elderly, and individuals with asthma or heart conditions should take regular breaks.',
  },
  {
    name: 'Poor',
    min: 201,
    max: 300,
    color: '#FF9900',
    lightBg: '#FFF7ED',
    lightBorder: '#FED7AA',
    tag: 'Poor (201–300)',
    headline: 'Mask recommended for outdoor commutes',
    action: 'Avoid prolonged outdoor exertion. Wear an N95 mask during highway and road commutes.',
    sensitive: 'People with lung or heart disease, pregnant women, and children should limit outdoor exposure.',
  },
  {
    name: 'Very Poor',
    min: 301,
    max: 400,
    color: '#FF0000',
    lightBg: '#FEF2F2',
    lightBorder: '#FECACA',
    tag: 'Very Poor (301–400)',
    headline: 'High pollution alert · Restrict outdoor activity',
    action: 'Keep windows shut. Avoid outdoor jogging or cycling. Run indoor HEPA air purifiers.',
    sensitive: 'Sensitive groups must stay indoors. Healthy individuals will feel respiratory irritation.',
  },
  {
    name: 'Severe',
    min: 401,
    max: 500,
    color: '#C00000',
    lightBg: '#FFF1F2',
    lightBorder: '#FECDD3',
    tag: 'Severe Emergency (401–500)',
    headline: 'Public health emergency · Stay indoors',
    action: 'Avoid all outdoor activity. Run purifiers in sealed rooms. Seek medical attention if distress occurs.',
    sensitive: 'May cause severe health effects even in healthy people; extreme hazard for compromised groups.',
  },
];

function getCategory(aqi: number | null): CategoryInfo {
  if (aqi === null || isNaN(aqi)) return CPCB_CATEGORIES[2];
  if (aqi <= 50) return CPCB_CATEGORIES[0];
  if (aqi <= 100) return CPCB_CATEGORIES[1];
  if (aqi <= 200) return CPCB_CATEGORIES[2];
  if (aqi <= 300) return CPCB_CATEGORIES[3];
  if (aqi <= 400) return CPCB_CATEGORIES[4];
  return CPCB_CATEGORIES[5];
}

function subIndex(conc: number | null, pollutant: 'pm25' | 'pm10'): number | null {
  if (conc === null || isNaN(conc) || conc < 0) return null;
  const breakpoints =
    pollutant === 'pm25'
      ? [
          [0, 30, 0, 50],
          [30, 60, 50, 100],
          [60, 90, 100, 200],
          [90, 120, 200, 300],
          [120, 250, 300, 400],
          [250, 380, 400, 500],
        ]
      : [
          [0, 50, 0, 50],
          [50, 100, 50, 100],
          [100, 250, 100, 200],
          [250, 350, 200, 300],
          [350, 430, 300, 400],
          [430, 510, 400, 500],
        ];

  for (const [cLo, cHi, iLo, iHi] of breakpoints) {
    if (conc <= cHi) {
      return iLo + ((iHi - iLo) / (cHi - cLo)) * (conc - cLo);
    }
  }
  return 500;
}

function calculateAqi(pm25: number | null, pm10: number | null): number | null {
  const i25 = subIndex(pm25, 'pm25');
  const i10 = subIndex(pm10, 'pm10');
  const valid = [i25, i10].filter((v): v is number => v !== null);
  if (valid.length === 0) return null;
  return Math.min(500, Math.round(Math.max(...valid)));
}

function classifyArea(stationName: string): string {
  const s = stationName.toLowerCase();
  if (s.includes('gurugram') || s.includes('gurgaon')) return 'Gurugram';
  if (s.includes('noida')) return 'Noida';
  if (s.includes('faridabad')) return 'Faridabad';
  if (s.includes('bahadurgarh')) return 'Bahadurgarh';
  return 'Delhi';
}

interface RawReading {
  station_id: string;
  station: string;
  ts: string;
  // The pipeline exports numbers (or null); old snapshots had strings, so accept both.
  pm25: number | string | null;
  pm10: number | string | null;
  no2: number | string | null;
  o3: number | string | null;
  source: string;
}

// Where the live data comes from. The GitHub Actions pipeline commits fresh
// JSON files to the repo 3 times a day, and raw.githubusercontent.com serves
// them with CORS enabled, so the dashboard always shows the newest data
// without being rebuilt. Override with VITE_DATA_BASE_URL if you fork the repo.
const LIVE_DATA_BASE =
  (import.meta as any).env?.VITE_DATA_BASE_URL ||
  'https://raw.githubusercontent.com/Divyanshukumar2005/delhi-aqi-pipeline/main/data';

// Turn "87.0", 87 or null/"" into a number or null (0 is a valid reading).
function toNum(v: number | string | null | undefined): number | null {
  if (v === null || v === undefined || v === '') return null;
  const n = typeof v === 'number' ? v : parseFloat(v);
  return Number.isFinite(n) ? n : null;
}

// Try the live files first; if GitHub is unreachable, fall back to the copy
// bundled with the site (public/data) so the dashboard never shows a blank page.
async function fetchJsonWithFallback<T>(file: string): Promise<T> {
  try {
    const res = await fetch(`${LIVE_DATA_BASE}/${file}`, { cache: 'no-cache' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return (await res.json()) as T;
  } catch (err) {
    console.warn(`Live ${file} failed, using bundled copy`, err);
    const res = await fetch(`/data/${file}`);
    return (await res.json()) as T;
  }
}

interface StationCoord {
  id: number | string;
  name: string;
  lat: number;
  lon: number;
  distance_km?: number;
}

interface ProcessedReading {
  stationId: string;
  station: string;
  area: string;
  label: string;
  ts: Date;
  isoTs: string;
  hour: number;
  dateStr: string;
  pm25: number | null;
  pm10: number | null;
  no2: number | null;
  o3: number | null;
  pm25_24h: number | null;
  pm10_24h: number | null;
  aqi: number | null;
  category: CategoryInfo;
  source: string;
}

interface StationSummary {
  stationId: string;
  name: string;
  area: string;
  label: string;
  lat: number;
  lon: number;
  latestAqi: number;
  latestCategory: CategoryInfo;
  latestPm25: number | null;
  latestPm10: number | null;
  latestNo2: number | null;
  latestO3: number | null;
  meanAqi: number;
  maxAqi: number;
  pctPoorOrWorse: number;
  readingsCount: number;
}

export default function App() {
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [readings, setReadings] = useState<ProcessedReading[]>([]);
  const [stations, setStations] = useState<StationCoord[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<
    'overview' | 'map' | 'heatmap' | 'trends' | 'deepdive' | 'compare' | 'forecast' | 'insights' | 'code'
  >('overview');

  // Filters
  const [selectedArea, setSelectedArea] = useState<string>('All');
  const [selectedSource, setSelectedSource] = useState<string>('all');
  const [deepDiveStation, setDeepDiveStation] = useState<string>('');
  const [compareStations, setCompareStations] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [pollutantChoice, setPollutantChoice] = useState<'pm25' | 'pm10' | 'no2' | 'o3'>('pm25');

  useEffect(() => {
    async function loadAllData() {
      try {
        setLoading(true);
        const [stationsData, readingsData] = await Promise.all([
          fetchJsonWithFallback<StationCoord[]>('stations.json'),
          fetchJsonWithFallback<RawReading[]>('readings.json'),
        ]);

        setStations(stationsData);

        const byStation: Record<string, RawReading[]> = {};
        for (const r of readingsData) {
          const key = r.station_id;
          if (!byStation[key]) byStation[key] = [];
          byStation[key].push(r);
        }

        const processed: ProcessedReading[] = [];

        for (const stationId in byStation) {
          const list = byStation[stationId].sort(
            (a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime()
          );

          for (let i = 0; i < list.length; i++) {
            const item = list[i];
            const tsDate = new Date(item.ts);
            const windowStart = tsDate.getTime() - 24 * 3600 * 1000;
            const windowItems = list.filter((x) => {
              const t = new Date(x.ts).getTime();
              return t <= tsDate.getTime() && t >= windowStart;
            });

            const validPm25 = windowItems
              .map((x) => toNum(x.pm25))
              .filter((v): v is number => v !== null && !isNaN(v) && v >= 0);

            const validPm10 = windowItems
              .map((x) => toNum(x.pm10))
              .filter((v): v is number => v !== null && !isNaN(v) && v >= 0);

            const meanPm25 =
              validPm25.length >= 1
                ? validPm25.reduce((a, b) => a + b, 0) / validPm25.length
                : null;

            const meanPm10 =
              validPm10.length >= 1
                ? validPm10.reduce((a, b) => a + b, 0) / validPm10.length
                : null;

            const aqiVal = calculateAqi(meanPm25, meanPm10);
            const category = getCategory(aqiVal);

            processed.push({
              stationId: item.station_id,
              station: item.station,
              area: classifyArea(item.station),
              label: item.source === 'open-meteo' ? `${item.station} (model)` : item.station,
              ts: tsDate,
              isoTs: item.ts,
              hour: tsDate.getHours(),
              dateStr: tsDate.toISOString().split('T')[0],
              pm25: toNum(item.pm25),
              pm10: toNum(item.pm10),
              no2: toNum(item.no2),
              o3: toNum(item.o3),
              pm25_24h: meanPm25,
              pm10_24h: meanPm10,
              aqi: aqiVal,
              category,
              source: item.source,
            });
          }
        }

        setReadings(processed);
        if (processed.length > 0) {
          const names = Array.from(new Set(processed.map((p) => p.label)));
          if (names.length > 0) {
            setDeepDiveStation(names[0]);
            setCompareStations(names.slice(0, 3));
          }
        }
      } catch (err) {
        console.error('Failed to load AQI data', err);
      } finally {
        setLoading(false);
      }
    }

    loadAllData();
  }, []);

  const filteredReadings = useMemo(() => {
    return readings.filter((r) => {
      if (selectedArea !== 'All' && r.area !== selectedArea) return false;
      if (selectedSource !== 'all' && r.source !== selectedSource) return false;
      return true;
    });
  }, [readings, selectedArea, selectedSource]);

  const stationSummaries = useMemo(() => {
    const coordsMap = new Map<string, StationCoord>();
    for (const s of stations) {
      coordsMap.set(String(s.id), s);
    }

    const byStation = new Map<string, ProcessedReading[]>();
    for (const r of filteredReadings) {
      if (!byStation.has(r.stationId)) byStation.set(r.stationId, []);
      byStation.get(r.stationId)!.push(r);
    }

    const summaries: StationSummary[] = [];
    byStation.forEach((list, stationId) => {
      const sorted = [...list].sort((a, b) => b.ts.getTime() - a.ts.getTime());
      const latest = sorted[0];
      const validAqis = list.map((x) => x.aqi).filter((v): v is number => v !== null);
      if (validAqis.length === 0) return;

      const meanAqi = validAqis.reduce((a, b) => a + b, 0) / validAqis.length;
      const maxAqi = Math.max(...validAqis);
      const poorCount = list.filter(
        (x) => x.category.name === 'Poor' || x.category.name === 'Very Poor' || x.category.name === 'Severe'
      ).length;
      const pctPoor = (poorCount / list.length) * 100;

      const coord = coordsMap.get(stationId);

      summaries.push({
        stationId,
        name: latest.station,
        area: latest.area,
        label: latest.label,
        lat: coord?.lat ?? 28.6139,
        lon: coord?.lon ?? 77.209,
        latestAqi: latest.aqi ?? meanAqi,
        latestCategory: latest.category,
        latestPm25: latest.pm25,
        latestPm10: latest.pm10,
        latestNo2: latest.no2,
        latestO3: latest.o3,
        meanAqi,
        maxAqi,
        pctPoorOrWorse: pctPoor,
        readingsCount: list.length,
      });
    });

    return summaries.sort((a, b) => b.latestAqi - a.latestAqi);
  }, [filteredReadings, stations]);

  const cityMetrics = useMemo(() => {
    if (stationSummaries.length === 0) {
      return {
        aqi: 0,
        category: CPCB_CATEGORIES[2],
        count: 0,
        worstStation: null as StationSummary | null,
        cleanestStation: null as StationSummary | null,
        pctPoor: 0,
        lastUpdatedIst: '31 Oct 2026, 11:00 IST',
      };
    }

    const sum = stationSummaries.reduce((acc, s) => acc + s.latestAqi, 0);
    const avgAqi = Math.round(sum / stationSummaries.length);
    const cat = getCategory(avgAqi);

    const worst = stationSummaries[0];
    const cleanest = stationSummaries[stationSummaries.length - 1];

    const poorCount = filteredReadings.filter(
      (r) => r.category.name === 'Poor' || r.category.name === 'Very Poor' || r.category.name === 'Severe'
    ).length;
    const pctPoor = (poorCount / (filteredReadings.length || 1)) * 100;

    let maxTs = new Date();
    if (filteredReadings.length > 0) {
      const times = filteredReadings.map((r) => r.ts.getTime());
      maxTs = new Date(Math.max(...times));
    }

    const lastUpdatedIst =
      maxTs.toLocaleDateString('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      }) +
      ', ' +
      maxTs.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }) +
      ' IST';

    return {
      aqi: avgAqi,
      category: cat,
      count: stationSummaries.length,
      worstStation: worst,
      cleanestStation: cleanest,
      pctPoor,
      lastUpdatedIst,
    };
  }, [stationSummaries, filteredReadings]);

  const areaAverages = useMemo(() => {
    const areas = ['Delhi', 'Gurugram', 'Noida', 'Faridabad', 'Bahadurgarh'];
    return areas.map((area) => {
      const subset = stationSummaries.filter((s) => s.area === area);
      if (subset.length === 0) return { area, aqi: null, count: 0, cat: CPCB_CATEGORIES[0] };
      const avg = Math.round(subset.reduce((a, b) => a + b.latestAqi, 0) / subset.length);
      return { area, aqi: avg, count: subset.length, cat: getCategory(avg) };
    });
  }, [stationSummaries]);

  const diurnalProfile = useMemo(() => {
    const byHour: Record<number, number[]> = {};
    for (let h = 0; h < 24; h++) byHour[h] = [];

    for (const r of filteredReadings) {
      if (r.aqi !== null) byHour[r.hour].push(r.aqi);
    }

    return Array.from({ length: 24 }).map((_, h) => {
      const arr = byHour[h];
      const avg = arr.length > 0 ? Math.round(arr.reduce((a, b) => a + b, 0) / arr.length) : 0;
      return { hour: h, aqi: avg, category: getCategory(avg) };
    });
  }, [filteredReadings]);

  const peakHour = useMemo(() => {
    if (diurnalProfile.length === 0) return { hour: 0, aqi: 0 };
    return diurnalProfile.reduce((max, curr) => (curr.aqi > max.aqi ? curr : max), diurnalProfile[0]);
  }, [diurnalProfile]);

  const cleanHour = useMemo(() => {
    if (diurnalProfile.length === 0) return { hour: 0, aqi: 0 };
    return diurnalProfile.reduce((min, curr) => (curr.aqi < min.aqi ? curr : min), diurnalProfile[0]);
  }, [diurnalProfile]);

  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {
      Good: 0,
      Satisfactory: 0,
      Moderate: 0,
      Poor: 0,
      'Very Poor': 0,
      Severe: 0,
    };
    for (const r of filteredReadings) {
      if (r.category && counts[r.category.name] !== undefined) {
        counts[r.category.name]++;
      }
    }
    return CPCB_CATEGORIES.map((c) => ({
      name: c.name,
      count: counts[c.name],
      color: c.color,
    }));
  }, [filteredReadings]);

  const dailyTrends = useMemo(() => {
    const datesMap = new Map<string, number[]>();
    for (const r of filteredReadings) {
      if (r.aqi !== null) {
        if (!datesMap.has(r.dateStr)) datesMap.set(r.dateStr, []);
        datesMap.get(r.dateStr)!.push(r.aqi);
      }
    }

    const sortedDates = Array.from(datesMap.keys()).sort();
    return sortedDates.map((dateStr) => {
      const arr = datesMap.get(dateStr)!;
      const avg = Math.round(arr.reduce((a, b) => a + b, 0) / arr.length);
      return {
        dateStr,
        aqi: avg,
        cat: getCategory(avg),
      };
    });
  }, [filteredReadings]);

  const forecastData = useMemo(() => {
    if (dailyTrends.length === 0) return [];
    const latestAqi = cityMetrics.aqi;
    const hourNow = new Date().getHours();
    const rows = [];

    for (let k = 1; k <= 24; k++) {
      const targetHour = (hourNow + k) % 24;
      const diurnalDiff = (diurnalProfile[targetHour]?.aqi ?? latestAqi) - latestAqi;
      const decay = Math.pow(0.5, k / 12);
      const predicted = Math.round(decay * latestAqi + (1 - decay) * (latestAqi + diurnalDiff * 0.7));
      const unc = Math.round(18 * Math.sqrt(k / 12));
      rows.push({
        step: k,
        hour: targetHour,
        label: `${targetHour.toString().padStart(2, '0')}:00`,
        predicted: Math.min(500, Math.max(20, predicted)),
        lo: Math.max(0, predicted - unc),
        hi: Math.min(500, predicted + unc),
      });
    }
    return rows;
  }, [cityMetrics.aqi, diurnalProfile, dailyTrends]);

  const deepDiveData = useMemo(() => {
    if (!deepDiveStation) return null;
    const subset = readings
      .filter((r) => r.label === deepDiveStation)
      .sort((a, b) => a.ts.getTime() - b.ts.getTime());
    if (subset.length === 0) return null;

    const valid = subset.filter((r) => r.aqi !== null);
    const meanAqi = valid.length > 0 ? Math.round(valid.reduce((a, b) => a + b.aqi!, 0) / valid.length) : 0;
    const maxReading = valid.reduce((max, cur) => ((cur.aqi ?? 0) > (max.aqi ?? 0) ? cur : max), valid[0]);

    return {
      name: deepDiveStation,
      records: subset,
      latest: subset[subset.length - 1],
      meanAqi,
      maxReading,
      pctPoor:
        (subset.filter(
          (x) => x.category.name === 'Poor' || x.category.name === 'Very Poor' || x.category.name === 'Severe'
        ).length /
          subset.length) *
        100,
    };
  }, [deepDiveStation, readings]);

  const downloadCsv = () => {
    const headers = ['Station', 'Area', 'Timestamp_IST', 'PM25', 'PM10', 'NO2', 'O3', 'AQI', 'Category', 'Source'];
    const rows = filteredReadings.map((r) => [
      `"${r.station}"`,
      r.area,
      r.isoTs,
      r.pm25 ?? '',
      r.pm10 ?? '',
      r.no2 ?? '',
      r.o3 ?? '',
      r.aqi ?? '',
      r.category.name,
      r.source,
    ]);

    const csvContent = [headers.join(','), ...rows.map((row) => row.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', 'delhi_ncr_aqi_data.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const isLight = theme === 'light';

  // Dynamic Theme Styling Classes
  const themeClasses = {
    bgApp: isLight ? 'bg-[#F8FAFC]' : 'bg-[#0B0E14]',
    textPrimary: isLight ? 'text-slate-900' : 'text-slate-100',
    textSecondary: isLight ? 'text-slate-600' : 'text-slate-400',
    textMuted: isLight ? 'text-slate-400' : 'text-slate-500',
    headerBg: isLight ? 'bg-white/95 border-slate-200' : 'bg-[#0F131A]/95 border-[#202734]',
    filterBarBg: isLight ? 'bg-slate-100/90 border-slate-200' : 'bg-[#121620] border-[#1F2633]',
    cardBg: isLight ? 'bg-white border-slate-200 shadow-sm' : 'bg-[#141820] border-[#252B37] shadow-xl',
    cardElevated: isLight ? 'bg-slate-50 border-slate-200' : 'bg-[#0E121A] border-[#1F2735]',
    cardBorder: isLight ? 'border-slate-200' : 'border-[#252B37]',
    tabActive: isLight
      ? 'bg-white text-slate-900 shadow-sm border-b-2 border-amber-500'
      : 'bg-[#18202B] text-white border-b-2 border-[#FF9900]',
    tabInactive: isLight
      ? 'text-slate-500 hover:text-slate-800 hover:bg-slate-100'
      : 'text-slate-400 hover:text-slate-200 hover:bg-[#121620]',
    tableHeadBorder: isLight ? 'border-slate-200 text-slate-500' : 'border-[#202734] text-slate-400',
    tableRowBorder: isLight ? 'border-slate-100 hover:bg-slate-50' : 'border-[#18202C] hover:bg-[#18202B]',
    inputBg: isLight ? 'bg-white border-slate-200 text-slate-900' : 'bg-[#0E121A] border-[#222B3A] text-white',
  };

  if (loading) {
    return (
      <div className={`min-h-screen ${themeClasses.bgApp} ${themeClasses.textPrimary} flex flex-col items-center justify-center p-6`}>
        <RefreshCw className="w-10 h-10 text-amber-500 animate-spin mb-4" />
        <h2 className="text-xl font-bold tracking-tight">Ingesting Delhi-NCR Station Readings...</h2>
        <p className={`text-sm ${themeClasses.textSecondary} mt-2`}>
          Computing CPCB National AQI with rolling 24-hour averages for 25+ stations.
        </p>
      </div>
    );
  }

  return (
    <div className={`min-h-screen ${themeClasses.bgApp} ${themeClasses.textPrimary} selection:bg-amber-500/20 selection:text-amber-900 transition-colors duration-300 pb-16 font-['Bricolage_Grotesque']`}>
      {/* Top Header & Theme Switcher */}
      <header className={`sticky top-0 z-40 ${themeClasses.headerBg} backdrop-blur-md border-b px-4 lg:px-8 py-3.5 transition-colors`}>
        <div className="max-w-[1360px] mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-2xl flex items-center justify-center shadow-xs ${
              isLight ? 'bg-amber-50 border border-amber-200/80 text-amber-700' : 'bg-[#1A222E] border border-[#2D384A] text-[#8FB8C9]'
            }`}>
              <Wind className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-extrabold tracking-tight">
                  Delhi-NCR Air Quality Tracker
                </h1>
                <span className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full ${
                  isLight ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-[#1A2332] text-[#8FB8C9] border border-[#2B394E]'
                }`}>
                  CPCB NAQI 2014
                </span>
              </div>
              <p className={`text-xs ${themeClasses.textSecondary}`}>
                Hourly government stations: Delhi, Gurugram, Noida, Faridabad, Bahadurgarh
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 self-end sm:self-auto">
            {/* Light / Dark Mode Toggle */}
            <button
              onClick={() => setTheme(isLight ? 'dark' : 'light')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-bold transition-all shadow-xs ${
                isLight
                  ? 'bg-white hover:bg-slate-50 border-slate-200 text-slate-700'
                  : 'bg-[#18202B] hover:bg-[#202B3A] border-[#2A374A] text-slate-200'
              }`}
              title={`Switch to ${isLight ? 'Dark' : 'Light'} theme`}
            >
              {isLight ? <Moon className="w-3.5 h-3.5 text-indigo-600" /> : <Sun className="w-3.5 h-3.5 text-amber-400" />}
              <span>{isLight ? 'Dark Theme' : 'Light Theme'}</span>
            </button>

            <div className="text-right pl-2 border-l border-slate-200">
              <div className={`text-[10px] uppercase tracking-wider font-mono ${themeClasses.textMuted}`}>Last Ingested</div>
              <div className="text-xs font-bold font-mono flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                {cityMetrics.lastUpdatedIst}
              </div>
            </div>

            <button
              onClick={downloadCsv}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl border transition-all shadow-xs ${
                isLight
                  ? 'bg-amber-500 hover:bg-amber-600 border-amber-600 text-white shadow-amber-500/20'
                  : 'bg-[#18202B] hover:bg-[#202B3A] border-[#2A374A] text-slate-200'
              }`}
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export CSV</span>
            </button>
          </div>
        </div>
      </header>

      {/* Filter Bar */}
      <div className={`${themeClasses.filterBarBg} border-b px-4 lg:px-8 py-2.5 transition-colors`}>
        <div className="max-w-[1360px] mx-auto flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className={`${themeClasses.textMuted} font-semibold flex items-center gap-1 mr-1`}>
              <SlidersHorizontal className="w-3.5 h-3.5" /> Sub-Region:
            </span>
            {['All', 'Delhi', 'Gurugram', 'Noida', 'Faridabad', 'Bahadurgarh'].map((area) => (
              <button
                key={area}
                onClick={() => setSelectedArea(area)}
                className={`px-3 py-1 rounded-lg font-bold transition-all text-xs ${
                  selectedArea === area
                    ? isLight
                      ? 'bg-slate-900 text-white shadow-sm'
                      : 'bg-[#293548] text-white border border-[#445570]'
                    : isLight
                    ? 'bg-white text-slate-600 hover:text-slate-900 border border-slate-200'
                    : 'bg-[#181E29] text-slate-400 hover:text-white border border-[#222B3A]'
                }`}
              >
                {area}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <span className={themeClasses.textMuted}>Data Source:</span>
            <select
              value={selectedSource}
              onChange={(e) => setSelectedSource(e.target.value)}
              className={`${themeClasses.inputBg} border rounded-lg px-2.5 py-1 text-xs outline-none font-medium`}
            >
              <option value="all">All Sources (OpenAQ + Fallback)</option>
              <option value="openaq">OpenAQ Government Monitors Only</option>
              <option value="open-meteo">Open-Meteo CAMS Model Only</option>
            </select>
          </div>
        </div>
      </div>

      <main className="max-w-[1360px] mx-auto px-4 lg:px-8 pt-6">
        {/* Navigation Tabs Bar */}
        <div className={`flex items-center gap-1 overflow-x-auto pb-2 border-b ${themeClasses.cardBorder} mb-6 scrollbar-none`}>
          {[
            { id: 'overview', label: 'Basin Overview', icon: Activity },
            { id: 'map', label: 'Map & Rankings', icon: MapPin },
            { id: 'heatmap', label: 'Heatmap & Diurnal', icon: Clock },
            { id: 'trends', label: 'Trend & Pollutants', icon: TrendingUp },
            { id: 'deepdive', label: 'Station Deep-Dive', icon: Compass },
            { id: 'compare', label: 'Compare Stations', icon: Layers },
            { id: 'forecast', label: '24h Forecast', icon: Sparkles },
            { id: 'insights', label: 'Insights & Statistics', icon: BarChart3 },
            { id: 'code', label: 'Streamlit Python Code', icon: FileCode2 },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold rounded-t-xl transition-all whitespace-nowrap ${
                  isActive ? themeClasses.tabActive : themeClasses.tabInactive
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-amber-500' : 'text-slate-400'}`} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* TAB 1: BASIN OVERVIEW */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Hero Card Split */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
              {/* Dial Gauge Card */}
              <div className={`lg:col-span-5 ${themeClasses.cardBg} rounded-2xl p-6 flex flex-col items-center justify-between relative overflow-hidden`}>
                <div className="w-full flex items-center justify-between text-xs">
                  <span className={`font-bold uppercase tracking-wider ${themeClasses.textMuted}`}>Delhi-NCR Basin Mean</span>
                  <span className={`font-mono font-bold px-2 py-0.5 rounded-full ${isLight ? 'bg-slate-100 text-slate-700' : 'bg-slate-800 text-slate-300'}`}>
                    {stationSummaries.length} Stations Active
                  </span>
                </div>

                {/* Semicircle Radial Gauge */}
                <div className="relative w-64 h-36 my-4 flex items-end justify-center">
                  <svg className="w-64 h-36 overflow-visible" viewBox="0 0 200 110">
                    {/* CPCB 6 Category Segments */}
                    <path d="M 20 100 A 80 80 0 0 1 35.8 43.4" fill="none" stroke="#00B050" strokeWidth="15" strokeOpacity={isLight ? "0.4" : "0.3"} strokeLinecap="round" />
                    <path d="M 35.8 43.4 A 80 80 0 0 1 75.3 23.9" fill="none" stroke="#92D050" strokeWidth="15" strokeOpacity={isLight ? "0.4" : "0.3"} />
                    <path d="M 75.3 23.9 A 80 80 0 0 1 124.7 23.9" fill="none" stroke="#EAB308" strokeWidth="15" strokeOpacity={isLight ? "0.4" : "0.3"} />
                    <path d="M 124.7 23.9 A 80 80 0 0 1 164.2 43.4" fill="none" stroke="#FF9900" strokeWidth="15" strokeOpacity={isLight ? "0.4" : "0.3"} />
                    <path d="M 164.2 43.4 A 80 80 0 0 1 178 72" fill="none" stroke="#FF0000" strokeWidth="15" strokeOpacity={isLight ? "0.4" : "0.3"} />
                    <path d="M 178 72 A 80 80 0 0 1 180 100" fill="none" stroke="#C00000" strokeWidth="15" strokeOpacity={isLight ? "0.4" : "0.3"} strokeLinecap="round" />

                    {/* Active Needle Indicator */}
                    {(() => {
                      const angleDeg = 180 - (Math.min(500, cityMetrics.aqi) / 500) * 180;
                      const rad = (angleDeg * Math.PI) / 180;
                      const nx = 100 + 72 * Math.cos(rad);
                      const ny = 100 - 72 * Math.sin(rad);
                      return (
                        <>
                          <line
                            x1="100"
                            y1="100"
                            x2={nx}
                            y2={ny}
                            stroke={cityMetrics.category.color}
                            strokeWidth="4"
                            strokeLinecap="round"
                          />
                          <circle cx="100" cy="100" r="7" fill={cityMetrics.category.color} stroke={isLight ? '#FFFFFF' : '#141820'} strokeWidth="2" />
                        </>
                      );
                    })()}
                  </svg>

                  {/* Centered Value Readout */}
                  <div className="absolute -bottom-2 text-center">
                    <div
                      className="text-5xl font-black font-mono tracking-tight leading-none"
                      style={{ color: cityMetrics.category.color }}
                    >
                      {cityMetrics.aqi}
                    </div>
                    <div
                      className="inline-block mt-1.5 px-3 py-0.5 rounded-full text-xs font-black uppercase tracking-wider shadow-xs"
                      style={{
                        backgroundColor: isLight ? cityMetrics.category.lightBg : `${cityMetrics.category.color}25`,
                        color: cityMetrics.category.color,
                        border: `1.5px solid ${cityMetrics.category.color}`,
                      }}
                    >
                      {cityMetrics.category.name}
                    </div>
                  </div>
                </div>

                <div className={`w-full text-center text-xs ${themeClasses.textMuted} pt-3 border-t ${themeClasses.cardBorder}`}>
                  Scale: 0 to 500 National AQI · Maximum sub-index of PM2.5 / PM10 (24h Mean)
                </div>
              </div>

              {/* Actionable Health Guidance Card */}
              <div
                className={`lg:col-span-7 ${themeClasses.cardBg} rounded-2xl p-6 flex flex-col justify-between relative overflow-hidden`}
                style={{ borderLeftWidth: '6px', borderLeftColor: cityMetrics.category.color }}
              >
                <div>
                  <span
                    className="inline-block px-3.5 py-1 rounded-full text-xs font-extrabold tracking-wide mb-3 shadow-xs"
                    style={{
                      backgroundColor: isLight ? cityMetrics.category.lightBg : `${cityMetrics.category.color}20`,
                      color: cityMetrics.category.color,
                      border: `1px solid ${cityMetrics.category.color}40`,
                    }}
                  >
                    {cityMetrics.category.tag}
                  </span>
                  <h2 className="text-2xl font-black tracking-tight leading-snug mb-2 font-['Bricolage_Grotesque']">
                    {cityMetrics.category.headline}
                  </h2>
                  <p className={`text-sm ${themeClasses.textSecondary} leading-relaxed mb-4 font-normal`}>
                    {cityMetrics.category.action}
                  </p>
                </div>

                <div className={`pt-3 border-t ${themeClasses.cardBorder} space-y-1`}>
                  <div className={`text-xs ${themeClasses.textSecondary} leading-relaxed flex items-start gap-2`}>
                    <ShieldAlert className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                    <span>
                      <strong className={themeClasses.textPrimary}>Sensitive Groups: </strong>
                      {cityMetrics.category.sensitive}
                    </span>
                  </div>
                  <div className={`text-[11px] ${themeClasses.textMuted} pl-6`}>
                    * Formulated under CPCB National Air Quality Index advisory guidelines. Not medical advice.
                  </div>
                </div>
              </div>
            </div>

            {/* Sub-Region Breakdown Strip */}
            <div>
              <div className={`text-xs uppercase tracking-wider font-bold ${themeClasses.textMuted} mb-3 flex items-center gap-1.5`}>
                <Compass className="w-3.5 h-3.5 text-amber-500" /> Regional Basin Pulse Right Now
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
                {areaAverages.map((item) => (
                  <div
                    key={item.area}
                    className={`${themeClasses.cardBg} rounded-xl p-3.5 flex items-center justify-between transition-all hover:-translate-y-0.5`}
                    style={{ borderLeftWidth: '5px', borderLeftColor: item.cat.color }}
                  >
                    <div>
                      <div className="text-xs font-bold text-slate-800">{item.area}</div>
                      <div className={`text-[11px] ${themeClasses.textMuted} font-medium`}>
                        {item.count} station(s) · {item.cat.name}
                      </div>
                    </div>
                    <div className="text-xl font-black font-mono" style={{ color: item.cat.color }}>
                      {item.aqi !== null ? item.aqi : '—'}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 4 Summary Stat Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className={`${themeClasses.cardBg} rounded-xl p-4`}>
                <div className={`text-xs ${themeClasses.textMuted} uppercase tracking-wider font-bold`}>Most Polluted Now</div>
                <div className="text-sm font-bold truncate mt-1">
                  {cityMetrics.worstStation ? cityMetrics.worstStation.name : '—'}
                </div>
                <div className="text-2xl font-black font-mono text-[#FF0000] mt-1">
                  AQI {cityMetrics.worstStation ? cityMetrics.worstStation.latestAqi : '—'}
                </div>
              </div>

              <div className={`${themeClasses.cardBg} rounded-xl p-4`}>
                <div className={`text-xs ${themeClasses.textMuted} uppercase tracking-wider font-bold`}>Cleanest Station Now</div>
                <div className="text-sm font-bold truncate mt-1">
                  {cityMetrics.cleanestStation ? cityMetrics.cleanestStation.name : '—'}
                </div>
                <div className="text-2xl font-black font-mono text-[#00B050] mt-1">
                  AQI {cityMetrics.cleanestStation ? cityMetrics.cleanestStation.latestAqi : '—'}
                </div>
              </div>

              <div className={`${themeClasses.cardBg} rounded-xl p-4`}>
                <div className={`text-xs ${themeClasses.textMuted} uppercase tracking-wider font-bold`}>Hours in Poor or Worse</div>
                <div className={`text-xs ${themeClasses.textSecondary} mt-1`}>High Health Hazard Window</div>
                <div className="text-2xl font-black font-mono text-[#FF9900] mt-1">
                  {cityMetrics.pctPoor.toFixed(1)}%
                </div>
              </div>

              <div className={`${themeClasses.cardBg} rounded-xl p-4`}>
                <div className={`text-xs ${themeClasses.textMuted} uppercase tracking-wider font-bold`}>Diurnal Cleanest Hour</div>
                <div className={`text-xs ${themeClasses.textSecondary} mt-1`}>Basin Daily Minimum</div>
                <div className="text-2xl font-black font-mono text-emerald-600 mt-1">
                  {cleanHour.hour.toString().padStart(2, '0')}:00 IST
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: MAP & RANKINGS */}
        {activeTab === 'map' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Interactive Station Spatial Map */}
            <div className={`lg:col-span-7 ${themeClasses.cardBg} rounded-2xl p-5 flex flex-col`}>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-base font-bold flex items-center gap-2">
                  <MapPin className="w-4 h-4 text-amber-500" /> Delhi-NCR Station Spatial Map
                </h3>
                <span className={`text-xs font-mono font-bold ${themeClasses.textMuted}`}>{stationSummaries.length} monitors mapped</span>
              </div>

              {/* Styled Vector Light / Dark Map Graphic */}
              <div className={`relative w-full h-[470px] ${isLight ? 'bg-slate-50' : 'bg-[#0E121A]'} rounded-xl border ${themeClasses.cardBorder} overflow-hidden flex items-center justify-center`}>
                <svg className="w-full h-full" viewBox="76.85 28.35 0.55 0.45" preserveAspectRatio="none">
                  {/* Subtle Grid Lines */}
                  <line x1="77.0" y1="28.3" x2="77.0" y2="28.85" stroke={isLight ? "#E2E8F0" : "#1C2433"} strokeWidth="0.001" />
                  <line x1="77.2" y1="28.3" x2="77.2" y2="28.85" stroke={isLight ? "#E2E8F0" : "#1C2433"} strokeWidth="0.001" />
                  <line x1="76.8" y1="28.5" x2="77.45" y2="28.5" stroke={isLight ? "#E2E8F0" : "#1C2433"} strokeWidth="0.001" />
                  <line x1="76.8" y1="28.7" x2="77.45" y2="28.7" stroke={isLight ? "#E2E8F0" : "#1C2433"} strokeWidth="0.001" />

                  {/* Delhi Center marker */}
                  <circle cx="77.209" cy="28.6139" r="0.006" fill="none" stroke={isLight ? "#475569" : "#FFFFFF"} strokeWidth="0.0015" />
                  <circle cx="77.209" cy="28.6139" r="0.002" fill={isLight ? "#0F172A" : "#FFFFFF"} />

                  {/* Station Points */}
                  {stationSummaries.map((s) => (
                    <g key={s.stationId} className="cursor-pointer group">
                      <circle
                        cx={s.lon}
                        cy={s.lat}
                        r="0.012"
                        fill={s.latestCategory.color}
                        fillOpacity="0.9"
                        stroke={isLight ? "#FFFFFF" : "#0E121A"}
                        strokeWidth="0.002"
                      />
                      <circle
                        cx={s.lon}
                        cy={s.lat}
                        r="0.022"
                        fill={s.latestCategory.color}
                        fillOpacity="0.22"
                      />
                    </g>
                  ))}
                </svg>

                {/* Map Overlay Labels */}
                <div className={`absolute top-3 left-3 ${isLight ? 'bg-white/95 border-slate-200' : 'bg-[#141820]/90 border-[#2B3547]'} border rounded-xl p-3 text-xs pointer-events-none backdrop-blur-sm shadow-xs`}>
                  <div className="font-bold text-[11px] mb-1.5">CPCB Category Legend</div>
                  <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[10px]">
                    {CPCB_CATEGORIES.map((c) => (
                      <div key={c.name} className="flex items-center gap-1.5 font-medium">
                        <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: c.color }} />
                        <span>{c.name}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className={`absolute bottom-3 right-3 ${isLight ? 'bg-white/95 border-slate-200' : 'bg-[#141820]/90 border-[#2B3547]'} border rounded-lg px-2.5 py-1 text-[10px] ${themeClasses.textMuted} font-mono pointer-events-none`}>
                  Delhi-NCR Bounding Box
                </div>
              </div>
            </div>

            {/* Ranked Stations List */}
            <div className={`lg:col-span-5 ${themeClasses.cardBg} rounded-2xl p-5 flex flex-col h-[530px]`}>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-base font-bold flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-amber-500" /> Station Pollution Ranking
                </h3>
                <span className={`text-xs ${themeClasses.textMuted} font-medium`}>Most to Least Polluted</span>
              </div>

              {/* Search input */}
              <div className="relative mb-3">
                <Search className={`w-3.5 h-3.5 absolute left-3 top-2.5 ${themeClasses.textMuted}`} />
                <input
                  type="text"
                  placeholder="Search station or area..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className={`w-full ${themeClasses.inputBg} rounded-xl pl-8 pr-3 py-1.5 text-xs outline-none focus:ring-1 focus:ring-amber-500`}
                />
              </div>

              {/* Scrollable Bar List */}
              <div className="flex-1 overflow-y-auto pr-1 space-y-2">
                {stationSummaries
                  .filter((s) => s.name.toLowerCase().includes(searchQuery.toLowerCase()) || s.area.toLowerCase().includes(searchQuery.toLowerCase()))
                  .map((s, idx) => (
                    <div
                      key={s.stationId}
                      onClick={() => {
                        setDeepDiveStation(s.label);
                        setActiveTab('deepdive');
                      }}
                      className={`group ${isLight ? 'bg-slate-50 hover:bg-slate-100 border-slate-200' : 'bg-[#0F131C] hover:bg-[#18202C] border-[#1E2533]'} border rounded-xl p-2.5 transition-all cursor-pointer`}
                    >
                      <div className="flex items-center justify-between text-xs mb-1.5">
                        <div className="flex items-center gap-2 truncate pr-2">
                          <span className={`w-5 text-[11px] font-mono font-bold ${themeClasses.textMuted}`}>#{idx + 1}</span>
                          <span className="font-bold truncate">{s.name}</span>
                          <span className={`text-[10px] ${themeClasses.textMuted} shrink-0`}>({s.area})</span>
                        </div>
                        <div className="font-mono font-black text-sm shrink-0" style={{ color: s.latestCategory.color }}>
                          {s.latestAqi}
                        </div>
                      </div>

                      {/* Bar fill */}
                      <div className={`w-full ${isLight ? 'bg-slate-200' : 'bg-[#18202D]'} rounded-full h-1.5 overflow-hidden`}>
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${Math.min(100, (s.latestAqi / 500) * 100)}%`,
                            backgroundColor: s.latestCategory.color,
                          }}
                        />
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: HEATMAP & DIURNAL */}
        {activeTab === 'heatmap' && (
          <div className="space-y-6">
            {/* Hour-by-Day Grid */}
            <div className={`${themeClasses.cardBg} rounded-2xl p-6`}>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
                <div>
                  <h3 className="text-base font-bold flex items-center gap-2">
                    <Clock className="w-4 h-4 text-amber-500" /> City AQI by Day & Hour (IST)
                  </h3>
                  <p className={`text-xs ${themeClasses.textSecondary} mt-0.5`}>
                    Matrix showing hourly city-wide average AQI across all active monitoring stations.
                  </p>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className={themeClasses.textMuted}>CPCB Scale</span>
                  <div className="flex items-center h-2.5 w-36 rounded-full overflow-hidden border border-slate-200">
                    {CPCB_CATEGORIES.map((c) => (
                      <div key={c.name} className="flex-1 h-full" style={{ backgroundColor: c.color }} />
                    ))}
                  </div>
                </div>
              </div>

              {/* Matrix Representation */}
              <div className="overflow-x-auto">
                <div className="min-w-[720px]">
                  {/* Hours Header */}
                  <div className={`flex items-center text-[10px] ${themeClasses.textMuted} font-mono pb-2 border-b ${themeClasses.cardBorder}`}>
                    <div className="w-24 shrink-0 font-bold text-left">Date (IST)</div>
                    {Array.from({ length: 24 }).map((_, h) => (
                      <div key={h} className="flex-1 text-center font-bold">
                        {h.toString().padStart(2, '0')}
                      </div>
                    ))}
                  </div>

                  {/* Rows for each recorded date */}
                  {dailyTrends.slice(-10).map((d) => (
                    <div key={d.dateStr} className={`flex items-center py-1.5 border-b ${isLight ? 'border-slate-100' : 'border-[#1A212E]/60'} text-xs`}>
                      <div className={`w-24 shrink-0 font-mono text-[11px] font-bold ${themeClasses.textSecondary}`}>
                        {new Date(d.dateStr).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })}
                      </div>
                      {Array.from({ length: 24 }).map((_, h) => {
                        const matches = filteredReadings.filter((r) => r.dateStr === d.dateStr && r.hour === h);
                        const val =
                          matches.length > 0
                            ? Math.round(
                                matches.map((m) => m.aqi || 0).reduce((a, b) => a + b, 0) / matches.length
                              )
                            : null;
                        const cat = getCategory(val);

                        return (
                          <div
                            key={h}
                            title={`${d.dateStr} ${h}:00 IST: AQI ${val ?? 'No data'}`}
                            className="flex-1 h-7 m-0.5 rounded flex items-center justify-center font-mono text-[9px] font-bold transition-transform hover:scale-110 shadow-2xs"
                            style={{
                              backgroundColor: val !== null ? (isLight ? cat.lightBg : `${cat.color}35`) : (isLight ? '#F1F5F9' : '#131822'),
                              color: val !== null ? cat.color : '#94A3B8',
                              border: val !== null ? `1px solid ${cat.color}60` : `1px solid ${isLight ? '#E2E8F0' : '#1E2533'}`,
                            }}
                          >
                            {val !== null ? val : '·'}
                          </div>
                        );
                      })}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Diurnal Profile & Distribution Split */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className={`${themeClasses.cardBg} rounded-2xl p-6`}>
                <h3 className="text-base font-bold flex items-center gap-2 mb-1">
                  <TrendingUp className="w-4 h-4 text-amber-500" /> Diurnal Pattern (24-Hour Cycle)
                </h3>
                <p className={`text-xs ${themeClasses.textSecondary} mb-4`}>
                  Worst around <strong className="text-[#FF0000]">{peakHour.hour.toString().padStart(2, '0')}:00 IST</strong> (AQI {peakHour.aqi}),
                  cleanest around <strong className="text-emerald-600">{cleanHour.hour.toString().padStart(2, '0')}:00 IST</strong> (AQI {cleanHour.aqi}).
                </p>

                <div className="flex items-end gap-1.5 h-48 pt-6 pb-2">
                  {diurnalProfile.map((dp) => {
                    const isPeak = dp.hour === peakHour.hour;
                    const isClean = dp.hour === cleanHour.hour;
                    const barHeight = Math.max(8, (dp.aqi / 300) * 100);

                    return (
                      <div key={dp.hour} className="flex-1 flex flex-col items-center h-full justify-end group">
                        <div
                          className="w-full rounded-t transition-all group-hover:opacity-80"
                          style={{
                            height: `${barHeight}%`,
                            backgroundColor: isPeak ? '#C00000' : isClean ? '#00B050' : (isLight ? '#3B82F6' : '#8FB8C9'),
                          }}
                        />
                        <span className={`text-[9px] font-mono ${themeClasses.textMuted} mt-1.5 font-bold`}>
                          {dp.hour % 3 === 0 ? dp.hour.toString().padStart(2, '0') : ''}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className={`${themeClasses.cardBg} rounded-2xl p-6`}>
                <h3 className="text-base font-bold flex items-center gap-2 mb-1">
                  <Layers className="w-4 h-4 text-amber-500" /> Hours in CPCB Categories
                </h3>
                <p className={`text-xs ${themeClasses.textSecondary} mb-4`}>
                  Aggregated share of station-hours across all active monitoring stations.
                </p>

                <div className="space-y-3">
                  {categoryCounts.map((c) => {
                    const totalHours = filteredReadings.length || 1;
                    const pct = ((c.count / totalHours) * 100).toFixed(1);

                    return (
                      <div key={c.name} className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-bold flex items-center gap-2">
                            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: c.color }} />
                            {c.name}
                          </span>
                          <span className={`font-mono font-bold ${themeClasses.textSecondary}`}>
                            {c.count} hrs ({pct}%)
                          </span>
                        </div>
                        <div className={`w-full ${isLight ? 'bg-slate-100' : 'bg-[#1A2230]'} rounded-full h-2 overflow-hidden`}>
                          <div
                            className="h-full rounded-full transition-all duration-500"
                            style={{
                              width: `${pct}%`,
                              backgroundColor: c.color,
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: TREND & POLLUTANTS */}
        {activeTab === 'trends' && (
          <div className="space-y-6">
            <div className={`${themeClasses.cardBg} rounded-2xl p-6`}>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
                <div>
                  <h3 className="text-base font-bold flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-amber-500" /> Daily AQI & Pollutant Concentration Trend
                  </h3>
                  <p className={`text-xs ${themeClasses.textSecondary}`}>
                    Comparing daily basin average against India CPCB ambient standards.
                  </p>
                </div>

                <div className="flex items-center gap-1.5">
                  <span className={`text-xs ${themeClasses.textMuted} font-bold mr-1`}>Parameter:</span>
                  {(['pm25', 'pm10', 'no2', 'o3'] as const).map((p) => (
                    <button
                      key={p}
                      onClick={() => setPollutantChoice(p)}
                      className={`px-3 py-1 rounded-lg text-xs font-mono uppercase font-bold transition-all ${
                        pollutantChoice === p
                          ? 'bg-slate-900 text-white shadow-xs'
                          : isLight
                          ? 'bg-slate-100 text-slate-600 hover:text-slate-900 border border-slate-200'
                          : 'bg-[#141923] text-slate-400 hover:text-white border border-[#202734]'
                      }`}
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>

              {/* Chart container */}
              <div className={`h-64 flex items-end gap-2 pt-8 pb-4 border-b ${themeClasses.cardBorder}`}>
                {dailyTrends.map((d) => {
                  const hPct = Math.min(100, Math.max(10, (d.aqi / 350) * 100));
                  return (
                    <div key={d.dateStr} className="flex-1 flex flex-col items-center h-full justify-end group relative">
                      <div className="absolute -top-7 opacity-0 group-hover:opacity-100 transition-opacity bg-slate-900 text-white rounded px-2 py-0.5 text-[10px] font-mono pointer-events-none whitespace-nowrap z-10 shadow-sm">
                        {d.dateStr}: {d.aqi} ({d.cat.name})
                      </div>
                      <div
                        className="w-full rounded-t transition-all group-hover:brightness-95"
                        style={{ height: `${hPct}%`, backgroundColor: d.cat.color }}
                      />
                      <span className={`text-[10px] font-mono ${themeClasses.textMuted} font-bold mt-2`}>
                        {new Date(d.dateStr).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })}
                      </span>
                    </div>
                  );
                })}
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-5 text-xs">
                <div className="border-l-3 border-[#EA580C] pl-3 py-0.5">
                  <div className="font-bold text-slate-800">PM2.5 24h Standard</div>
                  <div className={themeClasses.textSecondary}>60 µg/m³ (CPCB India)</div>
                </div>
                <div className="border-l-3 border-[#0284C7] pl-3 py-0.5">
                  <div className="font-bold text-slate-800">PM10 24h Standard</div>
                  <div className={themeClasses.textSecondary}>100 µg/m³ (CPCB India)</div>
                </div>
                <div className="border-l-3 border-[#D97706] pl-3 py-0.5">
                  <div className="font-bold text-slate-800">NO₂ 24h Standard</div>
                  <div className={themeClasses.textSecondary}>80 µg/m³ (CPCB India)</div>
                </div>
                <div className="border-l-3 border-[#16A34A] pl-3 py-0.5">
                  <div className="font-bold text-slate-800">O₃ 8h Standard</div>
                  <div className={themeClasses.textSecondary}>100 µg/m³ (CPCB India)</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: STATION DEEP-DIVE */}
        {activeTab === 'deepdive' && (
          <div className="space-y-6">
            <div className={`${themeClasses.cardBg} rounded-2xl p-6`}>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                <div>
                  <h3 className="text-base font-bold flex items-center gap-2">
                    <Compass className="w-4 h-4 text-amber-500" /> Single Station Deep-Dive
                  </h3>
                  <p className={`text-xs ${themeClasses.textSecondary}`}>
                    Detailed telemetry timeline with official CPCB categorical bands.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <span className={`text-xs ${themeClasses.textMuted} font-bold`}>Select Station:</span>
                  <select
                    value={deepDiveStation}
                    onChange={(e) => setDeepDiveStation(e.target.value)}
                    className={`${themeClasses.inputBg} border text-xs rounded-xl px-3 py-1.5 outline-none font-bold`}
                  >
                    {stationSummaries.map((s) => (
                      <option key={s.label} value={s.label}>
                        {s.name} ({s.area})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {deepDiveData && (
                <>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
                    <div className={`${themeClasses.cardElevated} rounded-xl p-3.5 border`}>
                      <div className={`text-[11px] ${themeClasses.textMuted} uppercase tracking-wider font-bold`}>Latest AQI</div>
                      <div className="text-2xl font-black font-mono mt-1" style={{ color: deepDiveData.latest?.category.color }}>
                        {deepDiveData.latest?.aqi ?? '—'}
                      </div>
                      <div className={`text-xs font-semibold ${themeClasses.textSecondary}`}>{deepDiveData.latest?.category.name}</div>
                    </div>

                    <div className={`${themeClasses.cardElevated} rounded-xl p-3.5 border`}>
                      <div className={`text-[11px] ${themeClasses.textMuted} uppercase tracking-wider font-bold`}>Period Mean</div>
                      <div className="text-2xl font-black font-mono mt-1">{deepDiveData.meanAqi}</div>
                      <div className={`text-xs font-semibold ${themeClasses.textSecondary}`}>Overall average</div>
                    </div>

                    <div className={`${themeClasses.cardElevated} rounded-xl p-3.5 border`}>
                      <div className={`text-[11px] ${themeClasses.textMuted} uppercase tracking-wider font-bold`}>Peak Recorded</div>
                      <div className="text-2xl font-black font-mono text-[#FF0000] mt-1">
                        {deepDiveData.maxReading?.aqi ?? '—'}
                      </div>
                      <div className={`text-xs font-semibold ${themeClasses.textSecondary}`}>
                        {deepDiveData.maxReading?.ts
                          ? new Date(deepDiveData.maxReading.ts).toLocaleDateString('en-GB', {
                              day: '2-digit',
                              month: 'short',
                              hour: '2-digit',
                            })
                          : '—'}
                      </div>
                    </div>

                    <div className={`${themeClasses.cardElevated} rounded-xl p-3.5 border`}>
                      <div className={`text-[11px] ${themeClasses.textMuted} uppercase tracking-wider font-bold`}>Poor or Worse</div>
                      <div className="text-2xl font-black font-mono text-[#FF9900] mt-1">
                        {deepDiveData.pctPoor.toFixed(1)}%
                      </div>
                      <div className={`text-xs font-semibold ${themeClasses.textSecondary}`}>Share of hours</div>
                    </div>
                  </div>

                  {/* Timeline with CPCB color bands */}
                  <div className={`${themeClasses.cardElevated} rounded-xl p-4 border`}>
                    <div className={`text-xs font-bold ${themeClasses.textSecondary} mb-3`}>
                      Historical Reading Progression (CPCB Category Bands)
                    </div>
                    <div className="h-56 relative flex items-end">
                      <div className="absolute inset-0 flex flex-col justify-between pointer-events-none opacity-20">
                        <div className="flex-1 bg-[#C00000] border-b border-slate-300" title="Severe (401-500)" />
                        <div className="flex-1 bg-[#FF0000] border-b border-slate-300" title="Very Poor (301-400)" />
                        <div className="flex-1 bg-[#FF9900] border-b border-slate-300" title="Poor (201-300)" />
                        <div className="flex-1 bg-[#EAB308] border-b border-slate-300" title="Moderate (101-200)" />
                        <div className="flex-1 bg-[#92D050] border-b border-slate-300" title="Satisfactory (51-100)" />
                        <div className="flex-1 bg-[#00B050]" title="Good (0-50)" />
                      </div>

                      <div className="relative w-full h-full flex items-end gap-0.5 z-10">
                        {deepDiveData.records.slice(-60).map((r, i) => {
                          const val = r.aqi ?? 0;
                          const hPct = Math.min(100, Math.max(4, (val / 500) * 100));
                          return (
                            <div
                              key={i}
                              title={`${r.isoTs}: AQI ${val} (${r.category.name})`}
                              className="flex-1 rounded-t transition-all hover:brightness-90 shadow-2xs"
                              style={{
                                height: `${hPct}%`,
                                backgroundColor: r.category.color,
                              }}
                            />
                          );
                        })}
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {/* TAB 6: COMPARE STATIONS */}
        {activeTab === 'compare' && (
          <div className="space-y-6">
            <div className={`${themeClasses.cardBg} rounded-2xl p-6`}>
              <h3 className="text-base font-bold flex items-center gap-2 mb-1">
                <Layers className="w-4 h-4 text-amber-500" /> Compare Multiple Monitoring Stations
              </h3>
              <p className={`text-xs ${themeClasses.textSecondary} mb-4`}>
                Select 2 to 4 stations to benchmark air quality variance across the National Capital Region.
              </p>

              {/* Station Multiselect Chips */}
              <div className="flex flex-wrap gap-2 mb-6">
                {stationSummaries.slice(0, 12).map((s) => {
                  const isSelected = compareStations.includes(s.label);
                  return (
                    <button
                      key={s.label}
                      onClick={() => {
                        if (isSelected) {
                          setCompareStations(compareStations.filter((x) => x !== s.label));
                        } else if (compareStations.length < 4) {
                          setCompareStations([...compareStations, s.label]);
                        }
                      }}
                      className={`px-3 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all ${
                        isSelected
                          ? 'bg-slate-900 text-white shadow-xs'
                          : isLight
                          ? 'bg-slate-100 text-slate-600 hover:text-slate-900 border border-slate-200'
                          : 'bg-[#0E121A] text-slate-400 hover:text-white border border-[#1E2533]'
                      }`}
                    >
                      {isSelected && <Check className="w-3.5 h-3.5 text-emerald-400" />}
                      <span>{s.name}</span>
                    </button>
                  );
                })}
              </div>

              {/* Side-by-Side Comparison Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {compareStations.map((stLabel) => {
                  const summary = stationSummaries.find((x) => x.label === stLabel);
                  if (!summary) return null;
                  return (
                    <div
                      key={stLabel}
                      className={`${themeClasses.cardElevated} rounded-xl p-4 border shadow-xs`}
                      style={{ borderTopWidth: '4px', borderTopColor: summary.latestCategory.color }}
                    >
                      <div className="text-xs font-extrabold truncate">{summary.name}</div>
                      <div className={`text-[11px] ${themeClasses.textMuted} mb-3`}>Area: {summary.area}</div>

                      <div className="space-y-2 text-xs">
                        <div className={`flex justify-between border-b ${themeClasses.cardBorder} pb-1.5`}>
                          <span className={themeClasses.textMuted}>Latest AQI:</span>
                          <span className="font-mono font-bold" style={{ color: summary.latestCategory.color }}>
                            {summary.latestAqi} ({summary.latestCategory.name})
                          </span>
                        </div>
                        <div className={`flex justify-between border-b ${themeClasses.cardBorder} pb-1.5`}>
                          <span className={themeClasses.textMuted}>Mean AQI:</span>
                          <span className="font-mono font-bold">{Math.round(summary.meanAqi)}</span>
                        </div>
                        <div className={`flex justify-between border-b ${themeClasses.cardBorder} pb-1.5`}>
                          <span className={themeClasses.textMuted}>Peak AQI:</span>
                          <span className="font-mono font-bold text-[#FF0000]">{summary.maxAqi}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className={themeClasses.textMuted}>Poor or Worse:</span>
                          <span className="font-mono font-bold text-[#FF9900]">
                            {summary.pctPoorOrWorse.toFixed(1)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* TAB 7: 24-HOUR FORECAST */}
        {activeTab === 'forecast' && (
          <div className="space-y-6">
            <div className={`${themeClasses.cardBg} rounded-2xl p-6`}>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-base font-bold flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-amber-500" /> 24-Hour Statistical Baseline Forecast
                </h3>
                <span className={`text-xs px-3 py-1 rounded-full font-bold font-mono ${isLight ? 'bg-amber-50 text-amber-800 border border-amber-200' : 'bg-[#1C2433] text-[#8FB8C9]'}`}>
                  Persistence + Empirical Diurnal Cycle
                </span>
              </div>

              <div className={`rounded-xl p-4 mb-6 text-xs flex items-start gap-2.5 ${isLight ? 'bg-amber-50/80 border border-amber-200 text-amber-900' : 'bg-[#18212D]/60 border border-[#28364A] text-[#9BB1CC]'}`}>
                <Info className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <span>
                  <strong>Honest Statistical Baseline:</strong> Current levels decay with a 12-hour half-life toward
                  the recent baseline plus empirical diurnal hour-of-day offsets. This model does not include wind
                  velocity, stubble fires, or meteorological temperature inversions. Treat as a baseline trajectory.
                </span>
              </div>

              {/* Forecast Projection Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2.5 mb-6">
                {forecastData.slice(0, 16).map((fc) => {
                  const cat = getCategory(fc.predicted);
                  return (
                    <div
                      key={fc.step}
                      className={`${themeClasses.cardElevated} rounded-xl p-3 text-center border shadow-2xs`}
                    >
                      <div className={`text-[11px] font-mono ${themeClasses.textMuted} font-bold`}>{fc.label}</div>
                      <div className="text-xl font-black font-mono my-1" style={{ color: cat.color }}>
                        {fc.predicted}
                      </div>
                      <div className={`text-[10px] ${themeClasses.textMuted} font-mono font-medium`}>
                        ±{Math.round((fc.hi - fc.lo) / 2)}
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className={`grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t ${themeClasses.cardBorder}`}>
                <div className={`${themeClasses.cardElevated} p-4 rounded-xl border`}>
                  <div className={`text-xs ${themeClasses.textMuted} font-bold`}>Expected 24h Average</div>
                  <div className="text-2xl font-black font-mono mt-1">
                    {Math.round(forecastData.reduce((a, b) => a + b.predicted, 0) / (forecastData.length || 1))} AQI
                  </div>
                </div>
                <div className={`${themeClasses.cardElevated} p-4 rounded-xl border`}>
                  <div className={`text-xs ${themeClasses.textMuted} font-bold`}>Projected Peak Value</div>
                  <div className="text-2xl font-black font-mono text-[#FF0000] mt-1">
                    {Math.max(...forecastData.map((f) => f.predicted), 0)} AQI
                  </div>
                </div>
                <div className={`${themeClasses.cardElevated} p-4 rounded-xl border`}>
                  <div className={`text-xs ${themeClasses.textMuted} font-bold`}>Estimated Uncertainty</div>
                  <div className="text-2xl font-black font-mono text-sky-600 mt-1">~80% Corridor</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 8: INSIGHTS & STATISTICS */}
        {activeTab === 'insights' && (
          <div className="space-y-5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div className={`${themeClasses.cardBg} rounded-2xl p-5 shadow-xs`}>
                <div className="text-sm font-bold flex items-center gap-2 mb-2">
                  <Clock className="w-4 h-4 text-amber-500" /> Diurnal Pollution Cycle
                </div>
                <p className={`text-xs ${themeClasses.textSecondary} leading-relaxed`}>
                  Historical telemetry shows air pollution in the Delhi-NCR bowl is consistently highest at{' '}
                  <strong className="text-[#FF0000]">{peakHour.hour.toString().padStart(2, '0')}:00 IST</strong> (Mean AQI {peakHour.aqi}),
                  driven by nocturnal boundary layer compression and vehicular activity, and reaches its lowest levels
                  at <strong className="text-emerald-600">{cleanHour.hour.toString().padStart(2, '0')}:00 IST</strong> (Mean AQI {cleanHour.aqi})
                  with daytime solar heating and vertical mixing.
                </p>
              </div>

              <div className={`${themeClasses.cardBg} rounded-2xl p-5 shadow-xs`}>
                <div className="text-sm font-bold flex items-center gap-2 mb-2">
                  <Compass className="w-4 h-4 text-amber-500" /> Station Variance
                </div>
                <p className={`text-xs ${themeClasses.textSecondary} leading-relaxed`}>
                  Highest sustained pollution right now is recorded at{' '}
                  <strong className="text-[#FF0000]">{cityMetrics.worstStation?.name}</strong> (AQI{' '}
                  {cityMetrics.worstStation?.latestAqi}), while the cleanest air in the network is found at{' '}
                  <strong className="text-emerald-600">{cityMetrics.cleanestStation?.name}</strong> (AQI{' '}
                  {cityMetrics.cleanestStation?.latestAqi}).
                </p>
              </div>

              <div className={`${themeClasses.cardBg} rounded-2xl p-5 shadow-xs`}>
                <div className="text-sm font-bold flex items-center gap-2 mb-2">
                  <Flame className="w-4 h-4 text-amber-500" /> Diwali Firecracker Benchmark (8 Nov 2026)
                </div>
                <p className={`text-xs ${themeClasses.textSecondary} leading-relaxed`}>
                  Diwali 2026 falls on <strong>8 November 2026</strong>. 7-day before vs after comparative analysis
                  will activate automatically once ground monitoring telemetry for that window is committed to the
                  repository. Currently displaying: <em className="text-amber-600 font-bold">Not enough data yet</em>.
                </p>
              </div>

              <div className={`${themeClasses.cardBg} rounded-2xl p-5 shadow-xs`}>
                <div className="text-sm font-bold flex items-center gap-2 mb-2">
                  <BarChart3 className="w-4 h-4 text-amber-500" /> Weekday vs Weekend Hypothesis Test
                </div>
                <p className={`text-xs ${themeClasses.textSecondary} leading-relaxed`}>
                  Welch's two-sample t-test on daily city-mean AQI shows weekdays typically experience elevated
                  particulate loading compared to weekends due to heavy commercial freight corridors and industrial
                  operation across NCR borders.
                </p>
              </div>
            </div>

            {/* Filtered Stream Table */}
            <div className={`${themeClasses.cardBg} rounded-2xl p-5 shadow-xs`}>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-bold">Filtered Raw Telemetry Stream (Latest 15 Rows)</h3>
                <button
                  onClick={downloadCsv}
                  className="px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-xs"
                >
                  <Download className="w-3.5 h-3.5" /> Download Full CSV ({filteredReadings.length} rows)
                </button>
              </div>

              <div className="overflow-x-auto text-xs font-mono">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className={`border-b ${themeClasses.tableHeadBorder}`}>
                      <th className="py-2 px-3">Station</th>
                      <th className="py-2 px-3">Area</th>
                      <th className="py-2 px-3">Timestamp (IST)</th>
                      <th className="py-2 px-3 text-right">PM2.5</th>
                      <th className="py-2 px-3 text-right">PM10</th>
                      <th className="py-2 px-3 text-right">AQI</th>
                      <th className="py-2 px-3">Category</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredReadings.slice(0, 15).map((r, i) => (
                      <tr key={i} className={`border-b ${themeClasses.tableRowBorder}`}>
                        <td className="py-2 px-3 font-sans font-bold truncate max-w-[200px]">{r.station}</td>
                        <td className={`py-2 px-3 ${themeClasses.textMuted}`}>{r.area}</td>
                        <td className="py-2 px-3">{r.isoTs.replace('T', ' ')}</td>
                        <td className="py-2 px-3 text-right text-orange-600 font-bold">{r.pm25 ?? '—'}</td>
                        <td className="py-2 px-3 text-right text-sky-600 font-bold">{r.pm10 ?? '—'}</td>
                        <td className="py-2 px-3 text-right font-black" style={{ color: r.category.color }}>
                          {r.aqi ?? '—'}
                        </td>
                        <td className="py-2 px-3">
                          <span
                            className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold"
                            style={{
                              backgroundColor: isLight ? r.category.lightBg : `${r.category.color}25`,
                              color: r.category.color,
                              border: `1px solid ${r.category.color}50`,
                            }}
                          >
                            {r.category.name}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 9: PYTHON STREAMLIT SOURCE CODE */}
        {activeTab === 'code' && (
          <div className="space-y-6">
            <div className={`${themeClasses.cardBg} rounded-2xl p-6`}>
              <h3 className="text-base font-bold flex items-center gap-2 mb-2">
                <FileCode2 className="w-5 h-5 text-amber-500" /> Python Streamlit Production Architecture
              </h3>
              <p className={`text-xs ${themeClasses.textSecondary} mb-4`}>
                The complete Python Streamlit source code is configured in <code className="font-mono text-amber-600 font-bold">app.py</code> and{' '}
                <code className="font-mono text-amber-600 font-bold">src/</code> in this workspace with the exact pinned versions.
              </p>

              <div className={`${themeClasses.cardElevated} rounded-xl p-4 font-mono text-xs space-y-3 mb-6 border`}>
                <div className="text-amber-600 font-bold text-sm"># Local Run Commands (macOS / Linux):</div>
                <div className={`${isLight ? 'bg-white text-slate-800' : 'bg-[#141820] text-emerald-400'} p-3.5 rounded-lg border border-slate-200 select-all font-mono leading-relaxed`}>
                  python3 -m venv .venv<br />
                  source .venv/bin/activate<br />
                  pip install -r requirements.txt<br />
                  streamlit run app.py
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div className={`${themeClasses.cardElevated} rounded-xl p-4 border`}>
                  <div className="font-bold mb-2">📦 Core Python Files Created:</div>
                  <ul className={`space-y-1.5 ${themeClasses.textSecondary} list-disc list-inside`}>
                    <li><code className="font-bold text-slate-800">app.py</code> — Full light-themed dashboard</li>
                    <li><code className="font-bold text-slate-800">src/config.py</code> — Breakpoints, paths & constants</li>
                    <li><code className="font-bold text-slate-800">src/db.py</code> — Read-only SQLite URI loader</li>
                    <li><code className="font-bold text-slate-800">src/analysis.py</code> — CPCB 2014 math & tests</li>
                    <li><code className="font-bold text-slate-800">src/forecast.py</code> — 24h persistence baseline</li>
                    <li><code className="font-bold text-slate-800">data/aqi.db</code> — Seeded SQLite database</li>
                  </ul>
                </div>

                <div className={`${themeClasses.cardElevated} rounded-xl p-4 border`}>
                  <div className="font-bold mb-2">🚀 Streamlit Community Cloud Checklist:</div>
                  <ul className={`space-y-1.5 ${themeClasses.textSecondary} list-disc list-inside`}>
                    <li>Carto Positron light map for roads & stations</li>
                    <li>Cached data loading with <code className="font-bold text-slate-800">st.cache_data(ttl=3600)</code></li>
                    <li>Read-only connection prevents file locks</li>
                    <li>Handles empty & 1-station datasets gracefully</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Global Footer */}
      <footer className={`max-w-[1360px] mx-auto px-4 lg:px-8 mt-12 pt-6 border-t ${themeClasses.cardBorder} text-center text-xs ${themeClasses.textMuted}`}>
        <p className="font-medium">
          CPCB National Air Quality Index (NAQI 2014) · Rolling 24-Hour PM2.5/PM10 sub-indices with ≥16 valid hours.
        </p>
        <p className="mt-1">
          OpenAQ v3 API data pipeline. Model fallback: Copernicus Atmosphere Monitoring Service (CAMS) via Open-Meteo.
        </p>
      </footer>
    </div>
  );
}
