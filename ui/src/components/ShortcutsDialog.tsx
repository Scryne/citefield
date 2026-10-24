import { Dialog } from '@base-ui/react/dialog'
import { X } from 'lucide-react'

const SHORTCUTS: [string[], string][] = [
  [['j'], 'Next value'],
  [['k'], 'Previous value'],
  [['a'], 'Approve the value'],
  [['e'], 'Edit the value'],
  [['c'], 'Fix the box: pick the words on the page'],
  [['Enter'], 'Save the edit or the new box'],
  [['Esc'], 'Cancel'],
  [[']'], 'Next document that needs review'],
  [['['], 'Previous document that needs review'],
  [['?'], 'Show these shortcuts'],
]

export function ShortcutsList() {
  return (
    <dl className="grid grid-cols-[auto_1fr] items-center gap-x-4 gap-y-2">
      {SHORTCUTS.map(([keys, what]) => (
        <div key={what} className="contents">
          <dt className="flex gap-1">
            {keys.map((k) => (
              <kbd key={k}>{k}</kbd>
            ))}
          </dt>
          <dd className="text-pretty">{what}</dd>
        </div>
      ))}
    </dl>
  )
}

export function ShortcutsDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Backdrop className="fixed inset-0 z-50 bg-black/40" />
        <Dialog.Popup className="fixed top-1/2 left-1/2 z-50 flex w-[min(26rem,calc(100vw-2rem))] -translate-x-1/2 -translate-y-1/2 flex-col gap-4 rounded-lg border border-border bg-surface p-5 shadow-xl">
          <div className="flex items-center">
            <Dialog.Title className="flex-1 text-base font-semibold">Keyboard shortcuts</Dialog.Title>
            <Dialog.Close
              aria-label="Close"
              className="grid size-8 cursor-pointer place-items-center rounded-md text-muted hover:bg-surface-raised"
            >
              <X aria-hidden className="size-4" />
            </Dialog.Close>
          </div>
          <ShortcutsList />
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
