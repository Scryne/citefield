// The few primitives every screen shares. Keyboard and focus behaviour comes from Base UI wherever there is any.
import { Tooltip } from '@base-ui/react/tooltip'
import type { LucideIcon } from 'lucide-react'
import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { cn } from '../lib'
import { buttonClass, type Size, type Variant } from './styles'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  icon?: LucideIcon
}

export function Button({ variant, size, icon: Icon, className, children, type = 'button', ...rest }: ButtonProps) {
  return (
    <button type={type} className={buttonClass(variant, size, className)} {...rest}>
      {Icon && <Icon aria-hidden className="size-4" />}
      {children}
    </button>
  )
}

/** Icon-only button: the label is both its accessible name and its tooltip. */
export function IconButton({
  label,
  icon: Icon,
  shortcut,
  className,
  ...rest
}: { label: string; icon: LucideIcon; shortcut?: string } & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <Tooltip.Root>
      <Tooltip.Trigger
        type="button"
        aria-label={label}
        className={cn(
          'grid size-8 shrink-0 cursor-pointer place-items-center rounded-md text-muted transition-colors duration-150',
          'hover:bg-surface-raised hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40',
          className,
        )}
        {...rest}
      >
        <Icon aria-hidden className="size-4" />
      </Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Positioner sideOffset={6} className="z-40">
          <Tooltip.Popup className="flex items-center gap-1.5 rounded-md bg-sidebar px-2 py-1 text-xs text-sidebar-foreground shadow-md">
            {label}
            {shortcut && <kbd className="border-sidebar-raised bg-sidebar-raised text-sidebar-muted">{shortcut}</kbd>}
          </Tooltip.Popup>
        </Tooltip.Positioner>
      </Tooltip.Portal>
    </Tooltip.Root>
  )
}

export function Card({ className, children, ...rest }: React.HTMLAttributes<HTMLElement> & { as?: 'section' }) {
  return (
    <section className={cn('rounded-lg border border-border bg-surface', className)} {...rest}>
      {children}
    </section>
  )
}

export function CardHeader({ title, id, action, hint }: { title: string; id?: string; action?: ReactNode; hint?: ReactNode }) {
  return (
    <header className="flex min-h-12 flex-wrap items-center gap-x-3 gap-y-1 border-b border-border px-4 py-2.5">
      <h2 id={id} className="font-medium text-balance">
        {title}
      </h2>
      {hint && <span className="text-xs text-muted">{hint}</span>}
      <span className="flex-1" />
      {action}
    </header>
  )
}

export function PageHeader({
  title,
  description,
  actions,
  breadcrumb,
}: {
  title: ReactNode
  description?: ReactNode
  actions?: ReactNode
  breadcrumb?: ReactNode
}) {
  return (
    <header className="flex flex-wrap items-end gap-x-6 gap-y-3 pb-6">
      <div className="flex min-w-0 flex-1 basis-80 flex-col gap-1">
        {breadcrumb}
        <h1 className="text-xl font-semibold text-balance">{title}</h1>
        {description && <p className="max-w-[70ch] text-pretty text-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  )
}

const TONE = {
  neutral: 'bg-surface-raised text-muted',
  primary: 'bg-primary-tint text-primary',
  review: 'bg-review-fill text-review-fg',
  approved: 'bg-approved-fill text-approved-fg',
  corrected: 'bg-corrected-fill text-corrected-fg',
  danger: 'bg-danger-fill text-danger-fg',
}
export type Tone = keyof typeof TONE

export function Badge({ tone = 'neutral', children, className }: { tone?: Tone; children: ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex h-5 shrink-0 items-center gap-1 rounded-sm px-1.5 text-xs font-medium whitespace-nowrap',
        TONE[tone],
        className,
      )}
    >
      {children}
    </span>
  )
}

export function EmptyState({
  icon: Icon,
  title,
  children,
  action,
}: {
  icon: LucideIcon
  title: string
  children?: ReactNode
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center gap-3 px-6 py-12 text-center">
      <span className="grid size-10 place-items-center rounded-lg bg-surface-raised text-muted">
        <Icon aria-hidden className="size-5" />
      </span>
      <div className="flex max-w-[44ch] flex-col gap-1">
        <p className="font-medium text-balance">{title}</p>
        {children && <p className="text-pretty text-muted">{children}</p>}
      </div>
      {action}
    </div>
  )
}

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cn('animate-pulse rounded-md bg-surface-raised motion-reduce:animate-none', className)} />
}

export function ErrorNote({ children }: { children: ReactNode }) {
  return (
    <p role="alert" className="rounded-md border border-danger/30 bg-danger-fill px-3 py-2 text-pretty text-danger-fg">
      {children}
    </p>
  )
}

/** The labelled select every form uses; native, so it works with every keyboard and screen reader. */
export function Select({
  label,
  hideLabel,
  className,
  children,
  ...rest
}: { label: string; hideLabel?: boolean } & React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <label className={cn('flex flex-col gap-1', className)}>
      <span className={cn('text-xs font-medium text-muted', hideLabel && 'sr-only')}>{label}</span>
      <select
        className="h-9 cursor-pointer rounded-md border border-border-strong bg-surface px-2.5 text-foreground"
        {...rest}
      >
        {children}
      </select>
    </label>
  )
}
