import { clsx, type ClassValue } from 'clsx'
import { useSyncExternalStore } from 'react'
import { twMerge } from 'tailwind-merge'
import type { Field } from './api'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// A handful of flat routes and one query parameter, so the history API is less code than a router library.
function subscribe(cb: () => void) {
  window.addEventListener('popstate', cb)
  return () => window.removeEventListener('popstate', cb)
}

export function useLocation() {
  const href = useSyncExternalStore(subscribe, () => window.location.pathname + window.location.search)
  const url = new URL(href, window.location.origin)
  return { path: url.pathname, query: url.searchParams }
}

export function navigate(to: string, { replace = false } = {}) {
  if (replace) window.history.replaceState(null, '', to)
  else window.history.pushState(null, '', to)
  window.dispatchEvent(new PopStateEvent('popstate'))
}

/** Same-tab clicks go through the history API; modified clicks (new tab, download) keep the browser's behaviour. */
export function linkProps(to: string) {
  return {
    href: to,
    onClick: (e: React.MouseEvent) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return
      e.preventDefault()
      navigate(to)
    },
  }
}

/** The order the field panel shows and the keyboard walks: fields that need a person, then the document's own
 *  fields, then line items by item number. */
export function orderFields(fields: Field[]) {
  const rest = fields.filter((f) => f.status !== 'review')
  return [
    ...fields.filter((f) => f.status === 'review'),
    ...rest.filter((f) => f.item === null),
    ...rest.filter((f) => f.item !== null).sort((a, b) => a.item! - b.item!),
  ]
}

export type Theme = 'system' | 'light' | 'dark'
const THEME_KEY = 'citefield-theme'
const themeListeners = new Set<() => void>()

function readTheme(): Theme {
  try {
    const t = localStorage.getItem(THEME_KEY)
    return t === 'light' || t === 'dark' ? t : 'system'
  } catch {
    return 'system'
  }
}

export function applyTheme(theme = readTheme()) {
  const dark = theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)
  document.documentElement.dataset.theme = dark ? 'dark' : 'light'
}

export function setTheme(theme: Theme) {
  try {
    if (theme === 'system') localStorage.removeItem(THEME_KEY)
    else localStorage.setItem(THEME_KEY, theme)
  } catch {
    /* private window: the choice lasts for this page only */
  }
  applyTheme(theme)
  themeListeners.forEach((l) => l())
}

export function useTheme(): Theme {
  return useSyncExternalStore(
    (cb) => {
      themeListeners.add(cb)
      return () => themeListeners.delete(cb)
    },
    readTheme,
  )
}
