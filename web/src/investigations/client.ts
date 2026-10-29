import { API_BASE } from '../api/client'
import { createRequestId } from '../api/requestId'
import type { Alert, InvestigationAction, RevisionRecord, StateEnvelope } from './types'

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
  alerts: () => request<{ alerts: Alert[] }>('/api/alerts').then(data => data.alerts),
  openAlert: (alert: string, model_id: string, client_request_id: string) =>
    request<{ chat_id: string; revision: number; created: boolean }>(
      `/api/alerts/${encodeURIComponent(alert)}/investigation`, { model_id, client_request_id }),
  create: (model_id: string, client_request_id: string) =>
    request<{ chat_id: string; revision: number }>('/api/investigations', { model_id, client_request_id }),
  get: (chat: string, signal?: AbortSignal) => request<StateEnvelope>(`/api/chats/${chat}/investigation`, undefined, signal),
  history: (chat: string, before?: number) => request<{ records: RevisionRecord[]; next_before: number | null }>(
    `/api/chats/${chat}/investigation/history${before === undefined ? '' : `?before=${before}`}`),
  action: (chat: string, action: InvestigationAction, payload: Record<string, unknown>, expected_revision: number) =>
    request<{ revision: number; sequence: number; turn_id?: string; task_id?: string }>(`/api/chats/${chat}/investigation/actions`, {
      client_request_id: createRequestId(), expected_revision, action, payload,
    }),
}
