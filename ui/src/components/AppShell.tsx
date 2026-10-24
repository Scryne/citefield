import { Dialog } from '@base-ui/react/dialog'
import { useQuery } from '@tanstack/react-query'
import { CircleAlert, FileStack, FileText, LayoutDashboard, Menu, Settings, Shapes, X } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { api } from '../api'
import { cn, linkProps, useLocation } from '../lib'
import { useDocuments } from '../queries'

export function Logo({ className }: { className?: string }) {
  return (
    <svg aria-hidden viewBox="0 0 32 32" className={className}>
      <rect x="6" y="5" width="15" height="21" rx="2" fill="none" stroke="currentColor" strokeWidth="2" />
      <rect x="12" y="13.5" width="15" height="8" rx="1.5" fill="#2563EB" fillOpacity="0.35" stroke="#5B8DEF" strokeWidth="2" />
    </svg>
  )
}

interface Item {
  to: string
  label: string
  icon: typeof FileText
  match: (path: string, query: URLSearchParams) => boolean
  count?: number
}

function Nav({ onNavigate }: { onNavigate?: () => void }) {
  const { path, query } = useLocation()
  const docs = useDocuments()
  const waiting = docs.data?.filter((d) => d.to_review > 0).length ?? 0
  const groups: { label?: string; items: Item[] }[] = [
    {
      items: [
        { to: '/', label: 'Overview', icon: LayoutDashboard, match: (p) => p === '/' },
        {
          to: '/documents',
          label: 'Documents',
          icon: FileStack,
          match: (p, q) => (p === '/documents' && q.get('tab') !== 'review') || p.startsWith('/d/'),
        },
        {
          to: '/documents?tab=review',
          label: 'Needs review',
          icon: CircleAlert,
          match: (p, q) => p === '/documents' && q.get('tab') === 'review',
          count: waiting,
        },
      ],
    },
    {
      label: 'Configure',
      items: [
        { to: '/schemas', label: 'Schemas', icon: Shapes, match: (p) => p.startsWith('/schemas') },
        { to: '/settings', label: 'Settings', icon: Settings, match: (p) => p === '/settings' },
      ],
    },
  ]
  return (
    <nav aria-label="Main" className="flex flex-col gap-5">
      {groups.map((g, i) => (
        <div key={i} className="flex flex-col gap-0.5">
          {g.label && <p className="px-2.5 pb-1 text-xs font-medium text-sidebar-muted">{g.label}</p>}
          {g.items.map((it) => {
            const active = it.match(path, query)
            const link = linkProps(it.to)
            return (
              <a
                key={it.to}
                {...link}
                onClick={(e) => {
                  link.onClick(e)
                  onNavigate?.()
                }}
                aria-current={active ? 'page' : undefined}
                className={cn(
                  'flex h-9 items-center gap-2.5 rounded-md px-2.5 text-sidebar-muted transition-colors duration-150',
                  'hover:bg-sidebar-raised hover:text-sidebar-foreground',
                  active && 'bg-sidebar-raised font-medium text-sidebar-foreground',
                )}
              >
                <it.icon aria-hidden className={cn('size-4', active && 'text-sidebar-accent')} />
                <span className="flex-1">{it.label}</span>
                {it.count ? (
                  <span className="rounded-sm bg-review/20 px-1.5 text-xs font-medium tabular-nums text-sidebar-review">
                    {it.count}
                    <span className="sr-only"> documents</span>
                  </span>
                ) : null}
              </a>
            )
          })}
        </div>
      ))}
    </nav>
  )
}

function InstanceStatus() {
  const settings = useQuery({ queryKey: ['settings'], queryFn: api.settings, staleTime: 60_000 })
  const s = settings.data
  return (
    <div className="flex flex-col gap-1 rounded-md border border-sidebar-raised px-2.5 py-2 text-xs text-sidebar-muted">
      <p className="flex items-center gap-2">
        <span
          aria-hidden
          className={cn('size-1.5 rounded-full', s ? (s.worker ? 'bg-approved' : 'bg-review') : 'bg-sidebar-muted')}
        />
        <span className="text-sidebar-foreground">{s ? (s.worker ? 'Worker running' : 'Worker stopped') : 'Connecting…'}</span>
      </p>
      {s && (
        <p className="truncate font-mono" title={`${s.provider} · ${s.model ?? 'default model'}`}>
          {s.provider} · {s.model ?? 'default'}
        </p>
      )}
    </div>
  )
}

function SidebarBody({ onNavigate }: { onNavigate?: () => void }) {
  const home = linkProps('/')
  return (
    <div className="flex h-full flex-col gap-6 p-3">
      <a
        {...home}
        onClick={(e) => {
          home.onClick(e)
          onNavigate?.()
        }}
        className="flex items-center gap-2 px-2.5 pt-1.5 text-sidebar-foreground"
      >
        <Logo className="size-6" />
        <span className="text-[15px] font-semibold">Citefield</span>
      </a>
      <Nav onNavigate={onNavigate} />
      <span className="flex-1" />
      <InstanceStatus />
    </div>
  )
}

export function AppShell({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="min-h-dvh lg:pl-60">
      <a
        href="#main"
        className="sr-only z-50 rounded-md bg-primary px-3 py-2 text-on-primary focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
      >
        Skip to content
      </a>
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-60 bg-sidebar lg:block">
        <SidebarBody />
      </aside>

      <Dialog.Root open={open} onOpenChange={setOpen}>
        <header className="sticky top-0 z-10 flex h-12 items-center gap-2 bg-sidebar px-2 text-sidebar-foreground lg:hidden">
          <Dialog.Trigger
            aria-label="Open navigation"
            className="grid size-9 cursor-pointer place-items-center rounded-md hover:bg-sidebar-raised"
          >
            <Menu aria-hidden className="size-5" />
          </Dialog.Trigger>
          <Logo className="size-5" />
          <span className="font-semibold">Citefield</span>
        </header>
        <Dialog.Portal>
          <Dialog.Backdrop className="fixed inset-0 z-30 bg-black/50 lg:hidden" />
          <Dialog.Popup
            aria-label="Navigation"
            className="fixed inset-y-0 left-0 z-30 w-[min(17rem,85vw)] bg-sidebar pb-[env(safe-area-inset-bottom)] lg:hidden"
          >
            <Dialog.Close
              aria-label="Close navigation"
              className="absolute top-3 right-3 grid size-8 cursor-pointer place-items-center rounded-md text-sidebar-muted hover:bg-sidebar-raised"
            >
              <X aria-hidden className="size-4" />
            </Dialog.Close>
            <SidebarBody onNavigate={() => setOpen(false)} />
          </Dialog.Popup>
        </Dialog.Portal>
      </Dialog.Root>

      <div id="main" tabIndex={-1} className="outline-none">
        {children}
      </div>
    </div>
  )
}

/** Standard page frame: max width and gutters. The review screen opts out and uses the full width. */
export function Page({ children, className }: { children: ReactNode; className?: string }) {
  return <main className={cn('mx-auto w-full max-w-[1440px] px-4 py-6 sm:px-6 lg:py-8', className)}>{children}</main>
}
