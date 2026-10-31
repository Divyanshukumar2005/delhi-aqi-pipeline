# Delhi-NCR Air Quality Dashboard

Live air quality dashboard for Delhi-NCR built on hourly government monitor data and India's CPCB National AQI.

- **Data pipeline:** OpenAQ v3 -> GitHub Actions (3x/day) -> JSON in a repo -> fetched by the browser. A bundled copy in `public/data` is the fallback.
- **AQI maths:** computed client-side from raw PM2.5 / PM10 (24 h rolling mean, minimum 16 valid hours, CPCB breakpoints).
- **Views:** overview dial, real basemap with station pins (Leaflet + CARTO), day x hour and station x hour heatmaps, trends, station comparison, 24 h baseline forecast, insights with a Welch t-test, methodology.

## Run

```bash
npm install
npm run dev      # http://localhost:3000
npm run build    # production build in dist/
```

## Configuration

`VITE_DATA_BASE_URL` (optional) points the app at a different folder of `readings.json` / `stations.json`.
Default: `https://raw.githubusercontent.com/Divyanshukumar2005/delhi-aqi-pipeline/main/data`

## Deploy

Push to GitHub and import in Vercel. Build command `npm run build`, output directory `dist`.

## Stack

React 19, TypeScript, Vite, Tailwind CSS 4, Recharts, Leaflet, self-hosted fonts (Schibsted Grotesk, Spline Sans Mono).
