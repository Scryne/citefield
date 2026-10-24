// Typed client for the Citefield REST API (src/citefield/api.py).

export type FieldStatus = 'auto' | 'review' | 'approved' | 'corrected'
export type Box = [number, number, number, number]

export interface Field {
  id: number
  name: string
  value: string
  extracted_value: string
  item: number | null
  confidence: number | null
  citation: string
  evidence: number[]
  box: Box | null
  page: number | null // 0-based
  status: FieldStatus
  reasons: string[]
}

export interface DocumentSummary {
  id: string
  filename: string
  schema_name: string
  status: 'queued' | 'processing' | 'ready' | 'failed'
  error: string | null
  to_review: number
  fields: number
  counts: Record<FieldStatus, number>
  page_count: number
  model: string | null
  created_at: string
  updated_at: string
}

export interface PageInfo {
  index: number
  width: number
  height: number
  source: 'pdf' | 'ocr'
}

export interface DocumentDetail extends DocumentSummary {
  pages: PageInfo[]
  rules: { rule: string; outcome: 'holds' | 'fails' | 'skipped'; detail: string }[]
  possibly_missed: { field: string; value: string; item: number | null }[]
  field_list: Field[]
}

export interface Word {
  id: number
  text: string
  box: Box
  page: number
  line: number
}

export type FieldKind = 'text' | 'amount' | 'count' | 'date' | 'id'
export type CheckDigit = 'iban' | 'tckn' | 'vkn' | 'luhn'

export interface FieldSpec {
  name: string
  kind: FieldKind
  description?: string
  group?: string
  anchor?: boolean
  check?: CheckDigit
}

export interface Rule {
  type: 'sum' | 'add' | 'product'
  equals: string
  of?: string
  fallback?: string
  terms?: string[]
  minus?: string[]
  factors?: string[]
}

export interface SchemaInfo {
  name: string
  description: string
  bundled: boolean
  fields: FieldSpec[]
  rules: Rule[]
}

export type Trigger = 'second_read' | 'confidence' | 'rule' | 'citation' | 'collision'

export interface Stats {
  documents: Record<DocumentSummary['status'], number>
  fields: Record<FieldStatus, number>
  auto_share: number | null
  triggers: Partial<Record<Trigger, number>>
  per_day: { date: string; documents: number }[]
  seconds_per_document: number | null
  schemas: Record<string, number>
}

export interface Settings {
  version: string
  provider: string
  model: string | null
  base_url: string | null
  api_key_env: string | null
  api_key_set: boolean
  data_dir: string
  schemas_dir: string
  max_upload_mb: number
  accepted_types: string[]
  worker: boolean
  kinds: FieldKind[]
  checks: CheckDigit[]
}

export type ExportFormat = 'json' | 'csv' | 'xlsx'

export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, init)
  if (!r.ok) {
    let detail = r.statusText
    try {
      const body = await r.json()
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      /* not JSON */
    }
    throw new ApiError(detail)
  }
  return (r.status === 204 ? undefined : await r.json()) as T
}

export const api = {
  documents: () => request<DocumentSummary[]>('/api/documents'),
  document: (id: string) => request<DocumentDetail>(`/api/documents/${id}`),
  words: (id: string, page: number) => request<Word[]>(`/api/documents/${id}/words?page=${page + 1}`),
  schemas: () => request<SchemaInfo[]>('/api/schemas'),
  schema: (name: string) => request<SchemaInfo>(`/api/schemas/${encodeURIComponent(name)}`),
  saveSchema: (name: string, body: Omit<SchemaInfo, 'name' | 'bundled'>) =>
    request<SchemaInfo>(`/api/schemas/${encodeURIComponent(name)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  removeSchema: (name: string) => request<void>(`/api/schemas/${encodeURIComponent(name)}`, { method: 'DELETE' }),
  stats: (days = 14) => request<Stats>(`/api/stats?days=${days}`),
  settings: () => request<Settings>('/api/settings'),
  health: () => request<{ status: string; version: string; queued: number }>('/api/health'),
  retry: (id: string) => request<{ id: string }>(`/api/documents/${id}/retry`, { method: 'POST' }),
  upload: (file: File, schema: string) => {
    const body = new FormData()
    body.append('file', file)
    body.append('schema', schema)
    return request<{ id: string }>('/api/documents', { method: 'POST', body })
  },
  patchField: (id: string, fieldId: number, patch: { value?: string; word_ids?: number[]; approve?: boolean }) =>
    request<Field>(`/api/documents/${id}/fields/${fieldId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    }),
  remove: (id: string) => request<void>(`/api/documents/${id}`, { method: 'DELETE' }),
  pageUrl: (id: string, page: number) => `/api/documents/${id}/pages/${page + 1}.png`,
  exportUrl: (id: string, format: ExportFormat) => `/api/documents/${id}/export?format=${format}`,
  exportManyUrl: (ids: string[], format: ExportFormat) => `/api/export?ids=${ids.join(',')}&format=${format}`,
}
