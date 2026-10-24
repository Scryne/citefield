import { Tabs } from '@base-ui/react/tabs'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDown, ArrowUp, Copy, Lock, Pencil, Plus, Save, Trash2, X } from 'lucide-react'
import { useState } from 'react'
import { api, type CheckDigit, type FieldKind, type FieldSpec, type Rule, type SchemaInfo } from '../api'
import { Page } from '../components/AppShell'
import { ConfirmDelete } from '../components/ConfirmDelete'
import { Badge, Button, Card, CardHeader, ErrorNote, IconButton, PageHeader, Select, Skeleton } from '../components/ui'
import { inputClass } from '../components/styles'
import { KIND_LABEL, ruleText } from '../format'
import { cn, linkProps, navigate } from '../lib'

const KINDS: FieldKind[] = ['text', 'amount', 'count', 'date', 'id']
const CHECKS: CheckDigit[] = ['iban', 'luhn', 'tckn', 'vkn']
const NAME = /^[A-Za-z0-9_-]{1,64}$/

const BLANK: Omit<SchemaInfo, 'name' | 'bundled'> = {
  description: '',
  fields: [{ name: '', kind: 'text' }],
  rules: [],
}

function Breadcrumb({ name }: { name: string }) {
  return (
    <a {...linkProps('/schemas')} className="w-fit text-xs text-muted hover:text-foreground hover:underline">
      Schemas{name ? ` / ${name}` : ''}
    </a>
  )
}

/** /schemas/new, /schemas/:name, /schemas/:name?edit, and duplicating a bundled schema (/schemas/new?from=). */
export function SchemaDetail({ name, edit, from }: { name: string | null; edit: boolean; from: string | null }) {
  const source = name ?? from
  const schema = useQuery({ queryKey: ['schema', source], queryFn: () => api.schema(source!), enabled: !!source })
  if (source && schema.isError)
    return (
      <Page>
        <PageHeader breadcrumb={<Breadcrumb name="" />} title="Schema not found" />
        <ErrorNote>
          There is no schema called {source}.{' '}
          <a {...linkProps('/schemas')} className="underline">
            See all schemas
          </a>
        </ErrorNote>
      </Page>
    )
  if (source && schema.isPending)
    return (
      <Page>
        <Skeleton className="h-96" />
      </Page>
    )
  const s = schema.data
  if (!name || edit)
    return (
      <Editor
        key={`${name}-${from}`}
        existing={name}
        initial={s ? { description: s.description, fields: s.fields, rules: s.rules } : BLANK}
        suggestedName={from ? `${from}-custom` : ''}
      />
    )
  return <View s={s!} />
}

function View({ s }: { s: SchemaInfo }) {
  const qc = useQueryClient()
  const [confirm, setConfirm] = useState(false)
  const remove = useMutation({
    mutationFn: () => api.removeSchema(s.name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['schemas'] })
      navigate('/schemas')
    },
  })
  return (
    <Page>
      <PageHeader
        breadcrumb={<Breadcrumb name="" />}
        title={<span className="font-mono">{s.name}</span>}
        description={s.description && s.description !== s.name ? s.description : undefined}
        actions={
          s.bundled ? (
            <>
              <Badge>
                <Lock aria-hidden className="size-3" /> Bundled, read-only
              </Badge>
              <Button icon={Copy} onClick={() => navigate(`/schemas/new?from=${s.name}`)}>
                Duplicate as custom
              </Button>
            </>
          ) : (
            <>
              <Button icon={Trash2} onClick={() => setConfirm(true)}>
                Delete
              </Button>
              <Button variant="primary" icon={Pencil} onClick={() => navigate(`/schemas/${s.name}?edit`)}>
                Edit schema
              </Button>
            </>
          )
        }
      />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
        <Card aria-labelledby="fields-h" className="overflow-hidden xl:col-span-8">
          <CardHeader id="fields-h" title="Fields" hint={`${s.fields.length}`} />
          <div className="relative overflow-x-auto">
            <table className="w-full min-w-[560px] text-left">
              <thead className="bg-surface-raised text-xs text-muted">
                <tr className="h-9">
                  <th className="pl-4 font-medium">Name</th>
                  <th className="font-medium">Kind</th>
                  <th className="font-medium">Line items</th>
                  <th className="font-medium">Check</th>
                  <th className="pr-4 font-medium">What the model looks for</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {s.fields.map((f) => (
                  <tr key={f.name} className="h-11">
                    <td className="pl-4 font-mono text-[13px]">{f.name}</td>
                    <td>{KIND_LABEL[f.kind]}</td>
                    <td className="text-muted">
                      {f.group ? (
                        <span className="flex items-center gap-1.5">
                          <span className="font-mono text-[13px]">{f.group}</span>
                          {f.anchor && <Badge tone="primary">anchor</Badge>}
                        </span>
                      ) : (
                        '–'
                      )}
                    </td>
                    <td className="font-mono text-[13px] uppercase text-muted">{f.check ?? '–'}</td>
                    <td className="pr-4 text-pretty text-muted">{f.description || '–'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
        <div className="flex flex-col gap-4 xl:col-span-4">
          <Card aria-labelledby="rules-h">
            <CardHeader id="rules-h" title="Arithmetic rules" hint={`${s.rules.length}`} />
            {s.rules.length ? (
              <ul className="divide-y divide-border">
                {s.rules.map((r, i) => (
                  <li key={i} className="flex flex-col gap-0.5 px-4 py-3">
                    <span className="text-xs font-medium text-muted uppercase">{r.type}</span>
                    <span className="font-mono text-[13px] text-pretty">{ruleText(r)}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="p-4 text-pretty text-muted">No rules. Values are still checked by the second read and citations.</p>
            )}
          </Card>
          <Card aria-labelledby="json-h">
            <CardHeader id="json-h" title="As JSON" hint="what the file on disk holds" />
            <pre className="max-h-80 overflow-auto p-4 font-mono text-xs leading-relaxed">
              {JSON.stringify({ name: s.name, description: s.description, fields: s.fields, rules: s.rules }, null, 2)}
            </pre>
          </Card>
        </div>
      </div>
      <ConfirmDelete
        open={confirm}
        onOpenChange={setConfirm}
        title={`Delete the ${s.name} schema?`}
        confirm="Delete schema"
        onConfirm={() => remove.mutate()}
        busy={remove.isPending}
        error={remove.isError ? `Could not delete: ${remove.error.message}` : null}
      >
        The schema file is removed. Documents already read with it keep their values; new uploads cannot choose it. This
        cannot be undone.
      </ConfirmDelete>
    </Page>
  )
}

type Draft = Omit<SchemaInfo, 'name' | 'bundled'>

function Editor({ existing, initial, suggestedName }: { existing: string | null; initial: Draft; suggestedName: string }) {
  const qc = useQueryClient()
  const [name, setName] = useState(existing ?? suggestedName)
  const [draft, setDraft] = useState<Draft>(initial)
  const [view, setView] = useState<'form' | 'json'>('form')
  const [json, setJson] = useState('')
  const [jsonError, setJsonError] = useState<string | null>(null)
  const [tried, setTried] = useState(false)
  const save = useMutation({
    mutationFn: (body: Draft) => api.saveSchema(name, body),
    onSuccess: (s) => {
      qc.invalidateQueries({ queryKey: ['schemas'] })
      qc.setQueryData(['schema', s.name], s)
      navigate(`/schemas/${s.name}`)
    },
  })

  const names = draft.fields.map((f) => f.name).filter(Boolean)
  const groups = [...new Set(draft.fields.map((f) => f.group).filter((g): g is string => !!g))]
  const nameError = name && !NAME.test(name) ? 'Use letters, digits, _ and - (up to 64).' : null
  const dupes = names.filter((n, i) => names.indexOf(n) !== i)
  const anchorless = groups.filter((g) => draft.fields.filter((f) => f.group === g && f.anchor).length !== 1)
  const formProblems = [
    !names.length && 'Add at least one field with a name.',
    dupes.length > 0 && `Field names must be unique: ${[...new Set(dupes)].join(', ')}.`,
    anchorless.length > 0 && `Each line-item group needs exactly one anchor field: ${anchorless.join(', ')}.`,
  ]
  // in the JSON view the form state is stale, so only the name is checked here; the server validates the rest
  const problems = [!name && 'Give the schema a name.', nameError, ...(view === 'json' ? [] : formProblems)].filter(
    Boolean,
  ) as string[]

  const setField = (i: number, patch: Partial<FieldSpec>) =>
    setDraft((d) => ({ ...d, fields: d.fields.map((f, j) => (j === i ? clean({ ...f, ...patch }) : f)) }))
  const move = (i: number, by: number) =>
    setDraft((d) => {
      const fields = [...d.fields]
      const [f] = fields.splice(i, 1)
      fields.splice(i + by, 0, f)
      return { ...d, fields }
    })
  const setRule = (i: number, r: Rule) => setDraft((d) => ({ ...d, rules: d.rules.map((x, j) => (j === i ? r : x)) }))

  const body = (): Draft => ({ ...draft, fields: draft.fields.filter((f) => f.name.trim()) })
  const switchView = (v: 'form' | 'json') => {
    if (v === 'json') setJson(JSON.stringify(body(), null, 2))
    else {
      try {
        const parsed = JSON.parse(json)
        setDraft({ description: parsed.description ?? '', fields: parsed.fields ?? [], rules: parsed.rules ?? [] })
        setJsonError(null)
      } catch (e) {
        setJsonError(`The JSON does not parse: ${(e as Error).message}`)
        return
      }
    }
    setView(v)
  }

  return (
    <Page>
      <PageHeader
        breadcrumb={<Breadcrumb name={existing ?? ''} />}
        title={existing ? `Edit ${existing}` : 'New schema'}
        description="Fields are what the model looks for; rules are arithmetic the values must satisfy. Saved as a JSON file in the schemas folder."
        actions={
          <>
            <a {...linkProps(existing ? `/schemas/${existing}` : '/schemas')} className="text-muted hover:text-foreground hover:underline">
              Cancel
            </a>
            <Button
              variant="primary"
              icon={Save}
              disabled={save.isPending || (view === 'json' && !!jsonError)}
              onClick={() => {
                // the problems list appears once the reviewer tries to save, not while they are still typing
                if (problems.length) setTried(true)
                else if (view === 'json') {
                  try {
                    save.mutate(JSON.parse(json))
                  } catch (e) {
                    setJsonError(`The JSON does not parse: ${(e as Error).message}`)
                  }
                } else save.mutate(body())
              }}
            >
              {save.isPending ? 'Saving…' : 'Save schema'}
            </Button>
          </>
        }
      />

      <div className="flex flex-col gap-4">
        {save.isError && <ErrorNote>The server did not accept the schema: {save.error.message}</ErrorNote>}
        {tried && problems.length > 0 && (
          <ul aria-live="polite" className="flex flex-col gap-1 rounded-md border border-review/30 bg-review-fill px-3 py-2 text-review-fg">
            {problems.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        )}

        <Card className="grid gap-4 p-4 md:grid-cols-[16rem_1fr]">
          <label className="flex flex-col gap-1">
            <span className="text-xs font-medium text-muted">Name</span>
            <input
              value={name}
              disabled={!!existing}
              onChange={(e) => setName(e.target.value)}
              aria-invalid={!!nameError}
              aria-describedby="name-help"
              className={cn(inputClass, 'font-mono disabled:bg-surface-raised disabled:text-muted')}
              placeholder="utility-bill"
            />
            <span id="name-help" className={cn('text-xs', nameError ? 'text-danger-fg' : 'text-muted')}>
              {existing ? 'The name is the file name and cannot change.' : (nameError ?? 'Chosen when uploading.')}
            </span>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs font-medium text-muted">Description</span>
            <input
              value={draft.description}
              onChange={(e) => setDraft((d) => ({ ...d, description: e.target.value }))}
              className={inputClass}
              placeholder="What kind of document this is, for the model: electricity bill"
            />
          </label>
        </Card>

        <Tabs.Root value={view} onValueChange={(v) => switchView(v as 'form' | 'json')}>
          <Tabs.List className="mb-4 flex w-fit gap-1 rounded-md border border-border bg-surface p-1">
            {(['form', 'json'] as const).map((v) => (
              <Tabs.Tab
                key={v}
                value={v}
                className="h-7 cursor-pointer rounded-sm px-3 text-muted data-[active]:bg-foreground data-[active]:text-background"
              >
                {v === 'form' ? 'Editor' : 'JSON'}
              </Tabs.Tab>
            ))}
          </Tabs.List>

          <Tabs.Panel value="form" className="flex flex-col gap-4 outline-none">
            <Card aria-labelledby="ef-h" className="overflow-hidden">
              <CardHeader
                id="ef-h"
                title="Fields"
                hint="Line-item fields share a group; one of them, the anchor (usually the name), starts each item."
              />
              <div className="relative overflow-x-auto">
                <table className="w-full min-w-[880px] text-left">
                  <thead className="bg-surface-raised text-xs text-muted">
                    <tr className="h-9">
                      <th className="w-16 pl-3 font-medium">
                        <span className="sr-only">Order</span>
                      </th>
                      <th className="font-medium">Name</th>
                      <th className="w-32 font-medium">Kind</th>
                      <th className="w-32 font-medium">Group</th>
                      <th className="w-16 font-medium">Anchor</th>
                      <th className="w-28 font-medium">Check</th>
                      <th className="font-medium">Description for the model</th>
                      <th className="w-12" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {draft.fields.map((f, i) => (
                      <tr key={i} className="h-12 align-middle">
                        <td className="pl-2">
                          <span className="flex">
                            <IconButton label="Move up" icon={ArrowUp} className="size-7" disabled={i === 0} onClick={() => move(i, -1)} />
                            <IconButton
                              label="Move down"
                              icon={ArrowDown}
                              className="size-7"
                              disabled={i === draft.fields.length - 1}
                              onClick={() => move(i, 1)}
                            />
                          </span>
                        </td>
                        <td className="pr-2">
                          <input
                            aria-label={`Field ${i + 1} name`}
                            value={f.name}
                            onChange={(e) => setField(i, { name: e.target.value.trim() })}
                            placeholder={i === 0 ? 'invoice.number' : ''}
                            className={cn(inputClass, 'h-8 font-mono text-[13px]', dupes.includes(f.name) && 'border-danger')}
                          />
                        </td>
                        <td className="pr-2">
                          <Select label={`Field ${i + 1} kind`} hideLabel value={f.kind} onChange={(e) => setField(i, { kind: e.target.value as FieldKind })}>
                            {KINDS.map((k) => (
                              <option key={k} value={k}>
                                {KIND_LABEL[k]}
                              </option>
                            ))}
                          </Select>
                        </td>
                        <td className="pr-2">
                          <input
                            aria-label={`Field ${i + 1} line-item group`}
                            value={f.group ?? ''}
                            onChange={(e) => setField(i, { group: e.target.value.trim() || undefined, anchor: e.target.value.trim() ? f.anchor : undefined })}
                            placeholder="none"
                            className={cn(inputClass, 'h-8 font-mono text-[13px]')}
                          />
                        </td>
                        <td>
                          <input
                            type="checkbox"
                            aria-label={`Field ${i + 1} is the anchor of its group`}
                            checked={!!f.anchor}
                            disabled={!f.group}
                            onChange={(e) => setField(i, { anchor: e.target.checked || undefined })}
                            className="ml-3 size-4 cursor-pointer accent-primary disabled:cursor-not-allowed disabled:opacity-40"
                          />
                        </td>
                        <td className="pr-2">
                          <Select
                            label={`Field ${i + 1} check digit`}
                            hideLabel
                            value={f.check ?? ''}
                            onChange={(e) => setField(i, { check: (e.target.value || undefined) as CheckDigit | undefined })}
                          >
                            <option value="">None</option>
                            {CHECKS.map((c) => (
                              <option key={c} value={c}>
                                {c.toUpperCase()}
                              </option>
                            ))}
                          </Select>
                        </td>
                        <td className="pr-2">
                          <input
                            aria-label={`Field ${i + 1} description`}
                            value={f.description ?? ''}
                            onChange={(e) => setField(i, { description: e.target.value || undefined })}
                            placeholder="e.g. amount due, only if printed"
                            className={cn(inputClass, 'h-8')}
                          />
                        </td>
                        <td className="pr-2">
                          <IconButton
                            label={`Remove ${f.name || `field ${i + 1}`}`}
                            icon={X}
                            disabled={draft.fields.length === 1}
                            onClick={() => setDraft((d) => ({ ...d, fields: d.fields.filter((_, j) => j !== i) }))}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="border-t border-border p-3">
                <Button
                  size="sm"
                  icon={Plus}
                  onClick={() => setDraft((d) => ({ ...d, fields: [...d.fields, { name: '', kind: 'text' }] }))}
                >
                  Add field
                </Button>
              </div>
            </Card>

            <Card aria-labelledby="er-h">
              <CardHeader id="er-h" title="Arithmetic rules" hint="A failing rule sends its values to review." />
              <ul className="divide-y divide-border">
                {draft.rules.map((r, i) => (
                  <RuleEditor
                    key={i}
                    rule={r}
                    names={names}
                    groups={groups}
                    onChange={(x) => setRule(i, x)}
                    onRemove={() => setDraft((d) => ({ ...d, rules: d.rules.filter((_, j) => j !== i) }))}
                  />
                ))}
              </ul>
              {!draft.rules.length && <p className="px-4 pt-4 text-muted">No rules yet.</p>}
              <div className="flex flex-wrap gap-2 p-3">
                {(
                  [
                    ['sum', 'Line items add up'],
                    ['add', 'Terms add up to a total'],
                    ['product', 'Quantity × price'],
                  ] as const
                ).map(([type, label]) => (
                  <Button
                    key={type}
                    size="sm"
                    icon={Plus}
                    disabled={!names.length}
                    onClick={() =>
                      setDraft((d) => ({
                        ...d,
                        rules: [...d.rules, type === 'sum' ? { type, of: '', equals: '' } : type === 'add' ? { type, terms: [], equals: '' } : { type, factors: [], equals: '' }],
                      }))
                    }
                  >
                    {label}
                  </Button>
                ))}
              </div>
            </Card>
          </Tabs.Panel>

          <Tabs.Panel value="json" className="flex flex-col gap-2 outline-none">
            <label className="flex flex-col gap-1">
              <span className="text-xs font-medium text-muted">Schema JSON (name comes from the name field above)</span>
              <textarea
                value={json}
                onChange={(e) => {
                  setJson(e.target.value)
                  setJsonError(null)
                }}
                spellCheck={false}
                rows={24}
                className="rounded-lg border border-border-strong bg-surface p-4 font-mono text-xs leading-relaxed"
              />
            </label>
            {jsonError && <ErrorNote>{jsonError}</ErrorNote>}
          </Tabs.Panel>
        </Tabs.Root>
      </div>
    </Page>
  )
}

/** Drop empty optional keys so the saved JSON stays what a person would write. */
function clean(f: FieldSpec): FieldSpec {
  return Object.fromEntries(Object.entries(f).filter(([k, v]) => k === 'name' || k === 'kind' || (v !== undefined && v !== '' && v !== false))) as unknown as FieldSpec
}

function MultiPick({ label, value, options, onChange }: { label: string; value: string[]; options: string[]; onChange: (v: string[]) => void }) {
  return (
    <fieldset className="flex flex-col gap-1">
      <legend className="pb-1 text-xs font-medium text-muted">{label}</legend>
      <div className="flex flex-wrap gap-1">
        {options.map((o) => {
          const on = value.includes(o)
          return (
            <button
              key={o}
              type="button"
              aria-pressed={on}
              onClick={() => onChange(on ? value.filter((v) => v !== o) : [...value, o])}
              className={cn(
                'h-7 cursor-pointer rounded-sm border px-2 font-mono text-xs',
                on ? 'border-primary bg-primary-tint text-primary' : 'border-border text-muted hover:border-border-strong',
              )}
            >
              {o}
            </button>
          )
        })}
      </div>
    </fieldset>
  )
}

function RuleEditor({
  rule: r,
  names,
  groups,
  onChange,
  onRemove,
}: {
  rule: Rule
  names: string[]
  groups: string[]
  onChange: (r: Rule) => void
  onRemove: () => void
}) {
  const pick = (label: string, value: string | undefined, set: (v: string) => void, opts = names, optional = false) => (
    <Select label={label} value={value ?? ''} onChange={(e) => set(e.target.value)} className="min-w-44 flex-1">
      <option value="">{optional ? 'None' : 'Choose a field'}</option>
      {opts.map((n) => (
        <option key={n} value={n}>
          {n}
        </option>
      ))}
    </Select>
  )
  const grouped = names.filter((n) => groups.length && groups.some((g) => n.startsWith(`${g}.`) || n === g))
  return (
    <li className="flex flex-col gap-3 px-4 py-4">
      <div className="flex items-center gap-2">
        <Badge tone="primary" className="uppercase">
          {r.type}
        </Badge>
        <span className="min-w-0 flex-1 truncate font-mono text-xs text-muted">{r.equals ? ruleText(r) : 'Not complete yet'}</span>
        <IconButton label="Remove rule" icon={Trash2} onClick={onRemove} />
      </div>
      <div className="flex flex-wrap gap-3">
        {r.type === 'sum' && (
          <>
            {pick('Line-item field', r.of, (v) => onChange({ ...r, of: v }), grouped.length ? grouped : names)}
            {pick('Adds up to', r.equals, (v) => onChange({ ...r, equals: v }))}
            {pick('Otherwise to', r.fallback, (v) => onChange({ ...r, fallback: v || undefined }), names, true)}
          </>
        )}
        {r.type === 'add' && (
          <>
            <MultiPick label="Terms" value={r.terms ?? []} options={names} onChange={(v) => onChange({ ...r, terms: v })} />
            <MultiPick label="Minus" value={r.minus ?? []} options={names} onChange={(v) => onChange({ ...r, minus: v.length ? v : undefined })} />
            {pick('Equals', r.equals, (v) => onChange({ ...r, equals: v }))}
          </>
        )}
        {r.type === 'product' && (
          <>
            <MultiPick label="Factors (per item)" value={r.factors ?? []} options={names} onChange={(v) => onChange({ ...r, factors: v })} />
            {pick('Equals', r.equals, (v) => onChange({ ...r, equals: v }))}
          </>
        )}
      </div>
    </li>
  )
}
