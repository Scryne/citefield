import { clsx, type ClassValue } from 'clsx'
import { useSyncExternalStore } from 'react'
import { twMerge } from 'tailwind-merge'
import type { Field } from './api'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Two routes only (list and one document), so a router library would be more code than it saves.
function subscribe(cb: () => void) {
  window.addEventListener('popstate', cb)
  return () => window.removeEventListener('popstate', cb)
}

export function usePath() {
  return useSyncExternalStore(subscribe, () => window.location.pathname)
}

export function navigate(path: string) {
  window.history.pushState(null, '', path)
  window.dispatchEvent(new PopStateEvent('popstate'))
}

/** Fields that need a person first, then everything that passed; in the order the keyboard walks them. */
export function orderFields(fields: Field[]) {
  return [...fields.filter((f) => f.status === 'review'), ...fields.filter((f) => f.status !== 'review')]
}
