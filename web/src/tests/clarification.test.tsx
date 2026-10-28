import { render, screen } from '@testing-library/react'
import { StrictMode } from 'react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { ClarificationSurface } from '../investigations/ClarificationSurface'
import { buildScopeOperations, validateScopeOperations } from '../investigations/surface'

it('renders the restricted official A2UI surface and submits only the scope answer', async () => {
  const user = userEvent.setup()
  const onResolve = vi.fn().mockResolvedValue(undefined)
  render(<ClarificationSurface activity={{
    id: 'scope1', surface_revision: 2, status: 'pending', question: 'Narrow scope',
    operations: buildScopeOperations('scope1', 2, 'Narrow scope'), answer: null,
  }} busy={false} onResolve={onResolve} onCancel={vi.fn()} />, { wrapper: StrictMode })
  expect(screen.queryByText(/Plain form fallback/)).not.toBeInTheDocument()
  await user.type(await screen.findByRole('textbox', { name: 'Investigation scope' }), 'Compare the supplier explanation.')
  await user.click(screen.getByRole('button', { name: 'Apply scope and ask agent' }))
  expect(onResolve).toHaveBeenCalledWith({
    clarification_id: 'scope1', surface_revision: 2, answer: 'Compare the supplier explanation.',
  })
})

it('retains the rest of the desk and offers a host fallback for rejected surface operations', async () => {
  const user = userEvent.setup()
  const onResolve = vi.fn().mockResolvedValue(undefined)
  render(<><p>Evidence remains usable</p><ClarificationSurface activity={{
    id: 'scope1', surface_revision: 2, status: 'pending', question: 'Narrow scope',
    operations: [{ script: 'forbidden' }], answer: null,
  }} busy={false} onResolve={onResolve} onCancel={vi.fn()} /></>)
  expect(screen.getByText('Evidence remains usable')).toBeInTheDocument()
  expect(screen.getByText(/Plain form fallback/)).toBeInTheDocument()
  await user.type(screen.getByRole('textbox', { name: 'Investigation scope' }), 'Only permitted evidence.')
  await user.click(screen.getByRole('button', { name: 'Apply scope and ask agent' }))
  expect(onResolve).toHaveBeenCalledWith({ clarification_id: 'scope1', surface_revision: 2, answer: 'Only permitted evidence.' })
})

it('rejects unknown actions, excessive nesting and oversized surface updates before rendering', () => {
  const ops = buildScopeOperations('scope1', 2, 'Narrow scope')
  const badAction = JSON.parse(JSON.stringify(ops).replace('submit_scope', 'external_approval'))
  expect(() => validateScopeOperations(badAction, 'scope1', 2, 'Narrow scope')).toThrow()
  expect(() => validateScopeOperations([{ text: 'x'.repeat(65537) }], 'scope1', 2, 'Narrow scope')).toThrow()
  let deep: unknown = {}
  for (let i = 0; i < 13; i++) deep = { child: deep }
  expect(() => validateScopeOperations(deep, 'scope1', 2, 'Narrow scope')).toThrow()
})
