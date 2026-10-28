import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { ChatSidebar } from '../chat/ChatSidebar'
import type { Alert } from '../investigations/types'

const base: Alert = {
  id: 'ALT-2041', case_id: 'CASE-1041', subject: 'Harbour Components Ltd', priority: 'High',
  trigger: 'Rapid movement of funds', received: '2026-10-28', review_by: '2026-11-27',
  evidence: 'demo', chat_id: null, stage: null,
}

function sidebar(alerts: Alert[], onOpenAlert = vi.fn(), onNewInvestigation = vi.fn()) {
  render(<ChatSidebar chats={[]} current={null} open onNew={vi.fn()} onOpen={vi.fn()} onNewInvestigation={onNewInvestigation}
    creating={false} onRename={vi.fn()} onDelete={vi.fn()} onAccount={vi.fn()} onClose={vi.fn()}
    alerts={alerts} onOpenAlert={onOpenAlert} />)
}

it('starts from an alert and keeps New investigation as a separate action', async () => {
  const onOpenAlert = vi.fn(), onNewInvestigation = vi.fn()
  sidebar([base, { ...base, id: 'ALT-2038', subject: 'Fenwick Print Ltd', chat_id: 'c1', stage: 'gather_evidence' }],
    onOpenAlert, onNewInvestigation)
  await userEvent.click(screen.getByRole('button', { name: /Open alert ALT-2041/ }))
  expect(onOpenAlert).toHaveBeenCalledWith(expect.objectContaining({ id: 'ALT-2041' }))
  expect(screen.getByRole('button', { name: /Resume alert ALT-2038/ })).toHaveTextContent('Case open at Gather evidence')
  await userEvent.click(screen.getByRole('button', { name: 'New investigation' }))
  expect(onNewInvestigation).toHaveBeenCalledTimes(1)
  expect(onOpenAlert).toHaveBeenCalledTimes(1)
})
