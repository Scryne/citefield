import { CircleAlert, CircleCheck, Loader, PenLine, ShieldCheck, TriangleAlert } from 'lucide-react'
import type { DocumentSummary, FieldStatus } from '../api'
import { DOCUMENT_STATUS_LABEL, FIELD_STATUS_LABEL } from '../format'
import { Badge, type Tone } from './ui'

const FIELD: Record<FieldStatus, { tone: Tone; icon: typeof CircleCheck }> = {
  review: { tone: 'review', icon: CircleAlert },
  auto: { tone: 'neutral', icon: ShieldCheck },
  approved: { tone: 'approved', icon: CircleCheck },
  corrected: { tone: 'corrected', icon: PenLine },
}

export function FieldBadge({ status }: { status: FieldStatus }) {
  const { tone, icon: Icon } = FIELD[status]
  return (
    <Badge tone={tone}>
      <Icon aria-hidden className="size-3" />
      {FIELD_STATUS_LABEL[status]}
    </Badge>
  )
}

/** A ready document is described by what is left to do in it, not by "ready". */
export function DocumentBadge({ doc }: { doc: Pick<DocumentSummary, 'status' | 'to_review'> }) {
  if (doc.status === 'ready')
    return doc.to_review ? (
      <Badge tone="review">
        <CircleAlert aria-hidden className="size-3" />
        Needs review
      </Badge>
    ) : (
      <Badge tone="approved">
        <CircleCheck aria-hidden className="size-3" />
        Checked
      </Badge>
    )
  if (doc.status === 'failed')
    return (
      <Badge tone="danger">
        <TriangleAlert aria-hidden className="size-3" />
        Failed
      </Badge>
    )
  return (
    <Badge tone="primary">
      <Loader aria-hidden className="size-3 animate-spin motion-reduce:animate-none" />
      {DOCUMENT_STATUS_LABEL[doc.status]}
    </Badge>
  )
}

/** Fields of one document by status as a thin stacked bar; the numbers are in the label next to it. */
export function StatusBar({ counts, className }: { counts: Record<FieldStatus, number>; className?: string }) {
  const total = counts.auto + counts.review + counts.approved + counts.corrected
  if (!total) return null
  const parts: [FieldStatus, string][] = [
    ['approved', 'bg-approved'],
    ['corrected', 'bg-corrected'],
    ['auto', 'bg-border-strong'],
    ['review', 'bg-review'],
  ]
  return (
    <span aria-hidden className={`flex h-1.5 overflow-hidden rounded-full bg-surface-raised ${className ?? ''}`}>
      {parts.map(([k, bg]) =>
        counts[k] ? <span key={k} className={bg} style={{ width: `${(counts[k] / total) * 100}%` }} /> : null,
      )}
    </span>
  )
}
