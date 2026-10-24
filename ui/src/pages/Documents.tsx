import { Menu } from '@base-ui/react/menu'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowDown, ArrowUp, Ellipsis, FileImage, FileText, Inbox, RotateCcw, Search, Trash2, Upload, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import { api, type DocumentSummary } from '../api'
import { Page } from '../components/AppShell'
import { useDocuments } from '../queries'
import { ConfirmDelete } from '../components/ConfirmDelete'
import { ExportMenu } from '../components/ExportMenu'
import { DocumentBadge, StatusBar } from '../components/StatusBadge'
import { Button, Card, EmptyState, ErrorNote, PageHeader, Select, Skeleton } from '../components/ui'
import { inputClass } from '../components/styles'
import { UploadDialog } from '../components/UploadDialog'
import { dateTime, plural, relativeTime } from '../format'
import { cn, linkProps, navigate, useLocation } from '../lib'

const TABS = [
  { id: 'all', label: 'All', match: () => true },
  { id: 'review', label: 'Needs review', match: (d: DocumentSummary) => d.status === 'ready' && d.to_review > 0 },
  { id: 'checked', label: 'Checked', match: (d: DocumentSummary) => d.status === 'ready' && d.to_review === 0 },
  { id: 'reading', label: 'Reading', match: (d: DocumentSummary) => d.status === 'queued' || d.status === 'processing' },
  { id: 'failed', label: 'Failed', match: (d: DocumentSummary) => d.status === 'failed' },
] as const
type TabId = (typeof TABS)[number]['id']

type SortKey = 'created_at' | 'filename' | 'to_review'

function isImage(name: string) {
  return /\.(png|jpe?g|tiff?|webp)$/i.test(name)
}

export function Documents() {
  const { query } = useLocation()
  const tab = (TABS.find((t) => t.id === query.get('tab'))?.id ?? 'all') as TabId
  const docs = useDocuments()
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [schema, setSchema] = useState('')
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean }>({ key: 'created_at', desc: true })
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [confirmIds, setConfirmIds] = useState<string[] | null>(null)

  const remove = useMutation({
    mutationFn: (ids: string[]) => Promise.all(ids.map((id) => api.remove(id))),
    onSuccess: (_, ids) => {
      setSelected((s) => new Set([...s].filter((id) => !ids.includes(id))))
      setConfirmIds(null)
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['documents'] })
      qc.invalidateQueries({ queryKey: ['stats'] })
    },
  })
  const retry = useMutation({
    mutationFn: api.retry,
    onSettled: () => qc.invalidateQueries({ queryKey: ['documents'] }),
  })

  const all = useMemo(() => docs.data ?? [], [docs.data])
  const schemas = useMemo(() => [...new Set(all.map((d) => d.schema_name))].sort(), [all])
  const rows = useMemo(() => {
    const t = TABS.find((x) => x.id === tab)!
    const q = search.trim().toLowerCase()
    const out = all.filter((d) => t.match(d) && (!schema || d.schema_name === schema) && (!q || d.filename.toLowerCase().includes(q)))
    const dir = sort.desc ? -1 : 1
    return out.sort((a, b) => {
      const x = a[sort.key]
      const y = b[sort.key]
      return (typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y))) * dir
    })
  }, [all, tab, search, schema, sort])

  const visibleSelected = rows.filter((d) => selected.has(d.id))
  const allVisibleSelected = rows.length > 0 && visibleSelected.length === rows.length
  const notReady = visibleSelected.filter((d) => d.status !== 'ready')
  const toggle = (id: string) =>
    setSelected((s) => {
      const n = new Set(s)
      if (n.has(id)) n.delete(id)
      else n.add(id)
      return n
    })

  const setTab = (id: TabId) => navigate(id === 'all' ? '/documents' : `/documents?tab=${id}`, { replace: true })
  const sortBy = (key: SortKey) => setSort((s) => ({ key, desc: s.key === key ? !s.desc : key !== 'filename' }))
  const confirmDocs = all.filter((d) => confirmIds?.includes(d.id))

  const upload = (
    <UploadDialog
      trigger={
        <Button variant="primary" icon={Upload}>
          Upload documents
        </Button>
      }
    />
  )

  return (
    <Page>
      <PageHeader
        title="Documents"
        description="Everything uploaded to this instance. Open a document to see each value on its page."
        actions={upload}
      />

      <div role="group" aria-label="Filter by status" className="-mx-1 flex gap-1 overflow-x-auto px-1 pb-4">
        {TABS.map((t) => {
          const n = all.filter(t.match).length
          const active = t.id === tab
          return (
            <button
              key={t.id}
              type="button"
              aria-pressed={active}
              onClick={() => setTab(t.id)}
              className={cn(
                'inline-flex h-8 shrink-0 cursor-pointer items-center gap-2 rounded-md px-3 transition-colors duration-150',
                active ? 'bg-foreground text-background' : 'text-muted hover:bg-surface-raised hover:text-foreground',
              )}
            >
              {t.label}
              <span className={cn('text-xs tabular-nums', active ? 'opacity-80' : t.id === 'review' && n ? 'text-review-fg' : '')}>
                {n}
              </span>
            </button>
          )
        })}
      </div>

      <Card className="overflow-hidden">
        <div className="flex flex-wrap items-end gap-3 border-b border-border p-3">
          {visibleSelected.length ? (
            <div className="flex min-h-9 flex-1 flex-wrap items-center gap-2" aria-live="polite">
              <span className="font-medium">{plural(visibleSelected.length, 'document')} selected</span>
              <Button variant="ghost" size="sm" icon={X} onClick={() => setSelected(new Set())}>
                Clear
              </Button>
              <span className="flex-1" />
              {notReady.length > 0 && (
                <span className="text-xs text-muted">{plural(notReady.length, 'document')} not ready, not exported</span>
              )}
              <ExportMenu
                variant="secondary"
                label="Export selected"
                disabled={notReady.length === visibleSelected.length}
                href={(f) => api.exportManyUrl(visibleSelected.filter((d) => d.status === 'ready').map((d) => d.id), f)}
              />
              <Button variant="secondary" icon={Trash2} onClick={() => setConfirmIds(visibleSelected.map((d) => d.id))}>
                Delete
              </Button>
            </div>
          ) : (
            <>
              <label className="relative flex min-w-48 flex-1 basis-64 flex-col gap-1">
                <span className="sr-only">Search by file name</span>
                <Search aria-hidden className="pointer-events-none absolute top-2.5 left-2.5 size-4 text-muted" />
                <input
                  type="search"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search by file name"
                  className={cn(inputClass, 'pl-8')}
                />
              </label>
              <Select label="Schema" hideLabel value={schema} onChange={(e) => setSchema(e.target.value)} className="w-44">
                <option value="">All schemas</option>
                {schemas.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </Select>
            </>
          )}
        </div>

        {docs.isPending ? (
          <div aria-busy className="flex flex-col gap-2 p-3">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-10" />
            ))}
          </div>
        ) : docs.isError ? (
          <div className="p-4">
            <ErrorNote>
              Could not load documents: {docs.error.message}. Check that `citefield serve` is running, then reload.
            </ErrorNote>
          </div>
        ) : !all.length ? (
          <EmptyState icon={Inbox} title="No documents yet" action={upload}>
            Upload invoices or receipts. Each value comes back tied to the words it was read from.
          </EmptyState>
        ) : !rows.length ? (
          <EmptyState icon={Search} title="Nothing matches">
            {tab === 'review'
              ? 'No document waits for review. Every value has passed its checks or been confirmed.'
              : 'No document matches this filter.'}{' '}
            {(search || schema) && (
              <button
                type="button"
                className="cursor-pointer text-primary hover:underline"
                onClick={() => {
                  setSearch('')
                  setSchema('')
                }}
              >
                Clear the search
              </button>
            )}
          </EmptyState>
        ) : (
          <>
          <ul className="divide-y divide-border md:hidden">
            {rows.map((d) => (
              <li key={d.id} className={cn('flex items-start gap-3 px-3 py-3', selected.has(d.id) && 'bg-primary-tint')}>
                <input
                  type="checkbox"
                  aria-label={`Select ${d.filename}`}
                  checked={selected.has(d.id)}
                  onChange={() => toggle(d.id)}
                  className="mt-0.5 size-4 shrink-0 cursor-pointer accent-primary"
                />
                <a {...linkProps(`/d/${d.id}`)} className="flex min-w-0 flex-1 flex-col gap-1">
                  <span className="truncate font-medium">{d.filename}</span>
                  <span className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted">
                    <DocumentBadge doc={d} />
                    <span className="font-mono">{d.schema_name}</span>
                    <span>{relativeTime(d.created_at)}</span>
                  </span>
                  {d.status === 'ready' && (
                    <span className="text-xs tabular-nums text-muted">
                      {d.to_review ? <span className="font-medium text-review-fg">{d.to_review} to review</span> : 'all checked'} ·{' '}
                      {d.fields} values
                    </span>
                  )}
                  {d.status === 'failed' && <span className="line-clamp-2 text-xs text-danger-fg">{d.error}</span>}
                </a>
                <RowMenu doc={d} onDelete={() => setConfirmIds([d.id])} onRetry={() => retry.mutate(d.id)} />
              </li>
            ))}
          </ul>
          {/* relative: the sr-only header text is absolutely positioned and would otherwise escape the scroller */}
          <div className="relative hidden overflow-x-auto md:block">
            <table className="w-full min-w-[820px] table-fixed text-left">
              <thead className="bg-surface-raised text-xs text-muted">
                <tr className="h-9">
                  <th className="w-10 pl-3">
                    <input
                      type="checkbox"
                      aria-label="Select all shown documents"
                      checked={allVisibleSelected}
                      ref={(el) => {
                        if (el) el.indeterminate = visibleSelected.length > 0 && !allVisibleSelected
                      }}
                      onChange={() =>
                        setSelected((s) => {
                          const n = new Set(s)
                          rows.forEach((d) => (allVisibleSelected ? n.delete(d.id) : n.add(d.id)))
                          return n
                        })
                      }
                      className="size-4 cursor-pointer accent-primary"
                    />
                  </th>
                  <SortHeader label="File" k="filename" sort={sort} onSort={sortBy} />
                  <th className="w-28 font-medium">Schema</th>
                  <th className="w-36 font-medium">Status</th>
                  <SortHeader label="Values" k="to_review" sort={sort} onSort={sortBy} className="w-52" />
                  <SortHeader label="Uploaded" k="created_at" sort={sort} onSort={sortBy} className="w-36" />
                  <th className="w-12">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {rows.map((d) => (
                  <tr
                    key={d.id}
                    className={cn('h-12 hover:bg-surface-raised/60', selected.has(d.id) && 'bg-primary-tint hover:bg-primary-tint')}
                  >
                    <td className="pl-3">
                      <input
                        type="checkbox"
                        aria-label={`Select ${d.filename}`}
                        checked={selected.has(d.id)}
                        onChange={() => toggle(d.id)}
                        className="size-4 cursor-pointer accent-primary"
                      />
                    </td>
                    <td className="pr-3">
                      <a {...linkProps(`/d/${d.id}`)} className="group flex items-center gap-2.5">
                        {isImage(d.filename) ? (
                          <FileImage aria-hidden className="size-4 shrink-0 text-muted" />
                        ) : (
                          <FileText aria-hidden className="size-4 shrink-0 text-muted" />
                        )}
                        <span className="flex min-w-0 flex-col">
                          <span className="truncate font-medium group-hover:text-primary group-hover:underline">{d.filename}</span>
                          {d.page_count > 0 && <span className="text-xs text-muted">{plural(d.page_count, 'page')}</span>}
                        </span>
                      </a>
                    </td>
                    <td className="pr-3 font-mono text-[13px] text-muted">{d.schema_name}</td>
                    <td className="pr-3">
                      <DocumentBadge doc={d} />
                    </td>
                    <td className="pr-4">
                      {d.status === 'ready' ? (
                        <span className="flex flex-col gap-1">
                          <span className="text-xs tabular-nums">
                            {d.to_review ? (
                              <span className="font-medium text-review-fg">{d.to_review} to review</span>
                            ) : (
                              <span className="text-muted">all checked</span>
                            )}
                            <span className="text-muted"> · {d.fields} values</span>
                          </span>
                          <StatusBar counts={d.counts} className="w-full max-w-40" />
                        </span>
                      ) : d.status === 'failed' ? (
                        <span className="line-clamp-2 text-xs text-danger-fg" title={d.error ?? undefined}>
                          {d.error}
                        </span>
                      ) : (
                        <span className="text-xs text-muted">Two reads, then the checks</span>
                      )}
                    </td>
                    <td className="pr-3 text-xs text-muted" title={dateTime(d.created_at)}>
                      {relativeTime(d.created_at)}
                    </td>
                    <td className="pr-2">
                      <RowMenu
                        doc={d}
                        onDelete={() => setConfirmIds([d.id])}
                        onRetry={() => retry.mutate(d.id)}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          </>
        )}
        {rows.length > 0 && (
          <p className="border-t border-border px-4 py-2.5 text-xs text-muted">
            {rows.length === all.length ? plural(all.length, 'document') : `${rows.length} of ${plural(all.length, 'document')}`}
          </p>
        )}
      </Card>

      {retry.isError && (
        <div className="pt-3">
          <ErrorNote>Could not queue the document again: {retry.error.message}</ErrorNote>
        </div>
      )}

      <ConfirmDelete
        open={confirmIds !== null}
        onOpenChange={(o) => !o && setConfirmIds(null)}
        title={confirmDocs.length === 1 ? 'Delete this document?' : `Delete ${confirmDocs.length} documents?`}
        confirm={confirmDocs.length === 1 ? 'Delete document' : `Delete ${confirmDocs.length} documents`}
        onConfirm={() => confirmIds && remove.mutate(confirmIds)}
        busy={remove.isPending}
        error={remove.isError ? `Could not delete: ${remove.error.message}` : null}
      >
        {confirmDocs.length === 1
          ? `${confirmDocs[0]?.filename} and every value and correction in it will be removed.`
          : 'These files and every value and correction in them will be removed.'}{' '}
        This cannot be undone.
      </ConfirmDelete>
    </Page>
  )
}

function SortHeader({
  label,
  k,
  sort,
  onSort,
  className,
}: {
  label: string
  k: SortKey
  sort: { key: SortKey; desc: boolean }
  onSort: (k: SortKey) => void
  className?: string
}) {
  const active = sort.key === k
  const Arrow = sort.desc ? ArrowDown : ArrowUp
  return (
    <th className={cn('font-medium', className)} aria-sort={active ? (sort.desc ? 'descending' : 'ascending') : 'none'}>
      <button
        type="button"
        onClick={() => onSort(k)}
        className={cn('inline-flex cursor-pointer items-center gap-1 hover:text-foreground', active && 'text-foreground')}
      >
        {label}
        {active && <Arrow aria-hidden className="size-3" />}
      </button>
    </th>
  )
}

function RowMenu({ doc, onDelete, onRetry }: { doc: DocumentSummary; onDelete: () => void; onRetry: () => void }) {
  const item = 'flex cursor-pointer items-center gap-2 rounded-sm px-2.5 py-1.5 data-[highlighted]:bg-surface-raised'
  return (
    <Menu.Root>
      <Menu.Trigger
        aria-label={`Actions for ${doc.filename}`}
        className="grid size-8 cursor-pointer place-items-center rounded-md text-muted hover:bg-surface-raised hover:text-foreground"
      >
        <Ellipsis aria-hidden className="size-4" />
      </Menu.Trigger>
      <Menu.Portal>
        <Menu.Positioner sideOffset={4} align="end" className="z-40">
          <Menu.Popup className="flex min-w-48 flex-col rounded-md border border-border bg-surface p-1 shadow-lg">
            <Menu.Item className={item} onClick={() => navigate(`/d/${doc.id}`)}>
              <FileText aria-hidden className="size-4 text-muted" /> Open
            </Menu.Item>
            {doc.status === 'ready' &&
              (['xlsx', 'csv', 'json'] as const).map((f) => (
                <Menu.LinkItem key={f} href={api.exportUrl(doc.id, f)} download className={item}>
                  <span className="w-4" />
                  Export {f === 'xlsx' ? 'Excel' : f.toUpperCase()}
                </Menu.LinkItem>
              ))}
            {doc.status === 'failed' && (
              <Menu.Item className={item} onClick={onRetry}>
                <RotateCcw aria-hidden className="size-4 text-muted" /> Read again
              </Menu.Item>
            )}
            <Menu.Separator className="my-1 h-px bg-border" />
            <Menu.Item className={cn(item, 'text-danger-fg')} onClick={onDelete}>
              <Trash2 aria-hidden className="size-4" /> Delete
            </Menu.Item>
          </Menu.Popup>
        </Menu.Positioner>
      </Menu.Portal>
    </Menu.Root>
  )
}
