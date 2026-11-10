/** CPCB National AQI (2014): categories, sub-index maths and colour tokens. */

export interface Category {
  id: number;
  name: string;
  min: number;
  max: number;
  /** Solid colour for fills, bars, map markers. */
  fill: string;
  /** Text-safe colour of the same hue (passes contrast on the page surface). */
  ink: string;
  /** Text colour to place on top of `fill`. */
  on: string;
  headline: string;
  action: string;
  sensitive: string;
}

const c = (i: number) => ({ fill: `var(--aqi-${i})`, ink: `var(--aqi-${i}-ink)`, on: `var(--aqi-${i}-on)` });

export const CATEGORIES: Category[] = [
  {
    id: 0, name: 'Good', min: 0, max: 50, ...c(0),
    headline: 'The air is clean and fresh',
    action: 'A good day for morning runs, outdoor sport and open windows.',
    sensitive: 'Minimal health impact for everyone.',
  },
  {
    id: 1, name: 'Satisfactory', min: 51, max: 100, ...c(1),
    headline: 'Air quality is acceptable',
    action: 'Normal outdoor activity can continue without restriction.',
    sensitive: 'Unusually sensitive people may notice minor breathing discomfort.',
  },
  {
    id: 2, name: 'Moderate', min: 101, max: 200, ...c(2),
    headline: 'Go easier on long outdoor workouts',
    action: 'Keep intense aerobic exercise short, especially near arterial roads.',
    sensitive: 'Children, older adults and people with asthma or heart conditions should take regular breaks.',
  },
  {
    id: 3, name: 'Poor', min: 201, max: 300, ...c(3),
    headline: 'Wear a mask on outdoor commutes',
    action: 'Avoid prolonged outdoor exertion. An N95 mask helps on roads and highways.',
    sensitive: 'People with lung or heart disease, pregnant women and children should limit time outside.',
  },
  {
    id: 4, name: 'Very Poor', min: 301, max: 400, ...c(4),
    headline: 'High pollution: restrict outdoor activity',
    action: 'Keep windows shut, skip outdoor jogging or cycling and run a HEPA purifier indoors.',
    sensitive: 'Sensitive groups should stay indoors. Healthy people may feel respiratory irritation.',
  },
  {
    id: 5, name: 'Severe', min: 401, max: 500, ...c(5),
    headline: 'Public health emergency: stay indoors',
    action: 'Avoid all outdoor activity and run purifiers in a sealed room. Seek care if breathing becomes difficult.',
    sensitive: 'Serious effects are possible even in healthy people.',
  },
];

export const POOR_OR_WORSE = 3;

export function categoryOf(aqi: number | null | undefined): Category {
  if (aqi === null || aqi === undefined || Number.isNaN(aqi)) return CATEGORIES[2];
  if (aqi <= 50) return CATEGORIES[0];
  if (aqi <= 100) return CATEGORIES[1];
  if (aqi <= 200) return CATEGORIES[2];
  if (aqi <= 300) return CATEGORIES[3];
  if (aqi <= 400) return CATEGORIES[4];
  return CATEGORIES[5];
}

/** Soft tinted background derived from a category fill. */
export const soft = (cat: Category, pct = 14) =>
  `color-mix(in srgb, ${cat.fill} ${pct}%, var(--surface))`;

/** [concLow, concHigh, indexLow, indexHigh] */
type Breakpoints = [number, number, number, number][];

export const BREAKPOINTS: Record<'pm25' | 'pm10', Breakpoints> = {
  pm25: [[0, 30, 0, 50], [30, 60, 50, 100], [60, 90, 100, 200], [90, 120, 200, 300], [120, 250, 300, 400], [250, 380, 400, 500]],
  pm10: [[0, 50, 0, 50], [50, 100, 50, 100], [100, 250, 100, 200], [250, 350, 200, 300], [350, 430, 300, 400], [430, 510, 400, 500]],
};

export function subIndex(conc: number | null, p: 'pm25' | 'pm10'): number | null {
  if (conc === null || Number.isNaN(conc) || conc < 0) return null;
  for (const [cLo, cHi, iLo, iHi] of BREAKPOINTS[p]) {
    if (conc <= cHi) return iLo + ((iHi - iLo) / (cHi - cLo)) * (conc - cLo);
  }
  return 500;
}

export function calculateAqi(pm25: number | null, pm10: number | null): number | null {
  const vals = [subIndex(pm25, 'pm25'), subIndex(pm10, 'pm10')].filter((v): v is number => v !== null);
  if (!vals.length) return null;
  return Math.min(500, Math.round(Math.max(...vals)));
}

export type Pollutant = 'pm25' | 'pm10' | 'no2' | 'o3';

export const POLLUTANTS: Record<Pollutant, { label: string; short: string; limit: number; limitNote: string }> = {
  pm25: { label: 'PM2.5', short: 'PM2.5', limit: 60, limitNote: 'CPCB 24-hour standard' },
  pm10: { label: 'PM10', short: 'PM10', limit: 100, limitNote: 'CPCB 24-hour standard' },
  no2: { label: 'NO2', short: 'NO2', limit: 80, limitNote: 'CPCB 24-hour standard' },
  o3: { label: 'O3', short: 'O3', limit: 100, limitNote: 'CPCB 8-hour standard' },
};

/**
 * Extended sub-index (not a CPCB value): above the top CPCB band it keeps the Severe band's slope instead of stopping at 500.
 * Private platforms show numbers like this, which is why their peaks are far above CPCB's.
 */
export function subIndexExt(conc: number | null, p: 'pm25' | 'pm10'): number | null {
  if (conc === null || Number.isNaN(conc) || conc < 0) return null;
  const [cLo, cHi, iLo, iHi] = BREAKPOINTS[p][BREAKPOINTS[p].length - 1];
  if (conc <= cHi) return subIndex(conc, p);
  return iHi + ((iHi - iLo) / (cHi - cLo)) * (conc - cHi);
}

export function calculateAqiExt(pm25: number | null, pm10: number | null): number | null {
  const vals = [subIndexExt(pm25, 'pm25'), subIndexExt(pm10, 'pm10')].filter((v): v is number => v !== null);
  return vals.length ? Math.round(Math.max(...vals)) : null;
}
