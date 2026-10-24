// Display text for values the API returns as keys.
import type { DocumentSummary, FieldKind, FieldStatus, Rule, Trigger } from './api'

const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ['year', 365 * 24 * 3600],
  ['month', 30 * 24 * 3600],
  ['day', 24 * 3600],
  ['hour', 3600],
  ['minute', 60],
]
const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })

export function relativeTime(iso: string, now = Date.now()) {
  const seconds = (new Date(iso).getTime() - now) / 1000
  for (const [unit, size] of UNITS) if (Math.abs(seconds) >= size) return rtf.format(Math.round(seconds / size), unit)
  return 'just now'
}

export function dateTime(iso: string) {
  return new Date(iso).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' })
}

export function percent(x: number | null | undefined, digits = 0) {
  return x == null ? '–' : `${(x * 100).toFixed(digits)}%`
}

/** "seller.tax_id" -> "Seller tax id", "SUB_TOTAL" -> "Sub total"; the raw key stays visible next to it in monospace. */
export function fieldLabel(name: string) {
  const words = name.replace(/[._]/g, ' ').trim().toLowerCase()
  return words.charAt(0).toUpperCase() + words.slice(1)
}

export const TRIGGER_LABEL: Record<Trigger, string> = {
  second_read: 'Second read disagrees',
  rule: 'Arithmetic or check digit fails',
  citation: 'Citation incomplete',
  confidence: 'Model unsure',
  collision: 'One value, two roles',
}

export const FIELD_STATUS_LABEL: Record<FieldStatus, string> = {
  review: 'Needs review',
  auto: 'Auto-approved',
  approved: 'Approved',
  corrected: 'Corrected',
}

export const DOCUMENT_STATUS_LABEL: Record<DocumentSummary['status'], string> = {
  queued: 'Queued',
  processing: 'Reading',
  ready: 'Ready',
  failed: 'Failed',
}

export const KIND_LABEL: Record<FieldKind, string> = {
  text: 'Text',
  amount: 'Amount',
  count: 'Count',
  date: 'Date',
  id: 'Identifier',
}

export function plural(n: number, one: string, many = `${one}s`) {
  return `${n.toLocaleString('en')} ${n === 1 ? one : many}`
}

/** A rule as a sentence: what has to add up to what. */
export function ruleText(r: Rule) {
  if (r.type === 'sum')
    return `${r.of} adds up to ${r.equals}${r.fallback ? ` (or to ${r.fallback} when ${r.equals} is not printed)` : ''}`
  if (r.type === 'add')
    return `${(r.terms ?? []).join(' + ')}${(r.minus ?? []).map((m) => ` − ${m}`).join('')} = ${r.equals}`
  return `${(r.factors ?? []).join(' × ')} = ${r.equals}, per line item`
}
