import type { Artifact, Attachment, Chat, ChatSummary, ModelChoice, Receipt, Skill, Task, TurnRequest } from './types'

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(API_BASE + path, options)
  if (!response.ok) {
    const body: unknown = await response.json()
    const message = typeof body === 'object' && body !== null && 'message' in body && typeof body.message === 'string'
      ? body.message : `Request failed (${response.status}). Check the input and try again.`
    throw new Error(message)
  }
  return response.status === 204 ? undefined as T : response.json()
}
const json = (method: string, body?: unknown): RequestInit => ({
  method, headers: { 'content-type': 'application/json' }, ...(body === undefined ? {} : { body: JSON.stringify(body) }),
})
export const api = {
  models: () => fetchJson<{ models: ModelChoice[]; default_model_id: string }>('/api/models'),
  skills: () => fetchJson<Skill[]>('/api/skills'),
  chats: () => fetchJson<ChatSummary[]>('/api/chats'),
  chat: (id: string) => fetchJson<Chat>(`/api/chats/${id}`),
  create: (model_id: string) => fetchJson<ChatSummary>('/api/chats', json('POST', { model_id })),
  patch: (id: string, body: { title?: string; model_id?: string }) => fetchJson<ChatSummary>(`/api/chats/${id}`, json('PATCH', body)),
  delete: (id: string) => fetchJson<void>(`/api/chats/${id}`, json('DELETE')),
  send: (id: string, body: TurnRequest) => fetchJson<Receipt>(`/api/chats/${id}/turns`, json('POST', body)),
  cancel: (id: string, turn: string) => fetchJson<unknown>(`/api/chats/${id}/turns/${turn}/cancel`, json('POST')),
  retry: (id: string, task: string) => fetchJson<Task>(`/api/chats/${id}/tasks/${task}/retry`, json('POST')),
  upload: (id: string, file: File) => {
    const body = new FormData(); body.append('file', file)
    return fetchJson<Attachment>(`/api/chats/${id}/attachments`, { method: 'POST', body })
  },
}
export const artifactUrl = (chatId: string, artifact: Artifact, mode: 'preview' | 'download') =>
  `${API_BASE}/api/chats/${chatId}/artifacts/${artifact.id}/${mode}`
