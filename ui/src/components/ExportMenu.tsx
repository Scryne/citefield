import { Menu } from '@base-ui/react/menu'
import { ChevronDown, Download } from 'lucide-react'
import type { ExportFormat } from '../api'
import { buttonClass } from './styles'

const FORMATS: { format: ExportFormat; label: string; hint: string }[] = [
  { format: 'xlsx', label: 'Excel (.xlsx)', hint: 'fields and line items sheets' },
  { format: 'csv', label: 'CSV', hint: 'one row per value' },
  { format: 'json', label: 'JSON', hint: 'with boxes and checks' },
]

export function ExportMenu({
  href,
  disabled,
  variant = 'primary',
  label = 'Export',
}: {
  href: (format: ExportFormat) => string
  disabled?: boolean
  variant?: 'primary' | 'secondary'
  label?: string
}) {
  return (
    <Menu.Root>
      <Menu.Trigger disabled={disabled} className={buttonClass(variant, 'md')}>
        <Download aria-hidden className="size-4" />
        {label}
        <ChevronDown aria-hidden className="-mr-1 size-4 opacity-70" />
      </Menu.Trigger>
      <Menu.Portal>
        <Menu.Positioner sideOffset={6} align="end" className="z-40">
          <Menu.Popup className="flex min-w-56 flex-col rounded-md border border-border bg-surface p-1 shadow-lg">
            {FORMATS.map((f) => (
              <Menu.LinkItem
                key={f.format}
                href={href(f.format)}
                download
                className="flex cursor-pointer flex-col rounded-sm px-2.5 py-1.5 data-[highlighted]:bg-surface-raised"
              >
                <span>{f.label}</span>
                <span className="text-xs text-muted">{f.hint}</span>
              </Menu.LinkItem>
            ))}
          </Menu.Popup>
        </Menu.Positioner>
      </Menu.Portal>
    </Menu.Root>
  )
}
