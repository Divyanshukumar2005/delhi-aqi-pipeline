import { useState } from 'react';
import { categoryOf } from '../lib/aqi';
import { CatBadge } from './ui';
import { fmtHour, pad2 } from '../lib/time';

export interface HeatRow { key: string; label: string; sub?: string; cells: (number | null)[] }

/** 24-column heatmap. Cells are solid CPCB colours with auto-contrast numbers. */
export function HeatGrid({ rows, rowHeader, readout }: { rows: HeatRow[]; rowHeader: string; readout: (row: HeatRow, hour: number, v: number | null) => string }) {
  const [hover, setHover] = useState<{ row: HeatRow; hour: number; v: number | null } | null>(null);
  return (
    <div>
      <div className="mb-3 flex min-h-[28px] items-center gap-3 text-[13px]">
        {hover ? (
          <>
            <span className="subtle">{readout(hover.row, hover.hour, hover.v)}</span>
            {hover.v !== null && <CatBadge cat={categoryOf(hover.v)} />}
          </>
        ) : (
          <span className="muted">Hover a cell for details</span>
        )}
      </div>
      <div className="scroll-x pb-2">
        <div className="min-w-[920px]" onMouseLeave={() => setHover(null)}>
          <div className="grid items-end gap-[3px] pb-1.5" style={{ gridTemplateColumns: '12rem repeat(24, minmax(0, 1fr))' }}>
            <div className="text-xs muted">{rowHeader}</div>
            {Array.from({ length: 24 }, (_, h) => (
              <div key={h} className={`num text-center text-[11px] ${h % 3 === 0 ? 'subtle' : 'muted'}`}>{pad2(h)}</div>
            ))}
          </div>
          <div className="space-y-[3px]">
            {rows.map((row) => (
              <div key={row.key} className="grid items-center gap-[3px]" style={{ gridTemplateColumns: '12rem repeat(24, minmax(0, 1fr))' }}>
                <div className="truncate pr-2 text-[13px] font-medium" title={row.label}>
                  {row.label}
                  {row.sub && <span className="ml-1.5 text-xs font-normal muted">{row.sub}</span>}
                </div>
                {row.cells.map((v, h) => {
                  const cat = v === null ? null : categoryOf(v);
                  return (
                    <div
                      key={h}
                      onMouseEnter={() => setHover({ row, hour: h, v })}
                      className="num grid h-7 cursor-default place-items-center rounded-[5px] text-[10.5px] font-medium transition-transform hover:z-10 hover:scale-[1.25]"
                      style={{ background: cat ? cat.fill : 'var(--surface-2)', color: cat ? cat.on : 'var(--ink-3)', border: cat ? 'none' : '1px dashed var(--line)' }}
                      aria-label={`${row.label} ${fmtHour(h)} ${v ?? 'no data'}`}
                    >
                      {v ?? ''}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
