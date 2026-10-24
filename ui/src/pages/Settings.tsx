import { useQuery } from '@tanstack/react-query'
import { CircleCheck, ExternalLink, Monitor, Moon, Sun, TriangleAlert } from 'lucide-react'
import type { ReactNode } from 'react'
import { api } from '../api'
import { Page } from '../components/AppShell'
import { ShortcutsList } from '../components/ShortcutsDialog'
import { Badge, Card, CardHeader, ErrorNote, PageHeader, Skeleton } from '../components/ui'
import { cn, setTheme, useTheme, type Theme } from '../lib'

function Row({ label, children, hint }: { label: string; children: ReactNode; hint?: ReactNode }) {
  return (
    <div className="grid gap-1 px-4 py-3 sm:grid-cols-[14rem_1fr] sm:gap-4">
      <dt className="text-muted">{label}</dt>
      <dd className="flex min-w-0 flex-col gap-1">
        <span className="min-w-0 break-words">{children}</span>
        {hint && <span className="text-xs text-pretty text-muted">{hint}</span>}
      </dd>
    </div>
  )
}

const THEMES: { value: Theme; label: string; icon: typeof Sun }[] = [
  { value: 'system', label: 'System', icon: Monitor },
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
]

export function Settings() {
  const settings = useQuery({ queryKey: ['settings'], queryFn: api.settings })
  const theme = useTheme()
  const s = settings.data

  return (
    <Page className="max-w-5xl">
      <PageHeader
        title="Settings"
        description="How this instance runs. The model and paths are set with environment variables when the server starts, so they are shown here, not edited."
      />
      <div className="flex flex-col gap-4">
        <Card aria-labelledby="appearance-h">
          <CardHeader id="appearance-h" title="Appearance" hint="Saved in this browser only" />
          <div className="px-4 py-4">
            <div role="group" aria-label="Theme" className="grid max-w-md grid-cols-3 gap-2">
              {THEMES.map((t) => {
                const on = theme === t.value
                return (
                  <button
                    key={t.value}
                    type="button"
                    aria-pressed={on}
                    onClick={() => setTheme(t.value)}
                    className={cn(
                      'flex h-16 cursor-pointer flex-col items-center justify-center gap-1 rounded-md border transition-colors duration-150',
                      on ? 'border-primary bg-primary-tint text-primary' : 'border-border text-muted hover:border-border-strong hover:text-foreground',
                    )}
                  >
                    <t.icon aria-hidden className="size-4" />
                    {t.label}
                  </button>
                )
              })}
            </div>
          </div>
        </Card>

        {settings.isError ? (
          <ErrorNote>Could not load the settings: {settings.error.message}</ErrorNote>
        ) : !s ? (
          <Skeleton className="h-80" />
        ) : (
          <>
            <Card aria-labelledby="model-h">
              <CardHeader id="model-h" title="Model provider" />
              <dl className="divide-y divide-border">
                <Row label="Provider" hint="CITEFIELD_PROVIDER: anthropic, openai, ollama or claude-code">
                  <span className="font-mono">{s.provider}</span>
                </Row>
                <Row label="Model" hint="CITEFIELD_MODEL; empty means the provider's default">
                  <span className="font-mono">{s.model ?? 'default'}</span>
                </Row>
                {s.base_url && (
                  <Row label="Base URL" hint="CITEFIELD_BASE_URL">
                    <span className="font-mono">{s.base_url}</span>
                  </Row>
                )}
                {s.api_key_env && (
                  <Row label="API key" hint={`Read from ${s.api_key_env}. The key itself never leaves the server.`}>
                    {s.api_key_set ? (
                      <Badge tone="approved">
                        <CircleCheck aria-hidden className="size-3" /> Set
                      </Badge>
                    ) : (
                      <Badge tone="danger">
                        <TriangleAlert aria-hidden className="size-3" /> Not set, documents will fail to read
                      </Badge>
                    )}
                  </Row>
                )}
                <Row label="Background worker">
                  {s.worker ? (
                    <Badge tone="approved">
                      <CircleCheck aria-hidden className="size-3" /> Running
                    </Badge>
                  ) : (
                    <Badge tone="review">
                      <TriangleAlert aria-hidden className="size-3" /> Stopped: uploads wait in the queue
                    </Badge>
                  )}
                </Row>
              </dl>
              <div className="border-t border-border px-4 py-3">
                <p className="pb-2 text-xs text-muted">To change the model, restart the server with, for example:</p>
                <pre className="overflow-x-auto rounded-md bg-surface-raised px-3 py-2 font-mono text-xs">
                  CITEFIELD_MODEL=claude-haiku-5-5 citefield serve
                </pre>
              </div>
            </Card>

            <Card aria-labelledby="instance-h">
              <CardHeader id="instance-h" title="Instance" />
              <dl className="divide-y divide-border">
                <Row label="Version">
                  <span className="font-mono">{s.version}</span>
                </Row>
                <Row label="Data directory" hint="Uploads, the database and the page cache. Set with CITEFIELD_DATA or --data.">
                  <span className="font-mono">{s.data_dir}</span>
                </Row>
                <Row label="Custom schemas" hint="JSON files here appear under Schemas and in the upload dialog.">
                  <span className="font-mono">{s.schemas_dir}</span>
                </Row>
                <Row label="Uploads">
                  {s.accepted_types.join(', ')}, up to {s.max_upload_mb} MB each
                </Row>
                <Row label="Access" hint="v1 has no login. Keep it on 127.0.0.1, or put an authenticating proxy in front.">
                  Single user
                </Row>
              </dl>
            </Card>
          </>
        )}

        <Card aria-labelledby="keys-h">
          <CardHeader id="keys-h" title="Keyboard shortcuts" hint="On a document's review screen" />
          <div className="px-4 py-4">
            <ShortcutsList />
          </div>
        </Card>

        <Card aria-labelledby="about-h">
          <CardHeader id="about-h" title="About" />
          <div className="flex flex-col gap-2 px-4 py-4 text-pretty">
            <p>
              Citefield is open source under the AGPL-3.0. Accuracy figures, measured on open datasets, are in the README.
            </p>
            <a href="/docs" target="_blank" rel="noreferrer" className="inline-flex w-fit items-center gap-1 text-primary hover:underline">
              REST API reference (OpenAPI) <ExternalLink aria-hidden className="size-3.5" />
            </a>
          </div>
        </Card>
      </div>
    </Page>
  )
}
