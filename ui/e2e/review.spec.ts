import { expect, test } from '@playwright/test'

test('review a receipt with the keyboard: approve, correct, re-cite, export, delete', async ({ page }) => {
  await page.goto('/')
  const row = page.getByRole('link', { name: /coffee-receipt\.pdf/ })
  await expect(row).toContainText('1 to review')
  await row.click()

  // the queue opens on the one field the checks did not clear, with its reason and its box on the page
  await expect(page.getByRole('heading', { name: 'coffee-receipt.pdf' })).toBeVisible()
  const total = page.locator('[data-field-id]').first()
  await expect(total).toContainText('total')
  await expect(total).toContainText('the second read (image only) does not agree')
  await expect(page.locator('rect[data-box-id][stroke="var(--color-primary)"]')).toHaveCount(1)

  // a: approve the active field
  await page.keyboard.press('a')
  await expect(page.getByText('Nothing waits for you here.')).toBeVisible()
  await expect(page.getByText('all checked')).toBeVisible()

  // select a field, e to edit, Enter to save: the old value stays visible, struck through
  await page.locator('[data-field-id]', { hasText: 'merchant' }).click()
  await page.keyboard.press('e')
  const input = page.getByRole('textbox')
  await input.fill('COFFEE HOUSE LTD')
  await input.press('Enter')
  const merchant = page.locator('[data-field-id]', { hasText: 'COFFEE HOUSE LTD' })
  await expect(merchant).toContainText('Corrected')
  await expect(merchant.locator('.line-through')).toHaveText('COFFEE HOUSE')

  // c: pick a different word on the page as the evidence, Enter saves the new box
  const before = await page.locator('rect[data-box-id][stroke="var(--color-primary)"]').getAttribute('x')
  await page.keyboard.press('c')
  await expect(page.getByText('Click the words on the page')).toBeVisible()
  // both words start selected (the current evidence); clicking COFFEE drops it and leaves HOUSE
  await page.locator('svg rect', { has: page.locator('title', { hasText: /^COFFEE$/ }) }).click()
  await page.keyboard.press('Enter')
  await expect(page.getByText('Click the words on the page')).toHaveCount(0)
  const after = await page.locator('rect[data-box-id][stroke="var(--color-primary)"]').getAttribute('x')
  expect(Number(after)).toBeGreaterThan(Number(before))

  // export menu offers the three formats as downloads
  await page.getByRole('button', { name: 'Export' }).click()
  for (const name of ['Excel (.xlsx)', 'CSV', 'JSON']) await expect(page.getByRole('menuitem', { name })).toBeVisible()
  const download = page.waitForEvent('download')
  await page.getByRole('menuitem', { name: 'CSV' }).click()
  expect((await download).suggestedFilename()).toBe('coffee-receipt.csv')

  // delete asks first, then returns to the empty list
  await page.getByRole('button', { name: 'Delete document' }).click()
  await expect(page.getByRole('alertdialog')).toContainText('This cannot be undone.')
  await page.getByRole('button', { name: 'Delete document' }).last().click()
  await expect(page.getByText('No documents yet.')).toBeVisible()
})
