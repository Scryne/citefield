// Class strings shared by components and by links styled as buttons.
import { cn } from '../lib'

export type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'
export type Size = 'sm' | 'md'

const VARIANT: Record<Variant, string> = {
  primary: 'bg-primary text-on-primary hover:bg-primary-hover',
  secondary: 'border border-border-strong bg-surface text-foreground hover:bg-surface-raised',
  ghost: 'text-muted hover:bg-surface-raised hover:text-foreground',
  danger: 'bg-danger text-white hover:bg-danger/90',
}
const SIZE: Record<Size, string> = { sm: 'h-8 gap-1.5 px-2.5 text-[13px]', md: 'h-9 gap-2 px-3.5' }

export function buttonClass(variant: Variant = 'secondary', size: Size = 'md', className?: string) {
  return cn(
    'inline-flex shrink-0 cursor-pointer items-center justify-center rounded-md font-medium whitespace-nowrap',
    'transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50',
    VARIANT[variant],
    SIZE[size],
    className,
  )
}

export const inputClass =
  'h-9 w-full min-w-0 rounded-md border border-border-strong bg-surface px-2.5 text-foreground placeholder:text-muted/70'
