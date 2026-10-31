import type { ReactNode } from 'react';
import { soft, type Category } from '../lib/aqi';

export function CatBadge({ cat, label }: { cat: Category; label?: string }) {
  return (
    <span className="badge" style={{ background: soft(cat, 16), color: cat.ink, border: `1px solid color-mix(in srgb, ${cat.fill} 45%, transparent)` }}>
      <span className="h-2 w-2 rounded-full" style={{ background: cat.fill }} />
      {label ?? cat.name}
    </span>
  );
}

export function Section({ title, hint, right, children, className = '' }: { title: ReactNode; hint?: ReactNode; right?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`card p-5 sm:p-6 ${className}`}>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="h-section">{title}</h3>
          {hint && <p className="mt-0.5 max-w-[68ch] text-[13px] subtle">{hint}</p>}
        </div>
        {right}
      </div>
      {children}
    </section>
  );
}

export function Stat({ label, value, sub, color }: { label: string; value: ReactNode; sub?: ReactNode; color?: string }) {
  return (
    <div className="card p-4">
      <div className="text-[13px] muted">{label}</div>
      <div className="num mt-1.5 text-[26px] font-semibold leading-tight" style={{ color: color ?? 'var(--ink)' }}>{value}</div>
      {sub && <div className="mt-0.5 text-[13px] subtle">{sub}</div>}
    </div>
  );
}


export function Empty({ children }: { children: ReactNode }) {
  return <div className="card-flat grid place-items-center p-10 text-center text-sm subtle">{children}</div>;
}
