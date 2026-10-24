import { useQuery } from '@tanstack/react-query'
import { Lock, Plus, Shapes } from 'lucide-react'
import { api } from '../api'
import { Page } from '../components/AppShell'
import { Badge, Card, EmptyState, ErrorNote, PageHeader, Skeleton } from '../components/ui'
import { buttonClass } from '../components/styles'
import { plural } from '../format'
import { linkProps } from '../lib'

export function Schemas() {
  const schemas = useQuery({ queryKey: ['schemas'], queryFn: api.schemas })
  const stats = useQuery({ queryKey: ['stats', 90], queryFn: () => api.stats(90) })

  return (
    <Page>
      <PageHeader
        title="Schemas"
        description="A schema names the fields to extract, their kinds, line-item groups, the arithmetic that must hold and check digits."
        actions={
          <a {...linkProps('/schemas/new')} className={buttonClass('primary')}>
            <Plus aria-hidden className="size-4" /> New schema
          </a>
        }
      />
      {schemas.isError ? (
        <ErrorNote>Could not load schemas: {schemas.error.message}</ErrorNote>
      ) : schemas.isPending ? (
        <div aria-busy className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-44" />
          ))}
        </div>
      ) : !schemas.data.length ? (
        <Card>
          <EmptyState icon={Shapes} title="No schemas" />
        </Card>
      ) : (
        <ul className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {schemas.data.map((s) => {
            const groups = [...new Set(s.fields.map((f) => f.group).filter(Boolean))]
            const used = stats.data?.schemas[s.name] ?? 0
            return (
              <li key={s.name}>
                <a
                  {...linkProps(`/schemas/${s.name}`)}
                  className="group flex h-full flex-col gap-3 rounded-lg border border-border bg-surface p-4 transition-colors duration-150 hover:border-border-strong"
                >
                  <div className="flex items-center gap-2">
                    <span className="min-w-0 flex-1 truncate font-mono font-medium group-hover:text-primary">{s.name}</span>
                    {s.bundled ? (
                      <Badge>
                        <Lock aria-hidden className="size-3" /> Bundled
                      </Badge>
                    ) : (
                      <Badge tone="primary">Custom</Badge>
                    )}
                  </div>
                  <p className="line-clamp-2 min-h-10 text-pretty text-muted">
                    {s.description && s.description !== s.name ? s.description : `Fields for ${s.name} documents.`}
                  </p>
                  <ul className="flex flex-wrap gap-1">
                    {s.fields.slice(0, 6).map((f) => (
                      <li key={f.name} className="rounded-sm bg-surface-raised px-1.5 py-0.5 font-mono text-xs text-muted">
                        {f.name}
                      </li>
                    ))}
                    {s.fields.length > 6 && <li className="px-1 py-0.5 text-xs text-muted">+{s.fields.length - 6} more</li>}
                  </ul>
                  <dl className="mt-auto grid grid-cols-3 gap-2 border-t border-border pt-3 text-xs">
                    <div>
                      <dt className="text-muted">Fields</dt>
                      <dd className="font-medium tabular-nums">{s.fields.length}</dd>
                    </div>
                    <div>
                      <dt className="text-muted">Rules</dt>
                      <dd className="font-medium tabular-nums">{s.rules.length}</dd>
                    </div>
                    <div>
                      <dt className="text-muted">Documents</dt>
                      <dd className="font-medium tabular-nums">{used}</dd>
                    </div>
                  </dl>
                  {groups.length > 0 && (
                    <p className="-mt-1 text-xs text-muted">Line items: {groups.map((g) => plural(s.fields.filter((f) => f.group === g).length, `${g} field`)).join(', ')}</p>
                  )}
                </a>
              </li>
            )
          })}
        </ul>
      )}
    </Page>
  )
}
