import { useMemo } from 'react';
import { X } from 'lucide-react';
import { StationLines } from '../components/charts';
import { CatBadge, Empty, Section } from '../components/ui';
import type { Station } from '../lib/data';
import type { Model } from '../lib/model';

const COLORS = ['var(--s1)', 'var(--s2)', 'var(--s3)', 'var(--s4)'];
const MAX = 4;

export function StationsTab({ m, all, ids, setIds }: { m: Model; all: Station[]; ids: string[]; setIds: (ids: string[]) => void }) {
  const chosen = ids.map((id) => all.find((s) => s.id === id)).filter((s): s is Station => !!s);
  const options = m.stations.filter((s) => !ids.includes(s.id) && s.latest);

  const rows = useMemo(() => {
    const byT = new Map<number, Record<string, number | null>>();
    for (const s of chosen) for (const r of s.readings) {
      const row = byT.get(r.t) ?? { t: r.t };
      row[s.id] = r.aqi;
      byT.set(r.t, row);
    }
    const sorted = [...byT.values()].sort((a, b) => (a.t as number) - (b.t as number));
    // break the lines wherever the selected stations all went quiet for more than 3 hours
    const out: Record<string, number | null>[] = [];
    sorted.forEach((row, i) => {
      const prev = sorted[i - 1];
      if (prev && (row.t as number) - (prev.t as number) > 3 * 3600000) {
        out.push({ t: (prev.t as number) + 3600000, ...Object.fromEntries(chosen.map((s) => [s.id, null])) });
      }
      out.push(row);
    });
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ids, all]);

  return (
    <div className="space-y-5">
      <Section
        title="Station comparison"
        hint={`Pick up to ${MAX} stations. One station gives you a deep-dive; several show how far apart the same city can be.`}
        right={
          <select
            className="field"
            value=""
            disabled={ids.length >= MAX}
            onChange={(e) => e.target.value && setIds([...ids, e.target.value])}
            aria-label="Add a station"
          >
            <option value="">{ids.length >= MAX ? 'Maximum reached' : 'Add a station'}</option>
            {options.map((s) => <option key={s.id} value={s.id}>{s.short} ({s.area})</option>)}
          </select>
        }
      >
        <div className="mb-4 flex flex-wrap gap-2">
          {chosen.map((s, i) => (
            <span key={s.id} className="chip" style={{ cursor: 'default', color: 'var(--ink)' }}>
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: COLORS[i] }} />
              {s.short}
              <button aria-label={`Remove ${s.short}`} onClick={() => setIds(ids.filter((x) => x !== s.id))} className="-mr-1 grid h-5 w-5 place-items-center rounded-full hover:bg-[var(--surface-2)]"><X className="h-3.5 w-3.5" /></button>
            </span>
          ))}
        </div>
        {chosen.length ? (
          <StationLines rows={rows} series={chosen.map((s, i) => ({ key: s.id, name: s.short, color: COLORS[i] }))} />
        ) : (
          <Empty>Add a station above to see its AQI history.</Empty>
        )}
      </Section>

      {chosen.length > 0 && (
        <Section title="Side by side">
          <div className="scroll-x">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Station</th><th>Area</th><th className="text-right">Latest AQI</th><th>Category</th>
                  <th className="text-right">Mean</th><th className="text-right">Peak</th><th className="text-right">Poor or worse</th>
                  <th className="text-right">PM2.5</th><th className="text-right">PM10</th>
                </tr>
              </thead>
              <tbody>
                {chosen.map((s, i) => (
                  <tr key={s.id}>
                    <td className="font-semibold"><span className="mr-2 inline-block h-2.5 w-2.5 rounded-full" style={{ background: COLORS[i] }} />{s.short}</td>
                    <td className="muted">{s.area}</td>
                    <td className="num text-right font-semibold" style={{ color: s.latest?.cat.ink }}>{s.latest?.aqi ?? '–'}</td>
                    <td>{s.latest && <CatBadge cat={s.latest.cat} />}</td>
                    <td className="num text-right">{Math.round(s.mean)}</td>
                    <td className="num text-right">{s.max}</td>
                    <td className="num text-right">{s.pctPoor.toFixed(1)}%</td>
                    <td className="num text-right">{s.latest?.pm25 === null || !s.latest ? '–' : Math.round(s.latest.pm25!)}</td>
                    <td className="num text-right">{s.latest?.pm10 === null || !s.latest ? '–' : Math.round(s.latest.pm10!)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}
    </div>
  );
}
