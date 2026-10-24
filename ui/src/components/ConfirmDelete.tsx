import { AlertDialog } from '@base-ui/react/alert-dialog'
import type { ReactNode } from 'react'
import { Button } from './ui'

/** Every destructive action goes through this: what goes, that it cannot be undone, and an exact verb. */
export function ConfirmDelete({
  open,
  onOpenChange,
  title,
  children,
  confirm,
  onConfirm,
  busy,
  error,
  trigger,
}: {
  open?: boolean
  onOpenChange?: (open: boolean) => void
  title: string
  children: ReactNode
  confirm: string
  onConfirm: () => void
  busy?: boolean
  error?: string | null
  trigger?: React.ReactElement
}) {
  return (
    <AlertDialog.Root open={open} onOpenChange={onOpenChange}>
      {trigger && <AlertDialog.Trigger render={trigger} />}
      <AlertDialog.Portal>
        <AlertDialog.Backdrop className="fixed inset-0 z-50 bg-black/40" />
        <AlertDialog.Popup className="fixed top-1/2 left-1/2 z-50 flex w-[min(28rem,calc(100vw-2rem))] -translate-x-1/2 -translate-y-1/2 flex-col gap-3 rounded-lg border border-border bg-surface p-5 shadow-xl">
          <AlertDialog.Title className="text-base font-semibold text-balance">{title}</AlertDialog.Title>
          <AlertDialog.Description className="text-pretty text-muted">{children}</AlertDialog.Description>
          {error && (
            <p role="alert" className="text-danger-fg">
              {error}
            </p>
          )}
          <div className="flex justify-end gap-2 pt-2">
            <AlertDialog.Close render={<Button>Cancel</Button>} />
            <Button variant="danger" onClick={onConfirm} disabled={busy}>
              {busy ? 'Deleting…' : confirm}
            </Button>
          </div>
        </AlertDialog.Popup>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  )
}
