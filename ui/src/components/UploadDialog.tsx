import { Dialog } from '@base-ui/react/dialog'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { CircleCheck, FileUp, Loader, TriangleAlert, Upload, X } from 'lucide-react'
import { useId, useRef, useState, type ReactNode } from 'react'
import { api } from '../api'
import { cn, navigate } from '../lib'
import { Button, Select } from './ui'

const ACCEPT = 'application/pdf,image/png,image/jpeg,image/tiff,image/webp'

interface Item {
  file: File
  state: 'waiting' | 'sending' | 'sent' | 'failed'
  error?: string
  id?: string
}

/** Upload one or more files under one schema. Each file reports on its own line; one failure does not stop the rest. */
export function UploadDialog({ trigger, defaultSchema = 'invoice' }: { trigger: ReactNode; defaultSchema?: string }) {
  const qc = useQueryClient()
  const inputId = useId()
  const fileInput = useRef<HTMLInputElement>(null)
  const [open, setOpen] = useState(false)
  const [schema, setSchema] = useState(defaultSchema)
  const [items, setItems] = useState<Item[]>([])
  const [dragging, setDragging] = useState(false)
  const schemas = useQuery({ queryKey: ['schemas'], queryFn: api.schemas, enabled: open })
  const chosen = schemas.data?.find((s) => s.name === schema)
  const busy = items.some((i) => i.state === 'sending')
  const done = items.length > 0 && items.every((i) => i.state === 'sent' || i.state === 'failed')

  const add = (list: FileList | null) => {
    if (!list?.length) return
    // copy now: the input's FileList is live and is emptied when the input is reset right after this call
    const added = [...list].map((file) => ({ file, state: 'waiting' as const }))
    setItems((cur) => [...cur.filter((i) => i.state !== 'sent'), ...added])
  }

  const send = async () => {
    for (let i = 0; i < items.length; i++) {
      if (items[i].state !== 'waiting' && items[i].state !== 'failed') continue
      setItems((cur) => cur.map((it, j) => (j === i ? { ...it, state: 'sending', error: undefined } : it)))
      try {
        const { id } = await api.upload(items[i].file, schema)
        setItems((cur) => cur.map((it, j) => (j === i ? { ...it, state: 'sent', id } : it)))
      } catch (e) {
        const error = e instanceof Error ? e.message : String(e)
        setItems((cur) => cur.map((it, j) => (j === i ? { ...it, state: 'failed', error } : it)))
      }
    }
    qc.invalidateQueries({ queryKey: ['documents'] })
    qc.invalidateQueries({ queryKey: ['stats'] })
  }

  const close = (next: boolean) => {
    if (busy) return
    setOpen(next)
    if (!next) setItems([])
  }

  const pending = items.filter((i) => i.state === 'waiting' || i.state === 'failed').length

  return (
    <Dialog.Root open={open} onOpenChange={close}>
      <Dialog.Trigger render={trigger as React.ReactElement} />
      <Dialog.Portal>
        <Dialog.Backdrop className="fixed inset-0 z-50 bg-black/40" />
        <Dialog.Popup className="fixed top-1/2 left-1/2 z-50 flex max-h-[min(44rem,calc(100dvh-2rem))] w-[min(36rem,calc(100vw-2rem))] -translate-x-1/2 -translate-y-1/2 flex-col rounded-lg border border-border bg-surface shadow-xl">
          <header className="flex items-start gap-3 border-b border-border px-5 py-4">
            <div className="flex flex-1 flex-col gap-0.5">
              <Dialog.Title className="text-base font-semibold">Upload documents</Dialog.Title>
              <Dialog.Description className="text-pretty text-muted">
                Each file is read twice and checked. Anything uncertain goes to the review queue with the reason.
              </Dialog.Description>
            </div>
            <Dialog.Close
              aria-label="Close"
              disabled={busy}
              className="grid size-8 cursor-pointer place-items-center rounded-md text-muted hover:bg-surface-raised"
            >
              <X aria-hidden className="size-4" />
            </Dialog.Close>
          </header>

          <div className="flex min-h-0 flex-col gap-4 overflow-y-auto px-5 py-4">
            <div className="flex flex-col gap-1">
              <Select label="Schema" value={schema} onChange={(e) => setSchema(e.target.value)} disabled={busy}>
                {(schemas.data ?? [{ name: defaultSchema }]).map((s) => (
                  <option key={s.name} value={s.name}>
                    {s.name}
                  </option>
                ))}
              </Select>
              {chosen && (
                <p className="text-xs text-muted">
                  {chosen.fields.length} fields, {chosen.rules.length} arithmetic {chosen.rules.length === 1 ? 'rule' : 'rules'}
                  {chosen.description && chosen.description !== chosen.name ? `: ${chosen.description}` : ''}
                </p>
              )}
            </div>

            <label
              htmlFor={inputId}
              onDragOver={(e) => {
                e.preventDefault()
                setDragging(true)
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault()
                setDragging(false)
                add(e.dataTransfer.files)
              }}
              className={cn(
                'flex cursor-pointer flex-col items-center gap-2 rounded-lg border border-dashed border-border-strong px-4 py-8 text-center transition-colors duration-150',
                'hover:border-primary hover:bg-primary-tint',
                // the input inside is visually hidden; its focus shows on the drop zone
                'focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-primary',
                dragging && 'border-primary bg-primary-tint',
              )}
            >
              <FileUp aria-hidden className="size-6 text-primary" />
              <span className="font-medium">Drop files here or choose them</span>
              <span className="text-xs text-muted">PDF, PNG, JPEG, TIFF or WebP, up to 25 MB each</span>
              <input
                ref={fileInput}
                id={inputId}
                type="file"
                multiple
                accept={ACCEPT}
                className="sr-only"
                onChange={(e) => {
                  add(e.target.files)
                  e.target.value = ''
                }}
              />
            </label>

            {items.length > 0 && (
              <ul aria-label="Files" aria-live="polite" className="flex flex-col divide-y divide-border rounded-md border border-border">
                {items.map((it, i) => (
                  <li key={`${it.file.name}-${i}`} className="flex items-center gap-3 px-3 py-2">
                    {it.state === 'sent' ? (
                      <CircleCheck aria-hidden className="size-4 shrink-0 text-approved" />
                    ) : it.state === 'failed' ? (
                      <TriangleAlert aria-hidden className="size-4 shrink-0 text-danger" />
                    ) : it.state === 'sending' ? (
                      <Loader aria-hidden className="size-4 shrink-0 animate-spin text-primary motion-reduce:animate-none" />
                    ) : (
                      <FileUp aria-hidden className="size-4 shrink-0 text-muted" />
                    )}
                    <div className="flex min-w-0 flex-1 flex-col">
                      <span className="truncate">{it.file.name}</span>
                      <span className={cn('text-xs', it.state === 'failed' ? 'text-danger-fg' : 'text-muted')}>
                        {it.state === 'failed'
                          ? `Not uploaded: ${it.error}`
                          : it.state === 'sent'
                            ? 'Uploaded, reading now'
                            : it.state === 'sending'
                              ? 'Uploading…'
                              : `${(it.file.size / 1024 / 1024).toFixed(1)} MB`}
                      </span>
                    </div>
                    {it.state === 'waiting' && (
                      <button
                        type="button"
                        aria-label={`Remove ${it.file.name}`}
                        onClick={() => setItems((cur) => cur.filter((_, j) => j !== i))}
                        className="grid size-7 cursor-pointer place-items-center rounded-md text-muted hover:bg-surface-raised"
                      >
                        <X aria-hidden className="size-3.5" />
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <footer className="flex flex-wrap items-center justify-end gap-2 border-t border-border px-5 py-3">
            {done && items.some((i) => i.state === 'sent') && (
              <Button
                variant="ghost"
                onClick={() => {
                  close(false)
                  const sent = items.filter((i) => i.state === 'sent')
                  navigate(sent.length === 1 ? `/d/${sent[0].id}` : '/documents')
                }}
              >
                {items.filter((i) => i.state === 'sent').length === 1 ? 'Open document' : 'View documents'}
              </Button>
            )}
            <Dialog.Close render={<Button disabled={busy}>{done ? 'Done' : 'Cancel'}</Button>} />
            <Button variant="primary" icon={Upload} onClick={send} disabled={!pending || busy}>
              {busy ? 'Uploading…' : pending ? `Upload ${pending === 1 ? '1 file' : `${pending} files`}` : 'Upload'}
            </Button>
          </footer>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
