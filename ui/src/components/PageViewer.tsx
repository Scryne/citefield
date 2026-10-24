import { useEffect, useRef } from 'react'
import type { Field, PageInfo, Word } from '../api'
import { cn } from '../lib'

const STATUS_STROKE: Record<Field['status'], string> = {
  review: 'var(--color-review)',
  auto: 'var(--color-approved)',
  approved: 'var(--color-approved)',
  corrected: 'var(--color-corrected)',
}

interface Props {
  src: string
  page: PageInfo
  fields: Field[]
  activeId: number | null
  onSelect: (id: number) => void
  zoom: number // 1 = fit width
  recite: { words: Word[]; selected: Set<number>; toggle: (id: number) => void } | null
}

/** The page image with every cited box drawn in page-pixel coordinates over it. */
export function PageViewer({ src, page, fields, activeId, onSelect, zoom, recite }: Props) {
  const scroller = useRef<HTMLDivElement>(null)
  const active = fields.find((f) => f.id === activeId && f.box)

  // keep the active box in view when the selection changes (DOM sync, not render logic)
  useEffect(() => {
    const el = scroller.current
    if (!el || !active?.box) return
    const scale = el.scrollWidth / page.width
    const [x0, y0, x1, y1] = active.box
    const top = y0 * scale - el.clientHeight / 3
    const left = ((x0 + x1) / 2) * scale - el.clientWidth / 2
    if (y0 * scale < el.scrollTop || y1 * scale > el.scrollTop + el.clientHeight || zoom > 1) {
      const instant = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      el.scrollTo({ top, left: zoom > 1 ? left : 0, behavior: instant ? 'auto' : 'smooth' })
    }
  }, [active?.id, active?.box, page.width, zoom])

  return (
    <div ref={scroller} className="relative min-h-0 flex-1 overflow-auto rounded-lg bg-surface p-3" data-page-scroller>
      <div className="relative mx-auto" style={{ width: `${zoom * 100}%`, aspectRatio: `${page.width} / ${page.height}` }}>
        <img
          src={src}
          alt={`Page ${page.index + 1}`}
          className="absolute inset-0 size-full rounded-sm bg-paper object-contain shadow-lg"
          draggable={false}
        />
        <svg
          viewBox={`0 0 ${page.width} ${page.height}`}
          preserveAspectRatio="none"
          className="absolute inset-0 size-full"
          role="presentation"
        >
          {recite?.words.map((w) => {
            const on = recite.selected.has(w.id)
            return (
              <rect
                key={`w${w.id}`}
                x={w.box[0] - 2}
                y={w.box[1] - 2}
                width={w.box[2] - w.box[0] + 4}
                height={w.box[3] - w.box[1] + 4}
                rx={3}
                onClick={() => recite.toggle(w.id)}
                className={cn(
                  'cursor-pointer',
                  on ? 'fill-primary-fill stroke-primary opacity-100' : 'fill-transparent stroke-primary/50 opacity-60 hover:opacity-100',
                )}
                strokeWidth={on ? 3 : 1.5}
                vectorEffect="non-scaling-stroke"
              >
                <title>{w.text}</title>
              </rect>
            )
          })}
          {!recite &&
            fields.map((f) => {
              if (!f.box) return null
              const isActive = f.id === activeId
              const [x0, y0, x1, y1] = f.box
              return (
                <rect
                  key={f.id}
                  data-box-id={f.id}
                  x={x0 - 4}
                  y={y0 - 4}
                  width={x1 - x0 + 8}
                  height={y1 - y0 + 8}
                  rx={4}
                  onClick={() => onSelect(f.id)}
                  className="cursor-pointer"
                  fill={isActive ? 'var(--color-primary-fill)' : 'transparent'}
                  stroke={isActive ? 'var(--color-primary)' : STATUS_STROKE[f.status]}
                  strokeOpacity={isActive ? 1 : 0.55}
                  strokeWidth={isActive ? 3 : 1.5}
                  vectorEffect="non-scaling-stroke"
                >
                  <title>{`${f.name}: ${f.value}`}</title>
                </rect>
              )
            })}
        </svg>
      </div>
    </div>
  )
}
