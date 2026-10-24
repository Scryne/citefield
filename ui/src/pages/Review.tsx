import { AlertDialog } from '@base-ui/react/alert-dialog'
import { Menu } from '@base-ui/react/menu'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, ChevronDown, Minus, Plus, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, type DocumentDetail, type Field } from '../api'
import { FieldPanel } from '../components/FieldPanel'
import { LeaderLine } from '../components/LeaderLine'
import { PageViewer } from '../components/PageViewer'
import { DocumentBadge } from '../components/StatusBadge'
import { navigate, orderFields } from '../lib'

const ZOOMS = [1, 1.5, 2, 3]

export function Review({ id }: { id: string }) {
  const qc = useQueryClient()
  const doc = useQuery({
    queryKey: ['document', id],
    queryFn: () => api.document(id),
    refetchInterval: (q) => (q.state.data && ['queued', 'processing'].includes(q.state.data.status) ? 1500 : false),
  })
  const [chosenId, setActiveId] = useState<number | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [recitingId, setRecitingId] = useState<number | null>(null)
  const [picked, setPicked] = useState<Set<number>>(new Set())
  const [pageIndex, setPageIndex] = useState(0)
  const [zoom, setZoom] = useState(0)

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

  const patch = useMutation({
    mutationFn: (v: { fieldId: number; body: Parameters<typeof api.patchField>[2] }) => api.patchField(id, v.fieldId, v.body),
    onSuccess: (field) => {
      qc.setQueryData<DocumentDetail>(['document', id], (d) =>
        d && {
          ...d,
          field_list: d.field_list.map((f) => (f.id === field.id ? field : f)),
          to_review: d.field_list.filter((f) => (f.id === field.id ? field : f).status === 'review').length,
        },
      )
      setEditingId(null)
      setRecitingId(null)
      qc.invalidateQueries({ queryKey: ['documents'] })
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
            const next = ordered.find((o) => o.status === 'review' && o.id !== f.id)
            if (next) setActiveId(next.id)
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
      if (t.closest('input, textarea, select, [role="dialog"], [role="menu"]') || e.metaKey || e.ctrlKey || e.altKey) return
      if (e.key === 'j') step(1)
      else if (e.key === 'k') step(-1)
      else if (!active) return
      else if (e.key === 'a' && (active.status === 'review' || active.status === 'auto')) approve(active)
      else if (e.key === 'e') setEditingId(active.id)
      else if (e.key === 'c') startRecite(active)
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
  }, [step, active, patch, recitingId, picked, startRecite, approve])

  if (doc.isPending) return <div aria-busy className="m-4 h-[80dvh] rounded-lg bg-surface" />
  if (doc.isError)
    return (
      <p role="alert" className="m-6 text-danger">
        Could not open this document: {doc.error.message}.{' '}
        <button type="button" className="cursor-pointer underline" onClick={() => navigate('/')}>
          Back to documents
        </button>
      </p>
    )

  const d = doc.data
  const page = d.pages[shownPage]
  const failedRules = d.rules.filter((r) => r.outcome === 'fails')

  return (
    <div className="flex h-[calc(100dvh-3rem)] flex-col">
      <header className="glass sticky top-0 z-10 flex flex-wrap items-center gap-3 border-b px-4 py-2">
        <button
          type="button"
          aria-label="Back to documents"
          onClick={() => navigate('/')}
          className="grid size-8 cursor-pointer place-items-center rounded-md hover:bg-surface-raised"
        >
          <ArrowLeft aria-hidden className="size-4" />
        </button>
        <h1 className="min-w-0 flex-1 basis-40 truncate text-lg font-semibold">{d.filename}</h1>
        <DocumentBadge status={d.status} />
        {d.status === 'ready' && (
          <span className="text-xs tabular-nums text-muted">
            {d.to_review ? <span className="text-review">{d.to_review} to review</span> : 'all checked'} · {d.fields} fields
          </span>
        )}
        {d.status === 'ready' && (
          <Menu.Root>
            <Menu.Trigger className="inline-flex h-8 cursor-pointer items-center gap-1 rounded-md bg-primary px-3 font-medium text-background">
              Export <ChevronDown aria-hidden className="size-4" />
            </Menu.Trigger>
            <Menu.Portal>
              <Menu.Positioner sideOffset={6} className="z-30">
                <Menu.Popup className="flex min-w-36 flex-col rounded-md border border-border bg-surface-raised p-1 shadow-lg">
                  {(['xlsx', 'csv', 'json'] as const).map((f) => (
                    <Menu.LinkItem
                      key={f}
                      href={api.exportUrl(id, f)}
                      download
                      className="cursor-pointer rounded-sm px-2 py-1.5 data-[highlighted]:bg-primary data-[highlighted]:text-background"
                    >
                      {f === 'xlsx' ? 'Excel (.xlsx)' : f === 'csv' ? 'CSV' : 'JSON'}
                    </Menu.LinkItem>
                  ))}
                </Menu.Popup>
              </Menu.Positioner>
            </Menu.Portal>
          </Menu.Root>
        )}
        <DeleteButton id={id} filename={d.filename} />
      </header>

      {d.status !== 'ready' ? (
        <div className="m-6 flex flex-col gap-2 rounded-lg bg-surface p-6">
          {d.status === 'failed' ? (
            <>
              <p className="font-medium text-danger">Reading this document failed.</p>
              <p className="font-mono text-xs text-pretty text-muted">{d.error}</p>
              <p className="text-muted">Check the provider settings of `citefield serve`, then upload the file again.</p>
            </>
          ) : (
            <p className="text-muted">Reading the document: two reads of every page, then the checks. This takes under a minute.</p>
          )}
        </div>
      ) : (
        <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 p-3 lg:grid-cols-[minmax(0,1.3fr)_minmax(22rem,1fr)]">
          <section aria-label="Document page" className="flex min-h-[50dvh] flex-col gap-2 lg:min-h-0">
            <div className="flex items-center gap-2 text-xs text-muted">
              {d.pages.length > 1 && (
                <label className="flex items-center gap-1">
                  Page
                  <select
                    value={shownPage}
                    onChange={(e) => {
                      setActiveId(null)
                      setPageIndex(Number(e.target.value))
                    }}
                    className="h-7 rounded-sm border border-border bg-surface-raised px-1 text-foreground"
                  >
                    {d.pages.map((p) => (
                      <option key={p.index} value={p.index}>
                        {p.index + 1} of {d.pages.length}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <span>{page.source === 'pdf' ? 'Text layer' : 'OCR'}</span>
              <span className="flex-1" />
              <button
                type="button"
                aria-label="Zoom out"
                disabled={zoom === 0}
                onClick={() => setZoom((z) => Math.max(0, z - 1))}
                className="grid size-7 cursor-pointer place-items-center rounded-sm bg-surface-raised disabled:opacity-40"
              >
                <Minus aria-hidden className="size-3.5" />
              </button>
              <span className="w-10 text-center tabular-nums">{ZOOMS[zoom] * 100}%</span>
              <button
                type="button"
                aria-label="Zoom in"
                disabled={zoom === ZOOMS.length - 1}
                onClick={() => setZoom((z) => Math.min(ZOOMS.length - 1, z + 1))}
                className="grid size-7 cursor-pointer place-items-center rounded-sm bg-surface-raised disabled:opacity-40"
              >
                <Plus aria-hidden className="size-3.5" />
              </button>
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

          <aside aria-label="Extracted fields" className="flex min-h-0 flex-col overflow-y-auto pr-1" data-field-scroller>
            {patch.isError && (
              <p role="alert" className="mb-2 rounded-md bg-danger/15 p-2 text-danger">
                Could not save: {patch.error.message}
              </p>
            )}
            <FieldPanel
              fields={ordered}
              activeId={activeId}
              editingId={editingId}
              recitingId={recitingId}
              busy={patch.isPending}
              onSelect={select}
              onApprove={() => active && approve(active)}
              onEdit={() => active && setEditingId(active.id)}
              onRecite={() => active && startRecite(active)}
              onSave={(value) => active && patch.mutate({ fieldId: active.id, body: { value } })}
              onCancel={() => setEditingId(null)}
            />
            <section aria-labelledby="checks-h" className="mt-5 flex flex-col gap-1.5 pb-4">
              <h2 id="checks-h" className="text-xs font-medium text-muted">
                Checks
              </h2>
              <ul className="flex flex-col gap-1 rounded-md bg-surface p-3 text-xs">
                {d.rules.map((r) => (
                  <li key={r.rule} className="flex gap-2">
                    <span
                      className={
                        r.outcome === 'holds' ? 'text-approved' : r.outcome === 'fails' ? 'text-review' : 'text-muted'
                      }
                    >
                      {r.outcome === 'holds' ? 'Holds' : r.outcome === 'fails' ? 'Fails' : 'Skipped'}
                    </span>
                    <span className="min-w-0 flex-1 font-mono break-words">
                      {r.rule}
                      {r.detail && <span className="text-muted"> ({r.detail})</span>}
                    </span>
                  </li>
                ))}
                {d.possibly_missed.map((m, i) => (
                  <li key={i} className="flex gap-2 text-muted">
                    <span className="text-review">Missed?</span>
                    <span className="font-mono">
                      the image-only read also saw {m.field} = {m.value}
                    </span>
                  </li>
                ))}
                {!d.rules.length && !d.possibly_missed.length && <li className="text-muted">No checks for this schema.</li>}
              </ul>
              {failedRules.length > 0 && (
                <p className="text-xs text-pretty text-muted">
                  A failing check sends every value in it to review: one of them is misread, or the document itself does not
                  add up.
                </p>
              )}
            </section>
          </aside>
        </div>
      )}
      {active?.box && active.page === shownPage && recitingId === null && <LeaderLine fieldId={active.id} />}
    </div>
  )
}

function DeleteButton({ id, filename }: { id: string; filename: string }) {
  const qc = useQueryClient()
  const remove = useMutation({
    mutationFn: () => api.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['documents'] })
      navigate('/')
    },
  })
  return (
    <AlertDialog.Root>
      <AlertDialog.Trigger
        aria-label="Delete document"
        className="grid size-8 cursor-pointer place-items-center rounded-md text-muted hover:bg-surface-raised hover:text-danger"
      >
        <Trash2 aria-hidden className="size-4" />
      </AlertDialog.Trigger>
      <AlertDialog.Portal>
        <AlertDialog.Backdrop className="fixed inset-0 z-40 bg-black/60" />
        <AlertDialog.Popup className="fixed top-1/2 left-1/2 z-40 flex w-[min(28rem,calc(100vw-2rem))] -translate-x-1/2 -translate-y-1/2 flex-col gap-3 rounded-lg border border-border bg-surface-raised p-5 shadow-xl">
          <AlertDialog.Title className="text-lg font-semibold text-balance">Delete this document?</AlertDialog.Title>
          <AlertDialog.Description className="text-pretty text-muted">
            {filename} and every value and correction in it will be removed. This cannot be undone.
          </AlertDialog.Description>
          {remove.isError && (
            <p role="alert" className="text-danger">
              Could not delete: {remove.error.message}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <AlertDialog.Close className="h-9 cursor-pointer rounded-md bg-surface px-3 ring-1 ring-border">Keep it</AlertDialog.Close>
            <button
              type="button"
              onClick={() => remove.mutate()}
              disabled={remove.isPending}
              className="h-9 cursor-pointer rounded-md bg-danger px-3 font-medium text-background"
            >
              Delete document
            </button>
          </div>
        </AlertDialog.Popup>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  )
}
