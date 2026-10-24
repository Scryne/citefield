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
  created_at: string
}

export interface PageInfo {
  index: number
  width: number
  height: number
  source: 'pdf' | 'ocr'
}

export interface DocumentDetail extends DocumentSummary {
  model: string | null
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

export interface SchemaInfo {
  name: string
  description: string
  fields: string[]
}

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
  exportUrl: (id: string, format: 'json' | 'csv' | 'xlsx') => `/api/documents/${id}/export?format=${format}`,
}
