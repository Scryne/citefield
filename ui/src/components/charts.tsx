// Plain SVG charts for the overview (DESIGN.md: one series, neutral axes, numbers also in text).
import { useState } from 'react'

/** Documents per day: one series of thin bars with a hover tooltip and a screen-reader table. */
export function DayBars({ data, label }: { data: { date: string; documents: number }[]; label: string }) {
  const [hover, setHover] = useState<number | null>(null)
  const max = Math.max(1, ...data.map((d) => d.documents))
  const W = 100 / data.length
  const day = (iso: string, opts: Intl.DateTimeFormatOptions) =>
    new Date(`${iso}T00:00:00`).toLocaleDateString('en-GB', opts)
  const h = hover === null ? null : data[hover]
  return (
    <figure className="flex flex-col gap-2">
      <div className="relative h-44">
        <span className="absolute top-0 left-0 text-xs tabular-nums text-muted">{max}</span>
        <span className="absolute bottom-0 left-0 text-xs tabular-nums text-muted">0</span>
        <svg
          aria-hidden
          className="absolute inset-y-0 right-0 left-6 h-full w-[calc(100%-1.5rem)] overflow-visible"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
        >
          <line x1="0" x2="100" y1="0.5" y2="0.5" className="stroke-border" strokeWidth="1" vectorEffect="non-scaling-stroke" strokeDasharray="2 3" />
          <line x1="0" x2="100" y1="100" y2="100" className="stroke-border-strong" strokeWidth="1" vectorEffect="non-scaling-stroke" />
          {data.map((d, i) => {
            const bh = (d.documents / max) * 100
            return (
              <g key={d.date}>
                <rect
                  x={i * W + W * 0.22}
                  width={W * 0.56}
                  y={100 - bh}
                  height={bh}
                  rx={0.6}
                  className={hover === null || hover === i ? 'fill-primary' : 'fill-primary/40'}
                />
                {/* hit target: the whole column, larger than the bar */}
                <rect
                  x={i * W}
                  width={W}
                  y={0}
                  height={100}
                  fill="transparent"
                  onMouseEnter={() => setHover(i)}
                  onMouseLeave={() => setHover(null)}
                />
              </g>
            )
          })}
        </svg>
        {h && hover !== null && (
          <div
            role="status"
            className="pointer-events-none absolute -top-2 z-10 -translate-x-1/2 -translate-y-full rounded-md border border-border bg-surface px-2.5 py-1.5 text-xs whitespace-nowrap shadow-md"
            style={{ left: `calc(1.5rem + (100% - 1.5rem) * ${(hover + 0.5) / data.length})` }}
          >
            <span className="text-muted">{day(h.date, { weekday: 'short', day: 'numeric', month: 'short' })}</span>{' '}
            <span className="font-medium tabular-nums">{h.documents}</span> {h.documents === 1 ? 'document' : 'documents'}
          </div>
        )}
      </div>
      <div aria-hidden className="ml-6 flex justify-between text-xs text-muted">
        <span>{day(data[0].date, { day: 'numeric', month: 'short' })}</span>
        <span>{day(data[Math.floor(data.length / 2)].date, { day: 'numeric', month: 'short' })}</span>
        <span>Today</span>
      </div>
      <table className="sr-only">
        <caption>{label}</caption>
        <thead>
          <tr>
            <th>Day</th>
            <th>Documents</th>
          </tr>
        </thead>
        <tbody>
          {data.map((d) => (
            <tr key={d.date}>
              <td>{d.date}</td>
              <td>{d.documents}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  )
}

/** Ranked horizontal bars with the label and number in text next to each bar. */
export function BarList({ rows, empty }: { rows: { label: string; value: number }[]; empty: string }) {
  const max = Math.max(1, ...rows.map((r) => r.value))
  if (!rows.length) return <p className="text-pretty text-muted">{empty}</p>
  return (
    <ul className="flex flex-col gap-3">
      {rows.map((r) => (
        <li key={r.label} className="flex flex-col gap-1.5">
          <div className="flex items-baseline gap-2">
            <span className="min-w-0 flex-1 truncate">{r.label}</span>
            <span className="font-medium tabular-nums">{r.value.toLocaleString('en')}</span>
          </div>
          <span aria-hidden className="h-1.5 rounded-full bg-surface-raised">
            <span className="block h-full rounded-full bg-primary" style={{ width: `${(r.value / max) * 100}%` }} />
          </span>
        </li>
      ))}
    </ul>
  )
}
