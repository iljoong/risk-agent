import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import App from '../App'
import { ArtifactPanel } from '../artifacts/ArtifactPanel'
import type { Chat, TurnRequest } from '../api/types'

const chat = { id: 'chat1', title: 'New chat', model_id: 'openai', turns: [], attachments: [], tasks: [], artifacts: [] }

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(async (input: string, options?: RequestInit) => {
    const data = input === '/api/models' ? { models: [{ id: 'openai', label: 'Foundry OpenAI' }], default_model_id: 'openai' }
      : input === '/api/skills' ? [{ id: 'rfp-response', name: 'rfp-response', description: 'Draft RFP slides' }]
      : input === '/health/ready' ? { worker_ready: true }
      : input === '/api/chats' && options?.method === 'POST' ? chat
      : input === '/api/chats' ? [] : chat
    return new Response(JSON.stringify(data), { status: 200, headers: { 'content-type': 'application/json' } })
  }))
})
afterEach(() => vi.unstubAllGlobals())

it('resizes the session rail with keyboard controls while retaining the message draft', async () => {
  const user = userEvent.setup()
  render(<App />)
  await screen.findByRole('option', { name: 'Foundry OpenAI' })
  await user.type(screen.getByRole('textbox', { name: 'Message' }), 'Pending investigation question')
  const resize = screen.getByRole('separator', { name: 'Resize session sidebar' })
  const width = Number(resize.getAttribute('aria-valuenow'))
  fireEvent.keyDown(resize, { key: 'ArrowRight' })
  expect(Number(resize.getAttribute('aria-valuenow'))).toBeGreaterThan(width)
  fireEvent.keyDown(resize, { key: 'Home' })
  expect(resize).toHaveAttribute('aria-valuenow', '180')
  expect(screen.getByRole('textbox', { name: 'Message' })).toHaveValue('Pending investigation question')
})

it.each([
  ['Review a document', 'Summarize the attached PDF, cite the relevant pages, and list gaps or questions for review.'],
  ['Explore a question', 'Help me explore a finance question. Ask what context and evidence you need before drawing conclusions.'],
])('starts ordinary chat from %s without retaining a selected skill', async (label, prompt) => {
  const user = userEvent.setup()
  render(<App />)
  await screen.findByRole('option', { name: 'Foundry OpenAI' })
  await user.click(screen.getByRole('button', { name: 'Choose a skill' }))
  await user.click(screen.getByRole('option', { name: /rfp-response/ }))
  await user.click(screen.getByRole('button', { name: new RegExp(label) }))
  expect(screen.getByRole('textbox', { name: 'Message' })).toHaveValue(prompt)
  expect(screen.queryByRole('button', { name: 'Clear skill' })).not.toBeInTheDocument()
})

it('offers skills in the composer and clearly disables future account actions', async () => {
  const user = userEvent.setup()
  render(<App />)
  await screen.findByRole('option', { name: 'Foundry OpenAI' })
  await user.click(screen.getByRole('button', { name: 'Choose a skill' }))
  await user.click(screen.getByRole('option', { name: /rfp-response/ }))
  expect(screen.getByText('/rfp-response')).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Account & access' }))
  expect(screen.getByRole('button', { name: 'Sign in' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Manage members' })).toBeDisabled()
})

it.each(['button', 'slash'])('shows only skill names in the %s selection popup', async entry => {
  const user = userEvent.setup()
  render(<App />)
  await screen.findByRole('option', { name: 'Foundry OpenAI' })
  if (entry === 'button') await user.click(screen.getByRole('button', { name: 'Choose a skill' }))
  else await user.type(screen.getByRole('textbox', { name: 'Message' }), '/rfp')
  expect(screen.queryByText('Draft RFP slides')).not.toBeInTheDocument()
  await user.click(screen.getByRole('option', { name: 'rfp-response' }))
  expect(screen.getByText('/rfp-response')).toBeInTheDocument()
  expect(screen.queryByRole('listbox', { name: 'Available skills' })).not.toBeInTheDocument()
})

it('shows a PDF-only error instead of uploading another format', async () => {
  render(<App />)
  await screen.findByRole('option', { name: 'Foundry OpenAI' })
  fireEvent.change(screen.getByLabelText('Attach PDF'), {
    target: { files: [new File(['data'], 'RFP.docx', { type: 'application/octet-stream' })] },
  })
  expect(await screen.findByRole('alert')).toHaveTextContent('PDF')
})

it('keeps generated HTML in an opaque sandbox rather than the app DOM', () => {
  render(<ArtifactPanel chatId="chat1" artifact={{
    id: 'artifact1', title: 'Response', version: 1, text_content: 'draft', parent_version_id: null,
  }} onClose={() => {}} />)
  expect(screen.getByTitle('HTML artifact preview')).toHaveAttribute('sandbox', '')
})

it('allows clearing automatic artifact context before sending a question', async () => {
  const original = fetch
  const saved = { ...chat, title: 'Saved chat', artifacts: [{ id: 'large-artifact', title: 'Large draft', version: 1, text_content: 'draft', parent_version_id: null }] }
  const requests: string[] = []
  vi.stubGlobal('fetch', vi.fn(async (input: string, options?: RequestInit) => {
    if (input.endsWith('/turns') && options?.body) requests.push(String(options.body))
    if (input === '/api/chats') return new Response(JSON.stringify([saved]))
    if (input === '/api/chats/chat1') return new Response(JSON.stringify(saved))
    return original(input, options)
  }))
  const user = userEvent.setup()
  render(<App />)
  await user.click(await screen.findByRole('button', { name: 'Saved chat' }))
  await user.click(await screen.findByRole('button', { name: 'Clear artifact context' }))
  await user.type(screen.getByRole('textbox', { name: 'Message' }), 'Thanks')
  await user.click(screen.getByRole('button', { name: 'Send message' }))
  await waitFor(() => expect(requests.length).toBe(1))
  expect(JSON.parse(requests[0]).artifact_version_id).toBeNull()
})

it('does not put an upload from a previous chat into the current composer', async () => {
  const original = fetch
  const first = { ...chat, id: 'chat-a', title: 'Chat A' }
  const second = { ...chat, id: 'chat-b', title: 'Chat B' }
  let finishUpload!: (response: Response) => void
  const upload = new Promise<Response>(resolve => { finishUpload = resolve })
  vi.stubGlobal('fetch', vi.fn(async (input: string, options?: RequestInit) => {
    if (input === '/api/chats') return new Response(JSON.stringify([first, second]))
    if (input === '/api/chats/chat-a') return new Response(JSON.stringify(first))
    if (input === '/api/chats/chat-b') return new Response(JSON.stringify(second))
    if (input === '/api/chats/chat-a/attachments') return upload
    return original(input, options)
  }))
  const user = userEvent.setup()
  render(<App />)
  await user.click(await screen.findByRole('button', { name: 'Chat A' }))
  fireEvent.change(screen.getByLabelText('Attach PDF'), { target: { files: [new File(['%PDF-'], 'RFP.pdf')] } })
  await user.click(screen.getByRole('button', { name: 'Chat B' }))
  await act(async () => { finishUpload(new Response(JSON.stringify({ id: 'pdf-a', filename: 'RFP.pdf', state: 'pending', warnings: [] }))) })
  expect(screen.queryByText('RFP.pdf')).not.toBeInTheDocument()
})

it('keeps a slash-selected skill for clarification replies until explicitly cleared', async () => {
  const original = fetch
  const saved: Chat = { ...chat, title: 'Clarification flow' }
  const requests: TurnRequest[] = []
  vi.stubGlobal('fetch', vi.fn(async (input: string, options?: RequestInit) => {
    if (input === '/api/chats/chat1/turns' && options?.body) {
      const request: TurnRequest = JSON.parse(String(options.body))
      requests.push(request)
      saved.turns = [...saved.turns, {
        id: `turn-${requests.length}`, request, state: 'succeeded', mode: 'background',
        answer: 'How will you participate?', error: null,
      }]
      return new Response(JSON.stringify({
        turn_id: `turn-${requests.length}`, mode: 'background', task_id: 'task1', events_url: '',
      }))
    }
    if (input === '/api/chats' && options?.method !== 'POST') return new Response(JSON.stringify([saved]))
    if (input === '/api/chats/chat1') return new Response(JSON.stringify(saved))
    return original(input, options)
  }))
  const user = userEvent.setup()
  render(<App />)
  await screen.findByRole('option', { name: 'Foundry OpenAI' })
  await user.type(screen.getByRole('textbox', { name: 'Message' }), '/rfp-response Ask before analyzing.')
  await user.click(screen.getByRole('button', { name: 'Send message' }))
  await waitFor(() => expect(screen.getByRole('textbox', { name: 'Message' })).toHaveValue(''))
  expect(screen.getByRole('button', { name: 'Clear skill' })).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'New conversation' }))
  await user.click(screen.getByRole('button', { name: 'Clarification flow' }))
  await screen.findByRole('button', { name: 'Clear skill' })
  await user.type(screen.getByRole('textbox', { name: 'Message' }), 'Bidding alone.')
  await user.click(screen.getByRole('button', { name: 'Send message' }))
  await waitFor(() => expect(requests).toHaveLength(2))
  expect(requests[1].skill_id).toBe('rfp-response')
  await waitFor(() => expect(screen.getByRole('textbox', { name: 'Message' })).toHaveValue(''))
  await user.click(screen.getByRole('button', { name: 'Clear skill' }))
  await user.type(screen.getByRole('textbox', { name: 'Message' }), 'What is an RFP?')
  await user.click(screen.getByRole('button', { name: 'Send message' }))
  await waitFor(() => expect(requests).toHaveLength(3))
  expect(requests[2].skill_id).toBeNull()
})
