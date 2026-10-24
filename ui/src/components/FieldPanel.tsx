import { Check, Crosshair, Pencil } from 'lucide-react'
import { useState } from 'react'
import type { Field } from '../api'
import { cn } from '../lib'
import { FieldBadge } from './StatusBadge'

interface RowProps {
  field: Field
  active: boolean
  editing: boolean
  reciting: boolean
  busy: boolean
  onSelect: () => void
  onApprove: () => void
  onEdit: () => void
  onRecite: () => void
  onSave: (value: string) => void
  onCancel: () => void
}

function FieldRow(p: RowProps) {
  const { field: f } = p
  const [draft, setDraft] = useState(f.value)
  return (
    <li
      data-field-id={f.id}
      aria-current={p.active || undefined}
      onClick={p.active ? undefined : p.onSelect}
      className={cn(
        'group flex cursor-pointer flex-col gap-1.5 rounded-md border-l-2 bg-surface p-3',
        p.active ? 'border-primary bg-surface-raised' : 'border-transparent hover:bg-surface-raised/70',
      )}
    >
      <div className="flex items-center gap-2">
        <span className="min-w-0 flex-1 truncate text-xs font-medium text-muted">
          {f.name}
          {f.item !== null && <span className="tabular-nums"> · item {f.item}</span>}
          {f.page === null && <span className="text-review"> · no box</span>}
        </span>
        <FieldBadge status={f.status} />
      </div>

      {p.editing ? (
        <form
          className="flex gap-2"
          // Enter submits through a synthetic click on Save; it must not reach the row and reset the selection
          onClick={(e) => e.stopPropagation()}
          onSubmit={(e) => {
            e.preventDefault()
            p.onSave(draft)
          }}
        >
          <label className="sr-only" htmlFor={`v${f.id}`}>
            Value for {f.name}
          </label>
          <input
            id={`v${f.id}`}
            autoFocus
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => e.key === 'Escape' && p.onCancel()}
            className="h-8 min-w-0 flex-1 rounded-sm border border-border bg-background px-2 font-mono tabular-nums"
          />
          <button type="submit" disabled={p.busy} className="h-8 cursor-pointer rounded-sm bg-primary px-2 text-background">
            Save
          </button>
          <button type="button" onClick={p.onCancel} className="h-8 cursor-pointer rounded-sm bg-surface-raised px-2">
            Cancel
          </button>
        </form>
      ) : (
        <p className="font-mono text-[15px] font-medium tabular-nums break-words">
          {f.value}
          {f.status === 'corrected' && f.extracted_value !== f.value && (
            <span className="ml-2 font-sans text-xs font-normal text-muted line-through">{f.extracted_value}</span>
          )}
        </p>
      )}

      {f.status === 'review' && f.reasons.length > 0 && (
        <ul className="flex flex-col gap-0.5 text-xs text-pretty text-muted">
          {f.reasons.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      )}

      {p.reciting && (
        <p className="text-xs text-primary">Click the words on the page, then press Enter to save or Esc to cancel.</p>
      )}

      {p.active && !p.editing && (
        <div className="flex flex-wrap gap-1.5 pt-1" onClick={(e) => e.stopPropagation()}>
          {(f.status === 'review' || f.status === 'auto') && (
            <button
              type="button"
              onClick={p.onApprove}
              disabled={p.busy}
              className="inline-flex h-7 cursor-pointer items-center gap-1 rounded-sm bg-approved px-2 text-xs font-medium text-background"
            >
              <Check aria-hidden className="size-3.5" /> Approve <kbd className="opacity-70">a</kbd>
            </button>
          )}
          <button
            type="button"
            onClick={p.onEdit}
            className="inline-flex h-7 cursor-pointer items-center gap-1 rounded-sm bg-surface px-2 text-xs ring-1 ring-border"
          >
            <Pencil aria-hidden className="size-3.5" /> Edit value <kbd className="text-muted">e</kbd>
          </button>
          <button
            type="button"
            onClick={p.onRecite}
            className={cn(
              'inline-flex h-7 cursor-pointer items-center gap-1 rounded-sm px-2 text-xs ring-1',
              p.reciting ? 'bg-primary text-background ring-primary' : 'bg-surface ring-border',
            )}
          >
            <Crosshair aria-hidden className="size-3.5" /> {p.reciting ? 'Picking words' : 'Fix box'}{' '}
            <kbd className={p.reciting ? 'opacity-70' : 'text-muted'}>c</kbd>
          </button>
        </div>
      )}
    </li>
  )
}

interface PanelProps extends Omit<RowProps, 'field' | 'active' | 'editing' | 'reciting' | 'onSelect'> {
  fields: Field[]
  activeId: number | null
  editingId: number | null
  recitingId: number | null
  onSelect: (id: number) => void
}

export function FieldPanel({ fields, activeId, editingId, recitingId, onSelect, ...actions }: PanelProps) {
  const review = fields.filter((f) => f.status === 'review')
  const rest = fields.filter((f) => f.status !== 'review')
  const row = (f: Field) => (
    <FieldRow
      key={f.id}
      field={f}
      active={f.id === activeId}
      editing={f.id === editingId}
      reciting={f.id === recitingId}
      onSelect={() => onSelect(f.id)}
      {...actions}
    />
  )
  return (
    <div className="flex flex-col gap-5">
      <section aria-labelledby="review-h" className="flex flex-col gap-1.5">
        <h2 id="review-h" className="flex items-center gap-2 text-xs font-medium text-muted">
          Needs review <span className="tabular-nums text-review">{review.length}</span>
        </h2>
        {review.length ? (
          <ul className="flex flex-col gap-1.5">{review.map(row)}</ul>
        ) : (
          <p className="rounded-md bg-surface p-3 text-pretty text-muted">
            Nothing waits for you here. Spot-check the boxes below, then export.
          </p>
        )}
      </section>
      <section aria-labelledby="checked-h" className="flex flex-col gap-1.5">
        <h2 id="checked-h" className="flex items-center gap-2 text-xs font-medium text-muted">
          Checked <span className="tabular-nums">{rest.length}</span>
        </h2>
        <ul className="flex flex-col gap-1.5">{rest.map(row)}</ul>
      </section>
    </div>
  )
}
