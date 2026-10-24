import { expect, test } from '@playwright/test'

const activeBox = 'rect[data-box-id][stroke="var(--color-ink-primary)"]'

test('review a receipt with the keyboard: approve, correct, re-cite, export, delete', async ({ page }) => {
  await page.goto('/documents')
  await expect(page.getByRole('row', { name: /coffee-receipt\.pdf/ })).toContainText('1 to review')
  await page.getByRole('link', { name: /coffee-receipt\.pdf/ }).first().click()

  // the blocker summary names the check; the queue opens on that field with its reason and its box on the page
  await expect(page.getByRole('heading', { name: 'coffee-receipt.pdf' })).toBeVisible()
  await expect(page.getByText('1 of 6 values needs review')).toBeVisible()
  await expect(page.getByRole('button', { name: /Second read disagrees/ })).toBeVisible()
  const total = page.locator('[data-field-id]').first()
  await expect(total).toContainText('Total')
  await expect(total).toContainText('the second read (image only) does not agree')
  await expect(page.locator(activeBox)).toHaveCount(1)

  // ? lists the shortcuts
  await page.keyboard.press('?')
  const shortcuts = page.getByRole('dialog', { name: 'Keyboard shortcuts' })
  await expect(shortcuts).toBeVisible()
  await page.keyboard.press('Escape')
  // keys pressed inside a dialog are its own; wait until it is gone (slower machines keep it a moment longer)
  await expect(shortcuts).toBeHidden()

  // a: approve the active field
  await page.keyboard.press('a')
  await expect(page.getByText('All 6 values checked')).toBeVisible()
  await expect(page.getByText('No other document waits for review.')).toBeVisible()

  // select a field, e to edit, Enter to save: the value as read stays visible, struck through
  await page.locator('[data-field-id]', { hasText: 'Merchant' }).click()
  await page.keyboard.press('e')
  const input = page.getByRole('textbox')
  await input.fill('COFFEE HOUSE LTD')
  await input.press('Enter')
  const merchant = page.locator('[data-field-id]', { hasText: 'COFFEE HOUSE LTD' })
  await expect(merchant).toContainText('Corrected')
  await expect(merchant.locator('.line-through')).toHaveText('COFFEE HOUSE')

  // c: pick a different word on the page as the evidence, Enter saves the new box
  const before = await page.locator(activeBox).getAttribute('x')
  await page.keyboard.press('c')
  await expect(page.getByText('Click the words on the page')).toBeVisible()
  // both words start selected (the current evidence); clicking COFFEE drops it and leaves HOUSE
  await page.locator('svg rect', { has: page.locator('title', { hasText: /^COFFEE$/ }) }).click()
  await page.keyboard.press('Enter')
  await expect(page.getByText('Click the words on the page')).toHaveCount(0)
  const after = await page.locator(activeBox).getAttribute('x')
  expect(Number(after)).toBeGreaterThan(Number(before))

  // line items as a grid; a cell selects its field
  await page.getByRole('tab', { name: /Line items/ }).click()
  await page.getByRole('button', { name: /item\.name item 2: MUFFIN/ }).click()
  await expect(page.getByRole('button', { name: /item\.name item 2: MUFFIN/ })).toHaveAttribute('aria-pressed', 'true')
  await page.getByRole('tab', { name: /Checks/ }).click()
  await expect(page.getByText('Arithmetic', { exact: true })).toBeVisible()

  // export menu offers the three formats as downloads
  await page.getByRole('button', { name: 'Export' }).click()
  for (const name of [/^Excel/, /^CSV/, /^JSON/]) await expect(page.getByRole('menuitem', { name })).toBeVisible()
  const download = page.waitForEvent('download')
  await page.getByRole('menuitem', { name: /^CSV/ }).click()
  expect((await download).suggestedFilename()).toBe('coffee-receipt.csv')

  // delete asks first, then returns to the empty list
  await page.getByRole('button', { name: 'More actions' }).click()
  await page.getByRole('menuitem', { name: 'Delete document' }).click()
  await expect(page.getByRole('alertdialog')).toContainText('This cannot be undone.')
  await page.getByRole('button', { name: 'Delete document' }).click()
  await expect(page.getByText('No documents yet')).toBeVisible()
})
