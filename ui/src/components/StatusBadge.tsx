import type { DocumentSummary, FieldStatus } from '../api'
import { cn } from '../lib'

const FIELD: Record<FieldStatus, { label: string; className: string }> = {
  review: { label: 'Needs review', className: 'bg-review text-background' },
  auto: { label: 'Auto-approved', className: 'bg-surface-raised text-approved ring-1 ring-approved/40' },
  approved: { label: 'Approved', className: 'bg-approved text-background' },
  corrected: { label: 'Corrected', className: 'bg-corrected text-background' },
}

const DOCUMENT: Record<DocumentSummary['status'], { label: string; className: string }> = {
  queued: { label: 'Queued', className: 'bg-surface-raised text-muted ring-1 ring-border' },
  processing: { label: 'Reading', className: 'bg-surface-raised text-primary ring-1 ring-primary/50' },
  ready: { label: 'Ready', className: 'bg-surface-raised text-foreground ring-1 ring-border' },
  failed: { label: 'Failed', className: 'bg-danger text-background' },
}

function Badge({ label, className }: { label: string; className: string }) {
  return (
    <span className={cn('inline-flex shrink-0 items-center rounded-sm px-1.5 py-0.5 text-xs font-medium', className)}>
      {label}
    </span>
  )
}

export function FieldBadge({ status }: { status: FieldStatus }) {
  return <Badge {...FIELD[status]} />
}

export function DocumentBadge({ status }: { status: DocumentSummary['status'] }) {
  return <Badge {...DOCUMENT[status]} />
}
