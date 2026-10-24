import { expect, test } from '@playwright/test'

// Runs before review.spec.ts deletes the seeded receipt (files run in alphabetical order, one worker).

test('overview: the waiting value, the pass rate, and the way into the queue', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Overview' })).toBeVisible()
  const queue = page.getByRole('region', { name: 'Waiting for you' })
  await expect(queue).toContainText('value to check')
  await expect(page.getByRole('region', { name: 'Passed every check' })).toContainText('83.3%') // 5 of 6
  await expect(page.getByRole('region', { name: 'Why values went to review' })).toContainText('Second read disagrees')
  await expect(page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: /Needs review/ })).toContainText('1')
  await queue.getByRole('link', { name: /Start reviewing/ }).click()
  await expect(page).toHaveURL(/\/d\//)
  await expect(page.getByRole('heading', { name: 'coffee-receipt.pdf' })).toBeVisible()
})

test('documents: filters, search, selection and a failed upload read again', async ({ page }) => {
  await page.goto('/documents')
  await page.getByRole('button', { name: /^Needs review/ }).click()
  await expect(page).toHaveURL(/tab=review/)
  await expect(page.getByRole('row', { name: /coffee-receipt\.pdf/ })).toBeVisible()
  await page.getByRole('button', { name: /^Failed/ }).click()
  await expect(page.getByText('No document matches this filter.')).toBeVisible()
  await page.getByRole('button', { name: /^All/ }).click()

  await page.getByRole('searchbox').fill('nothing-like-this')
  await expect(page.getByText('Nothing matches')).toBeVisible()
  await page.getByRole('button', { name: 'Clear the search' }).click()

  // upload a file the reader cannot open: it is accepted, then fails, and can be queued again
  await page.getByRole('button', { name: 'Upload documents' }).click()
  const dialog = page.getByRole('dialog', { name: 'Upload documents' })
  await dialog.locator('input[type=file]').setInputFiles({
    name: 'broken.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.from('%PDF-1.4\nnot really a pdf\n%%EOF'),
  })
  await dialog.getByRole('button', { name: 'Upload 1 file' }).click()
  await expect(dialog).toContainText('Uploaded, reading now')
  await dialog.getByRole('button', { name: 'Done' }).click()
  await expect(page.getByRole('row', { name: /broken\.pdf/ })).toContainText('Failed', { timeout: 20_000 })
  await page.getByRole('button', { name: 'Actions for broken.pdf' }).click()
  await expect(page.getByRole('menuitem', { name: 'Read again' })).toBeVisible()
  await page.keyboard.press('Escape')

  // select both: the export is offered for the ready one only
  await page.getByRole('checkbox', { name: 'Select all shown documents' }).check()
  await expect(page.getByText('2 documents selected')).toBeVisible()
  await expect(page.getByText('1 document not ready, not exported')).toBeVisible()
  await page.getByRole('button', { name: 'Export selected' }).click()
  await expect(page.getByRole('menuitem', { name: /^Excel/ })).toHaveAttribute('href', /\/api\/export\?ids=[\w-]+&format=xlsx$/)
  await page.keyboard.press('Escape')
  await page.getByRole('button', { name: 'Clear' }).click()

  // delete the broken one from its row menu
  await page.getByRole('button', { name: 'Actions for broken.pdf' }).click()
  await page.getByRole('menuitem', { name: 'Delete' }).click()
  await page.getByRole('alertdialog').getByRole('button', { name: 'Delete document' }).click()
  await expect(page.getByRole('row', { name: /broken\.pdf/ })).toHaveCount(0)
})

test('schemas: bundled ones are read-only, a custom one is created, used and deleted', async ({ page }) => {
  await page.goto('/schemas')
  await page.getByRole('link', { name: /^invoice/ }).click()
  await expect(page.getByText('Bundled, read-only')).toBeVisible()
  await expect(page.getByRole('region', { name: 'Arithmetic rules' })).toContainText('line.amount adds up to subtotal')

  await page.goto('/schemas/new')
  // problems are listed once a save is tried, not while typing
  await expect(page.getByText('Give the schema a name.')).toHaveCount(0)
  await page.getByRole('button', { name: 'Save schema' }).click()
  await expect(page.getByText('Give the schema a name.')).toBeVisible()

  await page.getByRole('textbox', { name: 'Name', exact: false }).first().fill('parking-ticket')
  await page.getByRole('textbox', { name: 'Field 1 name' }).fill('plate')
  await page.getByRole('button', { name: 'Add field' }).click()
  await page.getByRole('textbox', { name: 'Field 2 name' }).fill('fee')
  await page.getByRole('combobox', { name: 'Field 2 kind' }).selectOption('amount')
  await page.getByRole('button', { name: 'Save schema' }).click()

  await expect(page).toHaveURL(/\/schemas\/parking-ticket$/)
  await expect(page.getByRole('region', { name: 'Fields' })).toContainText('fee')
  await page.goto('/documents')
  await page.getByRole('button', { name: 'Upload documents' }).first().click()
  await expect(page.getByRole('combobox', { name: 'Schema' }).locator('option', { hasText: 'parking-ticket' })).toHaveCount(1)
  await page.keyboard.press('Escape')

  await page.goto('/schemas/parking-ticket')
  await page.getByRole('button', { name: 'Delete' }).click()
  await page.getByRole('alertdialog').getByRole('button', { name: 'Delete schema' }).click()
  await expect(page).toHaveURL(/\/schemas$/)
  await expect(page.getByRole('link', { name: /parking-ticket/ })).toHaveCount(0)
})

test('settings: the provider without its key, and the theme choice', async ({ page }) => {
  await page.goto('/settings')
  await expect(page.getByRole('region', { name: 'Model provider' })).toContainText('fake-1')
  await page.getByRole('button', { name: 'Dark' }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await page.getByRole('button', { name: 'Light' }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
})

test('an unknown address says so and offers the way back', async ({ page }) => {
  await page.goto('/no/such/page')
  await expect(page.getByText('This page does not exist')).toBeVisible()
  await page.getByRole('link', { name: 'Go to the overview' }).click()
  await expect(page.getByRole('heading', { name: 'Overview' })).toBeVisible()
})
