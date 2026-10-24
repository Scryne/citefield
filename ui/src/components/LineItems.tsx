import type { Field } from '../api'
import { fieldLabel } from '../format'
import { cn } from '../lib'

const CELL: Record<Field['status'], string> = {
  review: 'bg-review-fill text-review-fg',
  auto: '',
  approved: '',
  corrected: 'text-corrected-fg',
}

/** Line items as a grid, one row per item number; a cell is the field, so clicking it selects it like a row would. */
export function LineItems({
  fields,
  activeId,
  onSelect,
}: {
  fields: Field[]
  activeId: number | null
  onSelect: (id: number) => void
}) {
  const items = fields.filter((f) => f.item !== null)
  if (!items.length) return <p className="px-1 py-6 text-center text-muted">This document has no line items.</p>
  const columns = [...new Set(items.map((f) => f.name))]
  const rows = [...new Set(items.map((f) => f.item!))].sort((a, b) => a - b)
  const at = new Map(items.map((f) => [`${f.item}:${f.name}`, f]))
  // amounts and counts read better right-aligned; the anchor (name) column is text
  const numeric = (name: string) => items.some((f) => f.name === name && /^[-+]?[\d.,\s]+$/.test(f.value))
  return (
    <div className="overflow-x-auto rounded-md border border-border">
      <table className="w-full text-left text-[13px]">
        <thead className="bg-surface-raised text-xs text-muted">
          <tr className="h-8">
            <th className="w-10 px-2 font-medium">#</th>
            {columns.map((c) => (
              <th key={c} className={cn('px-2 font-medium whitespace-nowrap', numeric(c) && 'text-right')}>
                {fieldLabel(c.split('.').pop() ?? c)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {rows.map((n) => (
            <tr key={n}>
              <td className="px-2 py-1.5 text-muted tabular-nums">{n}</td>
              {columns.map((c) => {
                const f = at.get(`${n}:${c}`)
                if (!f) return <td key={c} className="px-2 text-muted">–</td>
                return (
                  <td key={c} className="p-0.5">
                    <button
                      type="button"
                      onClick={() => onSelect(f.id)}
                      aria-pressed={f.id === activeId}
                      aria-label={`${f.name} item ${n}: ${f.value}${f.status === 'review' ? ', needs review' : ''}`}
                      className={cn(
                        'w-full cursor-pointer rounded-sm px-1.5 py-1 font-mono tabular-nums hover:bg-surface-raised',
                        numeric(c) ? 'text-right' : 'text-left',
                        CELL[f.status],
                        f.id === activeId && 'ring-1 ring-primary ring-inset',
                      )}
                    >
                      {f.value}
                    </button>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
