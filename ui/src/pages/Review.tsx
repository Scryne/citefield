import { Menu } from '@base-ui/react/menu'
import { Tabs } from '@base-ui/react/tabs'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  CircleCheck,
  Ellipsis,
  Keyboard,
  Minus,
  Plus,
  RotateCcw,
  Trash2,
  TriangleAlert,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, type DocumentDetail, type Field, type Trigger } from '../api'
import { Page } from '../components/AppShell'
import { useDocuments } from '../queries'
import { ConfirmDelete } from '../components/ConfirmDelete'
import { ExportMenu } from '../components/ExportMenu'
import { FieldPanel } from '../components/FieldPanel'
import { LeaderLine } from '../components/LeaderLine'
import { LineItems } from '../components/LineItems'
import { PageViewer } from '../components/PageViewer'
import { ShortcutsDialog } from '../components/ShortcutsDialog'
import { DocumentBadge } from '../components/StatusBadge'
import { Badge, Button, ErrorNote, IconButton, Skeleton } from '../components/ui'
import { buttonClass } from '../components/styles'
import { TRIGGER_LABEL, dateTime, plural } from '../format'
import { cn, linkProps, navigate, orderFields } from '../lib'

const ZOOMS = [1, 1.5, 2, 3]

// the same classification the server's overview uses (citefield.verify.TRIGGERS)
const TRIGGERS: [string, Trigger][] = [
  ['is also cited as', 'collision'],
  ['second read', 'second_read'],
  ['confidence', 'confidence'],
  ['does not hold', 'rule'],
  ['check digit', 'rule'],
  ['cited', 'citation'],
]
const trigger = (reason: string) => TRIGGERS.find(([k]) => reason.includes(k))?.[1] ?? 'rule'

export function Review({ id }: { id: string }) {
  const qc = useQueryClient()
  const doc = useQuery({
    queryKey: ['document', id],
    queryFn: () => api.document(id),
    refetchInterval: (q) => (q.state.data && ['queued', 'processing'].includes(q.state.data.status) ? 1500 : false),
  })
  const docs = useDocuments()
  const schema = useQuery({
    queryKey: ['schema', doc.data?.schema_name],
    queryFn: () => api.schema(doc.data!.schema_name),
    enabled: !!doc.data,
    staleTime: 60_000,
  })
  const [chosenId, setActiveId] = useState<number | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [recitingId, setRecitingId] = useState<number | null>(null)
  const [picked, setPicked] = useState<Set<number>>(new Set())
  const [pageIndex, setPageIndex] = useState(0)
  const [zoom, setZoom] = useState(0)
  const [tab, setTab] = useState<'values' | 'items' | 'checks'>('values')
  const [help, setHelp] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const ordered = useMemo(() => orderFields(doc.data?.field_list ?? []), [doc.data])
  // until the reviewer picks one, the first field in the queue is active, so its box is shown at once
  const activeId = chosenId ?? ordered[0]?.id ?? null
  const active = ordered.find((f) => f.id === activeId) ?? null
  // the page follows the active field; otherwise the reviewer's own choice
  const shownPage = active?.page ?? pageIndex
  const words = useQuery({
    queryKey: ['words', id, shownPage],
    queryFn: () => api.words(id, shownPage),
    enabled: recitingId !== null,
  })

  // the review queue across documents, oldest first, for [ and ]
  const { prev, next } = useMemo(() => {
    const queue = (docs.data ?? [])
      .filter((d) => d.to_review > 0 && d.id !== id)
      .sort((a, b) => a.created_at.localeCompare(b.created_at))
    const created = doc.data?.created_at ?? ''
    return {
      next: queue.find((d) => d.created_at > created) ?? queue[0] ?? null,
      prev: [...queue].reverse().find((d) => d.created_at < created) ?? queue.at(-1) ?? null,
    }
  }, [docs.data, id, doc.data?.created_at])

  const patch = useMutation({
    mutationFn: (v: { fieldId: number; body: Parameters<typeof api.patchField>[2] }) => api.patchField(id, v.fieldId, v.body),
    onSuccess: (field) => {
      qc.setQueryData<DocumentDetail>(['document', id], (d) => {
        if (!d) return d
        const list = d.field_list.map((f) => (f.id === field.id ? field : f))
        const counts = { auto: 0, review: 0, approved: 0, corrected: 0 }
        list.forEach((f) => counts[f.status]++)
        return { ...d, field_list: list, to_review: counts.review, counts }
      })
      setEditingId(null)
      setRecitingId(null)
      qc.invalidateQueries({ queryKey: ['documents'] })
      qc.invalidateQueries({ queryKey: ['stats'] })
    },
  })
  const retry = useMutation({
    mutationFn: () => api.retry(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['document', id] }),
  })
  const remove = useMutation({
    mutationFn: () => api.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['documents'] })
      navigate('/documents')
    },
  })

  const select = useCallback((fid: number) => {
    setActiveId(fid)
    setEditingId(null)
    setRecitingId(null)
  }, [])
  const step = useCallback(
    (by: number) => {
      if (!ordered.length) return
      const i = ordered.findIndex((f) => f.id === activeId)
      select(ordered[Math.min(ordered.length - 1, Math.max(0, i + by))].id)
    },
    [ordered, activeId, select],
  )
  // after an approval the reviewer lands on the next field still waiting, if there is one
  const approve = useCallback(
    (f: Field) =>
      patch.mutate(
        { fieldId: f.id, body: { approve: true } },
        {
          onSuccess: () => {
            const nextField = ordered.find((o) => o.status === 'review' && o.id !== f.id)
            if (nextField) setActiveId(nextField.id)
          },
        },
      ),
    [patch, ordered],
  )
  const startRecite = useCallback((f: Field) => {
    setActiveId(f.id)
    setEditingId(null)
    setRecitingId((cur) => (cur === f.id ? null : f.id))
    setPicked(new Set(f.evidence))
  }, [])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement
      if (t.closest('input, textarea, select, [role="dialog"], [role="alertdialog"], [role="menu"]') || e.metaKey || e.ctrlKey || e.altKey)
        return
      if (e.key === '?') setHelp(true)
      else if (e.key === ']' && next) navigate(`/d/${next.id}`)
      else if (e.key === '[' && prev) navigate(`/d/${prev.id}`)
      else if (e.key === 'j') step(1)
      else if (e.key === 'k') step(-1)
      else if (!active) return
      else if (e.key === 'a' && (active.status === 'review' || active.status === 'auto')) approve(active)
      else if (e.key === 'e') {
        setTab('values')
        setEditingId(active.id)
      } else if (e.key === 'c') startRecite(active)
      else if (e.key === 'Enter' && recitingId === active.id && picked.size)
        patch.mutate({ fieldId: active.id, body: { word_ids: [...picked] } })
      else if (e.key === 'Escape') {
        setEditingId(null)
        setRecitingId(null)
      } else return
      e.preventDefault()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [step, active, patch, recitingId, picked, startRecite, approve, next, prev])

  if (doc.isPending)
    return (
      <div aria-busy className="grid h-dvh gap-4 p-4 lg:grid-cols-[7fr_5fr]">
        <Skeleton className="h-full" />
        <Skeleton className="h-full" />
      </div>
    )
  if (doc.isError)
    return (
      <Page>
        <ErrorNote>
          Could not open this document: {doc.error.message}.{' '}
          <a {...linkProps('/documents')} className="underline">
            Back to documents
          </a>
        </ErrorNote>
      </Page>
    )

  const d = doc.data
  const page = d.pages[shownPage]
  const failedRules = d.rules.filter((r) => r.outcome === 'fails')
  const review = ordered.filter((f) => f.status === 'review')
  const blockers = new Map<Trigger, Field>()
  const blockerCount = new Map<Trigger, number>()
  for (const f of review)
    for (const t of new Set(f.reasons.map(trigger))) {
      if (!blockers.has(t)) blockers.set(t, f)
      blockerCount.set(t, (blockerCount.get(t) ?? 0) + 1)
    }
  const extracted = new Set(d.field_list.map((f) => f.name))
  const missing = (schema.data?.fields ?? []).map((f) => f.name).filter((n) => !extracted.has(n))
  const itemCount = new Set(d.field_list.filter((f) => f.item !== null).map((f) => f.item)).size

  const header = (
    <header className="bar sticky top-12 z-10 border-b border-border lg:top-0">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 px-4 py-2.5 sm:px-6">
        <nav aria-label="Breadcrumb" className="flex min-w-0 flex-1 basis-72 flex-col">
          <a {...linkProps('/documents')} className="w-fit text-xs text-muted hover:text-foreground hover:underline">
            Documents
          </a>
          <div className="flex min-w-0 items-center gap-2.5">
            <h1 className="truncate text-base font-semibold">{d.filename}</h1>
            <DocumentBadge doc={d} />
          </div>
        </nav>
        <dl className="hidden items-center gap-4 text-xs text-muted xl:flex">
          <div className="flex gap-1">
            <dt>Schema</dt>
            <dd className="font-mono text-foreground">{d.schema_name}</dd>
          </div>
          {d.pages.length > 0 && (
            <div className="flex gap-1">
              <dt className="sr-only">Pages</dt>
              <dd>{plural(d.pages.length, 'page')}</dd>
            </div>
          )}
          {d.model && (
            <div className="flex gap-1">
              <dt>Read by</dt>
              <dd className="font-mono text-foreground">{d.model}</dd>
            </div>
          )}
        </dl>
        <div className="flex items-center gap-1">
          <IconButton
            label={prev ? `Previous to review: ${prev.filename}` : 'No other document needs review'}
            icon={ChevronLeft}
            shortcut="["
            disabled={!prev}
            onClick={() => prev && navigate(`/d/${prev.id}`)}
          />
          <IconButton
            label={next ? `Next to review: ${next.filename}` : 'No other document needs review'}
            icon={ChevronRight}
            shortcut="]"
            disabled={!next}
            onClick={() => next && navigate(`/d/${next.id}`)}
          />
          <IconButton label="Keyboard shortcuts" icon={Keyboard} shortcut="?" onClick={() => setHelp(true)} />
          <Menu.Root>
            <Menu.Trigger
              aria-label="More actions"
              className="grid size-8 cursor-pointer place-items-center rounded-md text-muted hover:bg-surface-raised hover:text-foreground"
            >
              <Ellipsis aria-hidden className="size-4" />
            </Menu.Trigger>
            <Menu.Portal>
              <Menu.Positioner sideOffset={6} align="end" className="z-40">
                <Menu.Popup className="flex min-w-48 flex-col rounded-md border border-border bg-surface p-1 shadow-lg">
                  {d.status === 'failed' && (
                    <Menu.Item
                      onClick={() => retry.mutate()}
                      className="flex cursor-pointer items-center gap-2 rounded-sm px-2.5 py-1.5 data-[highlighted]:bg-surface-raised"
                    >
                      <RotateCcw aria-hidden className="size-4 text-muted" /> Read again
                    </Menu.Item>
                  )}
                  <Menu.Item
                    onClick={() => setConfirmDelete(true)}
                    className="flex cursor-pointer items-center gap-2 rounded-sm px-2.5 py-1.5 text-danger-fg data-[highlighted]:bg-surface-raised"
                  >
                    <Trash2 aria-hidden className="size-4" /> Delete document
                  </Menu.Item>
                </Menu.Popup>
              </Menu.Positioner>
            </Menu.Portal>
          </Menu.Root>
          {d.status === 'ready' && <ExportMenu href={(f) => api.exportUrl(id, f)} />}
        </div>
      </div>

      {d.status === 'ready' && (
        <div
          className={cn(
            'flex flex-wrap items-center gap-x-3 gap-y-2 border-t px-4 py-2 sm:px-6',
            review.length ? 'border-review/30 bg-review-fill' : 'border-approved/30 bg-approved-fill',
          )}
        >
          {review.length ? (
            <>
              <p className="flex items-center gap-2 font-medium text-review-fg">
                <CircleAlert aria-hidden className="size-4" />
                {review.length} of {plural(d.fields, 'value')} {review.length === 1 ? 'needs' : 'need'} review
              </p>
              <ul className="flex flex-wrap gap-1.5">
                {[...blockers.entries()].map(([t, f]) => (
                  <li key={t}>
                    <button
                      type="button"
                      onClick={() => {
                        setTab('values')
                        select(f.id)
                      }}
                      className="inline-flex h-6 cursor-pointer items-center gap-1.5 rounded-sm border border-review/40 bg-surface px-2 text-xs text-foreground hover:border-review"
                    >
                      {TRIGGER_LABEL[t]}
                      <span className="text-muted tabular-nums">{blockerCount.get(t)}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <>
              <p className="flex items-center gap-2 font-medium text-approved-fg">
                <CircleCheck aria-hidden className="size-4" />
                All {plural(d.fields, 'value')} checked
              </p>
              <span className="flex-1" />
              {next ? (
                <a {...linkProps(`/d/${next.id}`)} className={buttonClass('secondary', 'sm')}>
                  Next to review: <span className="max-w-48 truncate">{next.filename}</span>
                  <ChevronRight aria-hidden className="size-4" />
                </a>
              ) : (
                <span className="text-xs text-approved-fg">No other document waits for review.</span>
              )}
            </>
          )}
        </div>
      )}
    </header>
  )

  return (
    <div className="flex min-h-dvh flex-col lg:h-dvh">
      {header}

      {d.status !== 'ready' ? (
        <Page className="max-w-3xl">
          {d.status === 'failed' ? (
            <div className="flex flex-col items-start gap-3 rounded-lg border border-danger/30 bg-surface p-6">
              <p className="flex items-center gap-2 font-medium text-danger-fg">
                <TriangleAlert aria-hidden className="size-4" /> Reading this document failed
              </p>
              <p className="w-full rounded-md bg-surface-raised p-3 font-mono text-xs text-pretty break-words">{d.error}</p>
              <p className="text-pretty text-muted">
                Usually the model provider refused the request (key, quota or model name). Check Settings, then read it
                again; the file is kept.
              </p>
              <div className="flex gap-2">
                <Button variant="primary" icon={RotateCcw} onClick={() => retry.mutate()} disabled={retry.isPending}>
                  Read again
                </Button>
                <a {...linkProps('/settings')} className={buttonClass('secondary')}>
                  Open settings
                </a>
              </div>
              {retry.isError && <ErrorNote>Could not queue it: {retry.error.message}</ErrorNote>}
            </div>
          ) : (
            <div className="flex flex-col gap-3 rounded-lg border border-border bg-surface p-6">
              <p className="font-medium">Reading the document</p>
              <ol className="flex flex-col gap-1.5 text-muted">
                <li>1. Pages and words: text layer when the PDF has one, OCR otherwise.</li>
                <li>2. First read: page images and the words with their ids.</li>
                <li>3. Second read: page images only.</li>
                <li>4. Checks: agreement, arithmetic, check digits, citations.</li>
              </ol>
              <p className="text-xs text-muted">Under a minute for most documents. This page updates by itself.</p>
            </div>
          )}
        </Page>
      ) : (
        <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 p-4 sm:px-6 lg:grid-cols-[minmax(0,7fr)_minmax(24rem,5fr)]">
          <section aria-label="Document page" className="flex min-h-[60dvh] flex-col gap-2 lg:min-h-0">
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
              {d.pages.length > 1 ? (
                <div className="flex items-center gap-1">
                  <IconButton
                    label="Previous page"
                    icon={ChevronLeft}
                    disabled={shownPage === 0}
                    onClick={() => {
                      setActiveId(-1) // no field active: the page shown is the reviewer's choice
                      setPageIndex(shownPage - 1)
                    }}
                  />
                  <span className="tabular-nums">
                    Page {shownPage + 1} of {d.pages.length}
                  </span>
                  <IconButton
                    label="Next page"
                    icon={ChevronRight}
                    disabled={shownPage === d.pages.length - 1}
                    onClick={() => {
                      setActiveId(-1)
                      setPageIndex(shownPage + 1)
                    }}
                  />
                </div>
              ) : (
                <span>Page 1 of 1</span>
              )}
              <Badge>{page.source === 'pdf' ? 'Text layer' : 'OCR'}</Badge>
              <span className="flex-1" />
              <Legend />
              <div className="flex items-center gap-0.5 rounded-md border border-border bg-surface p-0.5">
                <IconButton label="Zoom out" icon={Minus} disabled={zoom === 0} onClick={() => setZoom((z) => Math.max(0, z - 1))} className="size-7" />
                <span className="w-11 text-center tabular-nums">{ZOOMS[zoom] * 100}%</span>
                <IconButton
                  label="Zoom in"
                  icon={Plus}
                  disabled={zoom === ZOOMS.length - 1}
                  onClick={() => setZoom((z) => Math.min(ZOOMS.length - 1, z + 1))}
                  className="size-7"
                />
              </div>
            </div>
            <PageViewer
              src={api.pageUrl(id, shownPage)}
              page={page}
              fields={d.field_list.filter((f) => f.page === shownPage)}
              activeId={activeId}
              onSelect={select}
              zoom={ZOOMS[zoom]}
              recite={
                recitingId !== null
                  ? {
                      words: words.data ?? [],
                      selected: picked,
                      toggle: (w) =>
                        setPicked((s) => {
                          const n = new Set(s)
                          if (n.has(w)) n.delete(w)
                          else n.add(w)
                          return n
                        }),
                    }
                  : null
              }
            />
          </section>

          <aside aria-label="Extracted values" className="flex min-h-0 flex-col rounded-lg border border-border bg-surface">
            <Tabs.Root value={tab} onValueChange={(v) => setTab(v as typeof tab)} className="flex min-h-0 flex-1 flex-col">
              <Tabs.List className="flex shrink-0 gap-1 border-b border-border px-2">
                {(
                  [
                    ['values', 'Values', d.fields],
                    ['items', 'Line items', itemCount],
                    ['checks', 'Checks', failedRules.length || d.rules.length],
                  ] as const
                ).map(([v, label, n]) => (
                  <Tabs.Tab
                    key={v}
                    value={v}
                    className="-mb-px flex h-10 cursor-pointer items-center gap-1.5 border-b-2 border-transparent px-2.5 text-muted hover:text-foreground data-[active]:border-primary data-[active]:font-medium data-[active]:text-foreground"
                  >
                    {label}
                    <span
                      className={cn(
                        'rounded-sm px-1 text-xs tabular-nums',
                        v === 'checks' && failedRules.length ? 'bg-review-fill text-review-fg' : 'bg-surface-raised',
                      )}
                    >
                      {n}
                    </span>
                  </Tabs.Tab>
                ))}
              </Tabs.List>

              {patch.isError && (
                <div className="px-3 pt-3">
                  <ErrorNote>Could not save: {patch.error.message}</ErrorNote>
                </div>
              )}

              <Tabs.Panel value="values" className="min-h-0 flex-1 overflow-y-auto p-3 outline-none" data-field-scroller>
                <FieldPanel
                  fields={ordered}
                  activeId={activeId}
                  editingId={editingId}
                  recitingId={recitingId}
                  busy={patch.isPending}
                  missing={missing}
                  onSelect={select}
                  onApprove={() => active && approve(active)}
                  onEdit={() => active && setEditingId(active.id)}
                  onRecite={() => active && startRecite(active)}
                  onSave={(value) => active && patch.mutate({ fieldId: active.id, body: { value } })}
                  onCancel={() => setEditingId(null)}
                />
              </Tabs.Panel>
              <Tabs.Panel value="items" className="min-h-0 flex-1 overflow-y-auto p-3 outline-none">
                <LineItems fields={d.field_list} activeId={activeId} onSelect={select} />
                {itemCount > 0 && (
                  <p className="pt-3 text-xs text-pretty text-muted">
                    Select a cell to see its box on the page. Cells that need review are tinted; edit them on the Values tab
                    (<kbd>e</kbd>).
                  </p>
                )}
              </Tabs.Panel>
              <Tabs.Panel value="checks" className="min-h-0 flex-1 overflow-y-auto p-3 outline-none">
                <Checks d={d} />
              </Tabs.Panel>
            </Tabs.Root>
          </aside>
        </div>
      )}

      {d.status === 'ready' && tab === 'values' && active?.box && active.page === shownPage && recitingId === null && (
        <LeaderLine fieldId={active.id} />
      )}
      <ShortcutsDialog open={help} onOpenChange={setHelp} />
      <ConfirmDelete
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title="Delete this document?"
        confirm="Delete document"
        onConfirm={() => remove.mutate()}
        busy={remove.isPending}
        error={remove.isError ? `Could not delete: ${remove.error.message}` : null}
      >
        {d.filename} and every value and correction in it will be removed. This cannot be undone.
      </ConfirmDelete>
    </div>
  )
}

function Legend() {
  const items = [
    ['var(--color-ink-review)', 'Needs review'],
    ['var(--color-ink-approved)', 'Checked'],
    ['var(--color-ink-corrected)', 'Corrected'],
  ]
  return (
    <ul aria-label="Box colours" className="hidden items-center gap-3 md:flex">
      {items.map(([c, label]) => (
        <li key={label} className="flex items-center gap-1.5">
          <span aria-hidden className="size-2.5 rounded-[3px] border-2" style={{ borderColor: c }} />
          {label}
        </li>
      ))}
    </ul>
  )
}

const OUTCOME = {
  holds: { tone: 'approved', label: 'Holds' },
  fails: { tone: 'review', label: 'Fails' },
  skipped: { tone: 'neutral', label: 'Skipped' },
} as const

function Checks({ d }: { d: DocumentDetail }) {
  const failed = d.rules.some((r) => r.outcome === 'fails')
  return (
    <div className="flex flex-col gap-5">
      <section aria-labelledby="rules-h" className="flex flex-col gap-2">
        <h2 id="rules-h" className="px-1 text-xs font-medium text-muted">
          Arithmetic
        </h2>
        {d.rules.length ? (
          <ul className="flex flex-col divide-y divide-border rounded-md border border-border">
            {d.rules.map((r) => (
              <li key={r.rule} className="flex items-start gap-3 px-3 py-2.5">
                <Badge tone={OUTCOME[r.outcome].tone} className="w-16 justify-center">
                  {OUTCOME[r.outcome].label}
                </Badge>
                <span className="min-w-0 flex-1 font-mono text-[13px] break-words">
                  {r.rule}
                  {r.detail && <span className="block font-sans text-xs text-muted">{r.detail}</span>}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="px-1 text-muted">This schema has no arithmetic rules.</p>
        )}
        {failed && (
          <p className="px-1 text-xs text-pretty text-muted">
            A failing rule sends every value in it to review: one of them is misread, or the document itself does not add
            up.
          </p>
        )}
      </section>

      {d.possibly_missed.length > 0 && (
        <section aria-labelledby="missed-h" className="flex flex-col gap-2">
          <h2 id="missed-h" className="px-1 text-xs font-medium text-muted">
            Possibly missed
          </h2>
          <ul className="flex flex-col divide-y divide-border rounded-md border border-border">
            {d.possibly_missed.map((m, i) => (
              <li key={i} className="flex flex-col gap-0.5 px-3 py-2.5">
                <span className="font-mono text-[13px]">
                  {m.field}
                  {m.item !== null && ` #${m.item}`} = {m.value}
                </span>
                <span className="text-xs text-muted">Only the second read (image only) saw this value.</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section aria-labelledby="info-h" className="flex flex-col gap-2">
        <h2 id="info-h" className="px-1 text-xs font-medium text-muted">
          Document
        </h2>
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 rounded-md border border-border px-3 py-2.5 text-[13px]">
          <dt className="text-muted">Uploaded</dt>
          <dd>{dateTime(d.created_at)}</dd>
          <dt className="text-muted">Schema</dt>
          <dd className="font-mono">{d.schema_name}</dd>
          <dt className="text-muted">Model</dt>
          <dd className="font-mono break-all">{d.model ?? '–'}</dd>
          <dt className="text-muted">Pages</dt>
          <dd>
            {d.pages.map((p) => `${p.index + 1}: ${p.source === 'pdf' ? 'text layer' : 'OCR'}`).join(', ') || '–'}
          </dd>
        </dl>
      </section>
    </div>
  )
}
