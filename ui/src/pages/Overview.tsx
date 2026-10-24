import { useQuery } from '@tanstack/react-query'
import { ArrowRight, CircleCheck, Download, FileSearch, ScanText, Upload } from 'lucide-react'
import { api, type FieldStatus, type Trigger } from '../api'
import { Page } from '../components/AppShell'
import { useDocuments } from '../queries'
import { BarList, DayBars } from '../components/charts'
import { DocumentBadge } from '../components/StatusBadge'
import { Badge, Button, Card, CardHeader, ErrorNote, PageHeader, Skeleton } from '../components/ui'
import { buttonClass } from '../components/styles'
import { UploadDialog } from '../components/UploadDialog'
import { FIELD_STATUS_LABEL, TRIGGER_LABEL, percent, plural, relativeTime } from '../format'
import { linkProps } from '../lib'

const DAYS = 14

const LEGEND: { status: FieldStatus; swatch: string }[] = [
  { status: 'auto', swatch: 'bg-border-strong' },
  { status: 'approved', swatch: 'bg-approved' },
  { status: 'corrected', swatch: 'bg-corrected' },
  { status: 'review', swatch: 'bg-review' },
]

export function Overview() {
  const docs = useDocuments()
  const stats = useQuery({
    queryKey: ['stats', DAYS, docs.dataUpdatedAt],
    queryFn: () => api.stats(DAYS),
    placeholderData: (prev) => prev,
  })

  const upload = (
    <UploadDialog
      trigger={
        <Button variant="primary" icon={Upload}>
          Upload documents
        </Button>
      }
    />
  )

  if (docs.isError || stats.isError)
    return (
      <Page>
        <PageHeader title="Overview" />
        <ErrorNote>
          Could not reach the Citefield server: {(docs.error ?? stats.error)?.message}. Check that `citefield serve` is
          running, then reload this page.
        </ErrorNote>
      </Page>
    )

  if (docs.isPending || stats.isPending)
    return (
      <Page>
        <PageHeader title="Overview" />
        <div aria-busy className="grid gap-4 lg:grid-cols-12">
          <Skeleton className="h-64 lg:col-span-7" />
          <Skeleton className="h-64 lg:col-span-5" />
          <Skeleton className="h-60 lg:col-span-8" />
          <Skeleton className="h-60 lg:col-span-4" />
        </div>
      </Page>
    )

  const all = docs.data
  const s = stats.data
  if (!all.length) return <FirstRun upload={upload} />

  // oldest first: the queue is worked in the order documents arrived
  const waiting = all.filter((d) => d.to_review > 0).sort((a, b) => a.created_at.localeCompare(b.created_at))
  const waitingFields = waiting.reduce((n, d) => n + d.to_review, 0)
  const checked = s.fields.auto + s.fields.approved + s.fields.corrected + s.fields.review
  const reading = s.documents.queued + s.documents.processing
  const triggers = (Object.entries(s.triggers) as [Trigger, number][]).map(([t, v]) => ({ label: TRIGGER_LABEL[t], value: v }))
  const inRange = s.per_day.reduce((n, d) => n + d.documents, 0)

  return (
    <Page>
      <PageHeader title="Overview" description={`What came in and what the checks did, last ${DAYS} days.`} actions={upload} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <Card aria-labelledby="queue-h" className="flex flex-col lg:col-span-7">
          <CardHeader
            id="queue-h"
            title="Waiting for you"
            hint={reading ? `${plural(reading, 'document')} still being read` : undefined}
          />
          {waiting.length ? (
            <div className="flex flex-1 flex-col gap-5 p-4">
              <div className="flex flex-wrap items-end gap-x-8 gap-y-3">
                <p className="flex flex-col">
                  <span className="text-[32px] leading-none font-semibold tabular-nums">{waitingFields}</span>
                  <span className="pt-1.5 text-muted">{waitingFields === 1 ? 'value to check' : 'values to check'}</span>
                </p>
                <p className="flex flex-col">
                  <span className="text-[32px] leading-none font-semibold tabular-nums text-muted">{waiting.length}</span>
                  <span className="pt-1.5 text-muted">{waiting.length === 1 ? 'document' : 'documents'}</span>
                </p>
                <span className="flex-1" />
                <a {...linkProps(`/d/${waiting[0].id}`)} className={buttonClass('primary')}>
                  Start reviewing <ArrowRight aria-hidden className="size-4" />
                </a>
              </div>
              <ul className="flex flex-col divide-y divide-border border-t border-border">
                {waiting.slice(0, 4).map((d) => (
                  <li key={d.id}>
                    <a {...linkProps(`/d/${d.id}`)} className="group flex items-center gap-3 py-2.5">
                      <span className="min-w-0 flex-1 truncate font-medium group-hover:text-primary">{d.filename}</span>
                      <span className="hidden text-xs text-muted sm:inline">{d.schema_name}</span>
                      <span className="w-24 text-right text-xs text-muted">{relativeTime(d.created_at)}</span>
                      <Badge tone="review" className="w-24 justify-center tabular-nums">
                        {plural(d.to_review, 'value')}
                      </Badge>
                    </a>
                  </li>
                ))}
              </ul>
              {waiting.length > 4 && (
                <a {...linkProps('/documents?tab=review')} className="-mt-2 text-primary hover:underline">
                  All {waiting.length} documents that need review
                </a>
              )}
            </div>
          ) : (
            <div className="flex flex-1 flex-col items-start justify-center gap-3 p-6">
              <span className="grid size-10 place-items-center rounded-lg bg-approved-fill text-approved-fg">
                <CircleCheck aria-hidden className="size-5" />
              </span>
              <p className="font-medium">Nothing waits for you.</p>
              <p className="max-w-[52ch] text-pretty text-muted">
                Every value in every document passed its checks or was confirmed by a person. Export what you need, or
                upload the next batch.
              </p>
              <a {...linkProps('/documents')} className={buttonClass('secondary')}>
                Go to documents
              </a>
            </div>
          )}
        </Card>

        <Card aria-labelledby="auto-h" className="flex flex-col lg:col-span-5">
          <CardHeader id="auto-h" title="Passed every check" hint={plural(checked, 'value')} />
          <div className="flex flex-1 flex-col gap-5 p-4">
            <p className="flex flex-col">
              <span className="text-[32px] leading-none font-semibold tabular-nums">{percent(s.auto_share, 1)}</span>
              <span className="pt-1.5 text-pretty text-muted">
                of extracted values were approved without a person. The rest were checked, corrected or still wait.
              </span>
            </p>
            {checked > 0 && (
              <div className="flex flex-col gap-3">
                <span aria-hidden className="flex h-2.5 gap-0.5 overflow-hidden rounded-full">
                  {LEGEND.map(({ status, swatch }) =>
                    s.fields[status] ? (
                      <span key={status} className={swatch} style={{ width: `${(s.fields[status] / checked) * 100}%` }} />
                    ) : null,
                  )}
                </span>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2">
                  {LEGEND.map(({ status, swatch }) => (
                    <div key={status} className="flex items-center gap-2">
                      <span aria-hidden className={`size-2 rounded-full ${swatch}`} />
                      <dt className="flex-1 text-muted">{FIELD_STATUS_LABEL[status]}</dt>
                      <dd className="font-medium tabular-nums">{s.fields[status].toLocaleString('en')}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            )}
            <dl className="mt-auto grid grid-cols-2 gap-4 border-t border-border pt-4">
              <div className="flex flex-col gap-0.5">
                <dt className="text-xs text-muted">Reading time per document</dt>
                <dd className="font-medium tabular-nums">
                  {s.seconds_per_document == null ? '–' : `${Math.round(s.seconds_per_document)} s`}
                </dd>
              </div>
              <div className="flex flex-col gap-0.5">
                <dt className="text-xs text-muted">Failed to read</dt>
                <dd className="font-medium tabular-nums">
                  {s.documents.failed ? (
                    <a {...linkProps('/documents?tab=failed')} className="text-danger-fg hover:underline">
                      {plural(s.documents.failed, 'document')}
                    </a>
                  ) : (
                    'None'
                  )}
                </dd>
              </div>
            </dl>
          </div>
        </Card>

        <Card aria-labelledby="days-h" className="lg:col-span-8">
          <CardHeader id="days-h" title="Documents per day" hint={`${plural(inRange, 'document')} in ${DAYS} days`} />
          <div className="p-4 pt-6">
            <DayBars data={s.per_day} label={`Documents uploaded per day, last ${DAYS} days`} />
          </div>
        </Card>

        <Card aria-labelledby="why-h" className="lg:col-span-4">
          <CardHeader id="why-h" title="Why values went to review" />
          <div className="p-4">
            <BarList rows={triggers} empty="No value has been sent to review yet." />
            {triggers.length > 0 && (
              <p className="pt-4 text-xs text-pretty text-muted">
                A value counts once for each check that flagged it, including values a person has since cleared.
              </p>
            )}
          </div>
        </Card>

        <Card aria-labelledby="recent-h" className="lg:col-span-12">
          <CardHeader
            id="recent-h"
            title="Recent documents"
            action={
              <a {...linkProps('/documents')} className="text-primary hover:underline">
                View all
              </a>
            }
          />
          <ul className="divide-y divide-border">
            {all.slice(0, 6).map((d) => (
              <li key={d.id}>
                <a {...linkProps(`/d/${d.id}`)} className="group flex items-center gap-3 px-4 py-2.5 hover:bg-surface-raised/60">
                  <span className="min-w-0 flex-1 truncate font-medium group-hover:text-primary">{d.filename}</span>
                  <span className="hidden w-24 text-xs text-muted md:inline">{d.schema_name}</span>
                  <span className="hidden w-28 text-xs text-muted sm:inline">{relativeTime(d.created_at)}</span>
                  <span className="flex w-32 justify-end">
                    <DocumentBadge doc={d} />
                  </span>
                </a>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </Page>
  )
}

function FirstRun({ upload }: { upload: React.ReactNode }) {
  const settings = useQuery({ queryKey: ['settings'], queryFn: api.settings, staleTime: 60_000 })
  const steps = [
    { icon: Upload, title: 'Upload', text: 'PDFs or photos of invoices and receipts, under a schema that names the fields.' },
    {
      icon: ScanText,
      title: 'Read and check',
      text: 'Each value is tied to the words it came from, read a second time, and checked against the arithmetic.',
    },
    {
      icon: FileSearch,
      title: 'Review what is flagged',
      text: 'Only values that failed a check wait for you, each with the reason and its box on the page.',
    },
    { icon: Download, title: 'Export', text: 'Excel, CSV or JSON. Every row keeps its page and box.' },
  ]
  return (
    <Page>
      <PageHeader title="Overview" />
      <Card className="grid gap-8 p-6 lg:grid-cols-12 lg:p-8">
        <div className="flex flex-col items-start gap-4 lg:col-span-5">
          <h2 className="text-xl font-semibold text-balance">Read your first document</h2>
          <p className="max-w-[48ch] text-pretty text-muted">
            Citefield extracts the fields you name, shows where on the page each value was read, and sends only the
            uncertain ones to you.
          </p>
          {upload}
          {settings.data && (
            <p className="max-w-[48ch] text-xs text-pretty text-muted">
              Files are stored in <span className="font-mono">{settings.data.data_dir}</span> and sent only to the model
              provider this instance uses ({settings.data.provider}
              {settings.data.model ? `, ${settings.data.model}` : ''}).
            </p>
          )}
        </div>
        <ol className="grid gap-x-6 gap-y-5 sm:grid-cols-2 lg:col-span-7">
          {steps.map((st, i) => (
            <li key={st.title} className="flex gap-3">
              <span className="grid size-8 shrink-0 place-items-center rounded-md bg-primary-tint text-primary">
                <st.icon aria-hidden className="size-4" />
              </span>
              <div className="flex flex-col gap-0.5">
                <p className="font-medium">
                  <span className="text-muted tabular-nums">{i + 1}.</span> {st.title}
                </p>
                <p className="text-pretty text-muted">{st.text}</p>
              </div>
            </li>
          ))}
        </ol>
      </Card>
    </Page>
  )
}
