import { useEffect, useState } from 'react'

interface Segment {
  x1: number
  y1: number
  x2: number
  y2: number
}

/** The thin line from the active field row to its box on the page (DESIGN.md, differentiating detail).
 *  Both ends live in different scroll containers, so their positions are measured, not derived from render. */
export function LeaderLine({ fieldId }: { fieldId: number }) {
  const [seg, setSeg] = useState<Segment | null>(null)

  useEffect(() => {
    let frame = 0
    const measure = () => {
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(() => {
        const row = document.querySelector(`[data-field-id="${fieldId}"]`)
        const box = document.querySelector(`[data-box-id="${fieldId}"]`)
        const pageArea = document.querySelector('[data-page-scroller]')
        const fieldArea = document.querySelector('[data-field-scroller]')
        if (!row || !box || !pageArea || !fieldArea) return setSeg(null)
        const r = row.getBoundingClientRect()
        const b = box.getBoundingClientRect()
        const pa = pageArea.getBoundingClientRect()
        const fa = fieldArea.getBoundingClientRect()
        const rowVisible = r.bottom > fa.top && r.top < fa.bottom
        const boxVisible = b.bottom > pa.top && b.top < pa.bottom && b.right > pa.left && b.left < pa.right
        // side by side only; stacked on narrow screens the line would cross the page
        if (!rowVisible || !boxVisible || r.left < b.right) return setSeg(null)
        setSeg({ x1: Math.min(b.right, pa.right), y1: b.top + b.height / 2, x2: r.left, y2: r.top + Math.min(20, r.height / 2) })
      })
    }
    measure()
    window.addEventListener('resize', measure)
    document.addEventListener('scroll', measure, true)
    return () => {
      cancelAnimationFrame(frame)
      window.removeEventListener('resize', measure)
      document.removeEventListener('scroll', measure, true)
    }
  }, [fieldId])

  if (!seg) return null
  return (
    <svg aria-hidden className="pointer-events-none fixed inset-0 z-20 size-full">
      <line {...seg} stroke="var(--color-primary)" strokeWidth={1.5} strokeOpacity={0.8} />
      <circle cx={seg.x1} cy={seg.y1} r={3} fill="var(--color-primary)" />
    </svg>
  )
}
