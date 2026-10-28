import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { InvestigationWorkbench } from '../investigations/InvestigationWorkbench'
import type { Investigation } from '../investigations/types'

export function fixture(): Investigation {
  const outputs = Object.fromEntries(['detect', 'investigate', 'gather_evidence', 'analyze', 'human_review', 'decision']
    .map(stage => [stage, { text: `${stage} original output`, version: 1, evidence_ids: [], needs_review: true }]))
  return {
    chat_id: 'case-chat', case_id: 'CASE-1041', connector: 'demo', revision: 1,
    current_stage: 'investigate', original_alert: { id: 'ALT-2041', priority: 'High', trigger: 'Rapid movement' },
    sources: [], shared_facts: { beneficiary_description: 'Not observed in available 90-day history' },
    outputs, history: [], review: { reviewed: false, rationale: '', prepared_note: null },
    clarification: null, external_status: 'unconfirmed', prepared: false, transactions: [], evidence: [], calculations: {},
  }
}

it('keeps inspected and current stages distinct and requires a reason before applying an edit', async () => {
  const user = userEvent.setup()
  render(<InvestigationWorkbench snapshot={fixture()} busy={false} onCommand={vi.fn()} conversation={<p>Existing conversation</p>} onDirection={vi.fn()} />)
  expect(screen.getByText('Demo connector / fictional records')).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: /4 Analyze/ }))
  expect(screen.getByRole('textbox', { name: 'Stage output' })).toHaveValue('analyze original output')
  expect(screen.getByRole('button', { name: /2 Investigate/ })).toHaveAttribute('aria-current', 'step')
  await user.type(screen.getByRole('textbox', { name: 'Stage output' }), ' amended')
  expect(screen.getByRole('button', { name: 'Apply stage amendment' })).toBeDisabled()
  expect(screen.getByText('Existing conversation')).toBeInTheDocument()
})

it('retains the analyst draft when another revision arrives or a command conflicts', async () => {
  const user = userEvent.setup()
  const onCommand = vi.fn().mockRejectedValue(new Error('Investigation changed. Refresh and reapply.'))
  const props = { busy: false, onCommand, conversation: <p>Conversation</p>, onDirection: vi.fn() }
  const snapshot = fixture()
  const { rerender } = render(<InvestigationWorkbench snapshot={snapshot} {...props} />)
  const text = screen.getByRole('textbox', { name: 'Stage output' })
  await user.clear(text)
  await user.type(text, 'My unsaved amendment')
  const newer = { ...snapshot, revision: 2, outputs: { ...snapshot.outputs,
    investigate: { ...snapshot.outputs.investigate, text: 'Other tab amendment', version: 2 } } }
  rerender(<InvestigationWorkbench snapshot={newer} {...props} />)
  expect(text).toHaveValue('My unsaved amendment')
  await user.type(screen.getByRole('textbox', { name: 'Reason for stage amendment' }), 'Correct interpretation')
  await user.click(screen.getByRole('button', { name: 'Apply stage amendment' }))
  await screen.findByRole('alert')
  expect(text).toHaveValue('My unsaved amendment')
  expect(onCommand.mock.calls[0][2]).toBe(1)
})

it('blocks review of stale outputs and does not imply an external approval', async () => {
  render(<InvestigationWorkbench snapshot={fixture()} busy={false} onCommand={vi.fn()} conversation={null} onDirection={vi.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: 'Review & record' }))
  fireEvent.change(screen.getByRole('textbox', { name: 'Analyst rationale' }), { target: { value: 'Both gaps acknowledged.' } })
  await waitFor(() => expect(screen.getByRole('button', { name: 'Mark note reviewed' })).toBeDisabled())
  expect(screen.getByText(/External saving \/ approval: unconfirmed/)).toBeInTheDocument()
})
