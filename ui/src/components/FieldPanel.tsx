import { Check, CircleAlert, Crosshair, MapPinOff, Pencil } from 'lucide-react'
import { useState } from 'react'
import type { Field } from '../api'
import { fieldLabel } from '../format'
import { cn } from '../lib'
import { FieldBadge } from './StatusBadge'

export interface RowActions {
  busy: boolean
  onApprove: () => void
  onEdit: () => void
  onRecite: () => void
  onSave: (value: string) => void
  onCancel: () => void
}

interface RowProps extends RowActions {
  field: Field
  active: boolean
  editing: boolean
  reciting: boolean
  onSelect: () => void
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
        'flex cursor-pointer flex-col gap-1.5 rounded-md border px-3 py-2.5 transition-colors duration-150',
        p.active
          ? 'border-primary bg-primary-tint'
          : 'border-transparent hover:border-border hover:bg-surface-raised/60',
      )}
    >
      <div className="flex items-center gap-2">
        <span className="flex min-w-0 flex-1 items-baseline gap-2">
          {/* the keyboard way to select a row (besides j/k); the row itself is a larger mouse target */}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              p.onSelect()
            }}
            aria-pressed={p.active}
            className="cursor-pointer truncate text-left text-[13px] font-medium"
          >
            {fieldLabel(f.name.split('.').pop() ?? f.name)}
          </button>
          <span className="truncate font-mono text-xs text-muted">
            {/* a flat key ("NUMBER", "due_date") is the label again; a dotted one says where the field belongs */}
            {f.name.includes('.') ? f.name : null}
            {f.item !== null && <span className="tabular-nums"> #{f.item}</span>}
          </span>
        </span>
        <FieldBadge status={f.status} />
      </div>

      {p.editing ? (
        <form
          className="flex flex-wrap gap-2"
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
            className="h-8 min-w-0 flex-1 basis-40 rounded-md border border-border-strong bg-surface px-2 font-mono tabular-nums"
          />
          <button
            type="submit"
            disabled={p.busy}
            className="h-8 cursor-pointer rounded-md bg-primary px-3 text-[13px] font-medium text-on-primary hover:bg-primary-hover"
          >
            Save
          </button>
          <button
            type="button"
            onClick={p.onCancel}
            className="h-8 cursor-pointer rounded-md border border-border-strong bg-surface px-3 text-[13px] hover:bg-surface-raised"
          >
            Cancel
          </button>
        </form>
      ) : (
        <p className="font-mono text-[15px] font-medium tabular-nums break-words">
          {f.value}
          {f.status === 'corrected' && f.extracted_value !== f.value && (
            <span className="ml-2 font-sans text-xs font-normal text-muted">
              read as <span className="line-through">{f.extracted_value}</span>
            </span>
          )}
        </p>
      )}

      {f.reasons.length > 0 && (f.status === 'review' || p.active) && (
        <ul className="flex flex-col gap-1 text-xs">
          {f.reasons.map((r) => (
            <li key={r} className={cn('flex gap-1.5 text-pretty', f.status === 'review' ? 'text-review-fg' : 'text-muted')}>
              <CircleAlert aria-hidden className="mt-px size-3.5 shrink-0" />
              <span>{r}</span>
            </li>
          ))}
        </ul>
      )}

      {f.page === null && (
        <p className="flex items-center gap-1.5 text-xs text-muted">
          <MapPinOff aria-hidden className="size-3.5" /> No box on the page. Fix it with the words it was read from.
        </p>
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
              aria-keyshortcuts="a"
              className="inline-flex h-7 cursor-pointer items-center gap-1.5 rounded-md bg-primary px-2.5 text-xs font-medium text-on-primary hover:bg-primary-hover disabled:opacity-60"
            >
              <Check aria-hidden className="size-3.5" /> Approve{' '}
              <kbd aria-hidden className="border-transparent bg-white/20 text-current">
                a
              </kbd>
            </button>
          )}
          <button
            type="button"
            onClick={p.onEdit}
            aria-keyshortcuts="e"
            className="inline-flex h-7 cursor-pointer items-center gap-1.5 rounded-md border border-border-strong bg-surface px-2.5 text-xs hover:bg-surface-raised"
          >
            <Pencil aria-hidden className="size-3.5" /> Edit value <kbd aria-hidden>e</kbd>
          </button>
          <button
            type="button"
            onClick={p.onRecite}
            aria-keyshortcuts="c"
            className={cn(
              'inline-flex h-7 cursor-pointer items-center gap-1.5 rounded-md border px-2.5 text-xs',
              p.reciting
                ? 'border-primary bg-primary text-on-primary'
                : 'border-border-strong bg-surface hover:bg-surface-raised',
            )}
          >
            <Crosshair aria-hidden className="size-3.5" /> {p.reciting ? 'Picking words' : 'Fix box'}{' '}
            <kbd aria-hidden className={p.reciting ? 'border-transparent bg-white/20 text-current' : ''}>
              c
            </kbd>
          </button>
        </div>
      )}
    </li>
  )
}

interface PanelProps extends RowActions {
  fields: Field[]
  activeId: number | null
  editingId: number | null
  recitingId: number | null
  onSelect: (id: number) => void
  missing: string[]
}

function Section({ id, title, count, tone, children }: { id: string; title: string; count: number; tone?: 'review'; children: React.ReactNode }) {
  return (
    <section aria-labelledby={id} className="flex flex-col gap-1">
      <h2 id={id} className="flex items-center gap-2 px-1 pb-1 text-xs font-medium text-muted">
        {title}
        <span className={cn('tabular-nums', tone === 'review' && count ? 'text-review-fg' : '')}>{count}</span>
      </h2>
      {children}
    </section>
  )
}

export function FieldPanel({ fields, activeId, editingId, recitingId, onSelect, missing, ...actions }: PanelProps) {
  const review = fields.filter((f) => f.status === 'review')
  const header = fields.filter((f) => f.status !== 'review' && f.item === null)
  const items = fields.filter((f) => f.status !== 'review' && f.item !== null)
  const byItem = new Map<number, Field[]>()
  for (const f of items) byItem.set(f.item!, [...(byItem.get(f.item!) ?? []), f])

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
      {review.length > 0 && (
        <Section id="review-h" title="Needs review" count={review.length} tone="review">
          <ul className="flex flex-col gap-1">{review.map(row)}</ul>
        </Section>
      )}
      {header.length > 0 && (
        <Section id="header-h" title="Document" count={header.length}>
          <ul className="flex flex-col gap-1">{header.map(row)}</ul>
        </Section>
      )}
      {byItem.size > 0 && (
        <Section id="items-h" title="Line items" count={byItem.size}>
          {[...byItem.entries()]
            .sort(([a], [b]) => a - b)
            .map(([n, fs]) => (
              <div key={n} className="flex flex-col gap-1 pb-1">
                <p className="px-1 text-xs text-muted tabular-nums">Item {n}</p>
                <ul className="flex flex-col gap-1">{fs.map(row)}</ul>
              </div>
            ))}
        </Section>
      )}
      {missing.length > 0 && (
        <Section id="missing-h" title="Not found on the document" count={missing.length}>
          <ul className="flex flex-wrap gap-1.5 px-1">
            {missing.map((m) => (
              <li key={m} className="rounded-sm border border-dashed border-border-strong px-1.5 py-0.5 font-mono text-xs text-muted">
                {m}
              </li>
            ))}
          </ul>
          <p className="px-1 pt-1 text-xs text-pretty text-muted">
            The schema asks for these, and neither read found them. Many are optional (a receipt rarely prints a due date).
          </p>
        </Section>
      )}
    </div>
  )
}
