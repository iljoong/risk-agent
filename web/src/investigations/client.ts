import { API_BASE } from '../api/client'
import type { InvestigationAction, StateEnvelope } from './types'

export class InvestigationError extends Error {
  readonly status: number
  constructor(message: string, status: number) { super(message); this.status = status }
}
async function request<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(API_BASE + path, body === undefined ? { signal } : {
    method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body), signal,
  })
  if (!response.ok) {
    const data = await response.json().catch(() => null) as { message?: string } | null
    throw new InvestigationError(data?.message ?? `Investigation request failed (${response.status}).`, response.status)
  }
  return response.json()
}
export const investigations = {
  create: (model_id: string, client_request_id: string) =>
    request<{ chat_id: string; revision: number }>('/api/investigations', { model_id, client_request_id }),
  get: (chat: string, signal?: AbortSignal) => request<StateEnvelope>(`/api/chats/${chat}/investigation`, undefined, signal),
  action: (chat: string, action: InvestigationAction, payload: Record<string, unknown>, expected_revision: number) =>
    request<{ revision: number; sequence: number; turn_id?: string; task_id?: string }>(`/api/chats/${chat}/investigation/actions`, {
      client_request_id: crypto.randomUUID(), expected_revision, action, payload,
    }),
}
