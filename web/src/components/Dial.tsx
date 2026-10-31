import { CATEGORIES, type Category } from '../lib/aqi';

const CX = 150, CY = 140, R = 104, SW = 20, START = 135, SWEEP = 270;
const rad = (d: number) => (d * Math.PI) / 180;
const pt = (deg: number, r = R) => [CX + r * Math.cos(rad(deg)), CY + r * Math.sin(rad(deg))] as const;
const angle = (v: number) => START + (Math.min(500, Math.max(0, v)) / 500) * SWEEP;

function arc(v0: number, v1: number, gap = 0.9) {
  const a0 = angle(v0) + (v0 > 0 ? gap : 0);
  const a1 = angle(v1) - (v1 < 500 ? gap : 0);
  const [x0, y0] = pt(a0);
  const [x1, y1] = pt(a1);
  const large = a1 - a0 > 180 ? 1 : 0;
  return { d: `M ${x0.toFixed(2)} ${y0.toFixed(2)} A ${R} ${R} 0 ${large} 1 ${x1.toFixed(2)} ${y1.toFixed(2)}`, len: rad(a1 - a0) * R };
}

/** 270° AQI dial. Segment widths are proportional to the real CPCB ranges, so the marker position is honest. */
export function Dial({ value, cat }: { value: number | null; cat: Category }) {
  const v = value ?? 0;
  const [kx, ky] = pt(angle(v));
  return (
    <div className="relative mx-auto w-full max-w-[340px]" role="img" aria-label={`Delhi-NCR AQI ${value ?? 'unavailable'}, ${cat.name}`}>
      <svg viewBox="0 0 300 244" className="block w-full overflow-visible">
        {CATEGORIES.map((c, i) => {
          const lo = i === 0 ? 0 : c.min - 1;
          const hi = c.max;
          const track = arc(lo, hi);
          const filled = Math.min(1, Math.max(0, (v - lo) / (hi - lo)));
          const part = filled > 0 ? arc(lo, lo + (hi - lo) * filled) : null;
          return (
            <g key={c.name}>
              <path d={track.d} fill="none" stroke={c.fill} strokeWidth={SW} strokeOpacity={0.2} />
              {part && (
                <path
                  d={part.d}
                  fill="none"
                  stroke={c.fill}
                  strokeWidth={SW}
                  className="dial-seg"
                  style={{ strokeDasharray: part.len, ['--len' as string]: part.len, animationDelay: `${i * 0.09}s` }}
                />
              )}
            </g>
          );
        })}

        {[0, 100, 200, 300, 400, 500].map((t) => {
          const [x, y] = pt(angle(t), R + 24);
          return (
            <text key={t} x={x} y={y} textAnchor="middle" dominantBaseline="middle" fontSize="11" fill="var(--ink-3)" className="num">
              {t}
            </text>
          );
        })}

        <circle cx={kx} cy={ky} r={SW / 2 + 5} fill="var(--surface)" stroke={cat.fill} strokeWidth="3.5" style={{ transition: 'all 0.6s' }} />
        <circle cx={kx} cy={ky} r="4" fill={cat.fill} />
      </svg>

      <div className="pointer-events-none absolute left-1/2 top-[56%] -translate-x-1/2 -translate-y-1/2 text-center">
        <div className="num text-[64px] font-semibold leading-none" style={{ color: cat.ink }}>
          {value ?? '–'}
        </div>
        <div className="mt-2 text-xs muted">National AQI</div>
      </div>
    </div>
  );
}
