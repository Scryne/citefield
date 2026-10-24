import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileUp } from 'lucide-react'
import { useId, useRef, useState } from 'react'
import { api } from '../api'
import { DocumentBadge } from '../components/StatusBadge'
import { cn, navigate } from '../lib'

const ACCEPT = 'application/pdf,image/png,image/jpeg,image/tiff,image/webp'

export function DocumentList() {
  const qc = useQueryClient()
  const inputId = useId()
  const fileInput = useRef<HTMLInputElement>(null)
  const [schema, setSchema] = useState('invoice')
  const [dragging, setDragging] = useState(false)
  const schemas = useQuery({ queryKey: ['schemas'], queryFn: api.schemas })
  const docs = useQuery({
    queryKey: ['documents'],
    queryFn: api.documents,
    // poll only while something is still being read
    refetchInterval: (q) => (q.state.data?.some((d) => d.status === 'queued' || d.status === 'processing') ? 1500 : false),
  })
  const upload = useMutation({
    mutationFn: (files: File[]) => Promise.all(files.map((f) => api.upload(f, schema))),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['documents'] }),
  })

  const send = (list: FileList | null) => {
    if (list && list.length) upload.mutate([...list])
  }

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-8">
      <section
        aria-labelledby="upload-heading"
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          send(e.dataTransfer.files)
        }}
        className={cn(
          'flex flex-col gap-4 rounded-lg border border-dashed border-border bg-surface/60 p-6 sm:flex-row sm:items-center',
          dragging && 'border-primary bg-primary-fill',
        )}
      >
        <FileUp aria-hidden className="size-8 shrink-0 text-primary" />
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <h2 id="upload-heading" className="text-lg font-semibold text-balance">
            Add documents
          </h2>
          <p className="text-pretty text-muted">
            Drop PDFs or photos here. Each value comes back with the words it was read from; anything uncertain waits for
            you in the review queue.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label htmlFor={`${inputId}-schema`} className="text-xs font-medium text-muted">
            Schema
          </label>
          <select
            id={`${inputId}-schema`}
            value={schema}
            onChange={(e) => setSchema(e.target.value)}
            className="h-9 rounded-md border border-border bg-surface-raised px-2 text-foreground"
          >
            {(schemas.data ?? [{ name: 'invoice' }, { name: 'receipt' }]).map((s) => (
              <option key={s.name} value={s.name}>
                {s.name}
              </option>
            ))}
          </select>
          <input
            ref={fileInput}
            id={inputId}
            type="file"
            multiple
            accept={ACCEPT}
            className="sr-only"
            onChange={(e) => {
              send(e.target.files)
              e.target.value = ''
            }}
          />
          <button
            type="button"
            onClick={() => fileInput.current?.click()}
            disabled={upload.isPending}
            className="h-9 cursor-pointer rounded-md bg-primary px-3 font-medium text-background disabled:opacity-60"
          >
            {upload.isPending ? 'Uploading…' : 'Choose files'}
          </button>
        </div>
      </section>
      {upload.isError && (
        <p role="alert" className="-mt-4 text-danger">
          Upload failed: {upload.error.message}
        </p>
      )}

      <section aria-labelledby="docs-heading" className="flex flex-col gap-2">
        <h2 id="docs-heading" className="text-xs font-medium text-muted">
          Documents
        </h2>
        {docs.isPending ? (
          <ul aria-hidden className="flex flex-col gap-2">
            {[0, 1, 2].map((i) => (
              <li key={i} className="h-14 rounded-md bg-surface" />
            ))}
          </ul>
        ) : docs.isError ? (
          <p role="alert" className="text-danger">
            Could not load documents: {docs.error.message}. Is `citefield serve` running?
          </p>
        ) : docs.data.length === 0 ? (
          <p className="rounded-md bg-surface p-6 text-muted">
            No documents yet.{' '}
            <button type="button" onClick={() => fileInput.current?.click()} className="cursor-pointer text-primary underline">
              Add your first one
            </button>
            .
          </p>
        ) : (
          <ul className="flex flex-col gap-1">
            {docs.data.map((d) => (
              <li key={d.id}>
                <a
                  href={`/d/${d.id}`}
                  onClick={(e) => {
                    e.preventDefault()
                    navigate(`/d/${d.id}`)
                  }}
                  className="flex items-center gap-3 rounded-md bg-surface px-4 py-3 hover:bg-surface-raised"
                >
                  <span className="min-w-0 flex-1 truncate font-medium">{d.filename}</span>
                  <span className="hidden text-xs text-muted sm:inline">{d.schema_name}</span>
                  {d.status === 'ready' && (
                    <span className="text-xs tabular-nums text-muted">
                      {d.to_review ? (
                        <span className="text-review">{d.to_review} to review</span>
                      ) : (
                        `${d.fields} fields`
                      )}
                    </span>
                  )}
                  <DocumentBadge status={d.status} />
                </a>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  )
}
