import { API_BASE } from './client'
import type { TurnEvent } from './types'

const kinds = ['text_delta', 'stage', 'tool_status', 'artifact', 'completed', 'error', 'promoted']

export class EventDecoder {
  private buffer = ''
  lastId = 0
  discardPartialFrame() { this.buffer = '' }
  push(chunk: string): TurnEvent[] {
    this.buffer = (this.buffer + chunk).replace(/\r\n/g, '\n')
    const result: TurnEvent[] = []
    let boundary: number
    while ((boundary = this.buffer.indexOf('\n\n')) !== -1) {
      const frame = this.buffer.slice(0, boundary)
      this.buffer = this.buffer.slice(boundary + 2)
      if (!frame.trim() || frame.startsWith(':')) continue
      const lines = frame.split('\n')
      const id = Number(lines.find(line => line.startsWith('id:'))?.slice(3).trim())
      const type = lines.find(line => line.startsWith('event:'))?.slice(6).trim()
      const raw = lines.filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n')
      const data: unknown = JSON.parse(raw)
      if (!Number.isSafeInteger(id) || id < 1 || !type || !kinds.includes(type) || typeof data !== 'object' || data === null) {
        throw new Error('The server returned an invalid progress event. Reload the conversation.')
      }
      if (Array.isArray(data) || ['text', 'state', 'artifact_id'].some(key =>
        key in data && Reflect.get(data, key) !== null && typeof Reflect.get(data, key) !== 'string',
      )) throw new Error('The server returned an invalid progress event. Reload the conversation.')
      if (id <= this.lastId) continue
      const text = 'text' in data && typeof data.text === 'string' ? data.text : undefined
      const state = 'state' in data && typeof data.state === 'string' ? data.state : undefined
      const artifact_id = 'artifact_id' in data && typeof data.artifact_id === 'string' ? data.artifact_id : undefined
      this.lastId = id
      result.push({ id, type: type as TurnEvent['type'], data: {
        ...(text === undefined ? {} : { text }), ...(state === undefined ? {} : { state }),
        ...(artifact_id === undefined ? {} : { artifact_id }),
      } })
    }
    return result
  }
}

export async function* subscribeTurn(chatId: string, turnId: string, signal: AbortSignal): AsyncGenerator<TurnEvent> {
  const decoder = new EventDecoder()
  let attempts = 0
  while (!signal.aborted) {
    decoder.discardPartialFrame()
    try {
      const response = await fetch(`${API_BASE}/api/chats/${chatId}/turns/${turnId}/events?after=${decoder.lastId}`, { signal })
      if (!response.ok || !response.body) throw new Error(`Progress connection failed (${response.status})`)
      const reader = response.body.getReader()
      const text = new TextDecoder()
      try {
        while (true) {
          const { value, done } = await reader.read()
          if (done) break
          for (const event of decoder.push(text.decode(value, { stream: true }))) {
            yield event
            if (event.type === 'completed' || event.type === 'error') return
          }
        }
      } finally { await reader.cancel(); reader.releaseLock() }
    } catch (error) {
      if (signal.aborted) return
      if (!(error instanceof TypeError) && !(error instanceof Error && error.message.startsWith('Progress connection'))) throw error
    }
    if (++attempts > 3) throw new Error('Progress connection lost. Reopen the chat to see its saved state.')
    await new Promise<void>((resolve) => {
      const timer = window.setTimeout(resolve, 500 * attempts)
      signal.addEventListener('abort', () => { window.clearTimeout(timer); resolve() }, { once: true })
    })
  }
}
