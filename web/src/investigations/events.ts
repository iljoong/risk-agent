import { EventSchemas } from '@ag-ui/core/schemas'
import { z } from 'zod/v4'
import { API_BASE } from '../api/client'
import { investigations } from './client'
import { stages } from './types'
import type { Investigation } from './types'

export class InvestigationEventDecoder {
  private buffer = ''
  sequence: number
  constructor(sequence: number) { this.sequence = sequence }
  discardPartialFrame() { this.buffer = '' }
  push(chunk: string) {
    this.buffer = (this.buffer + chunk).replace(/\r\n/g, '\n')
    if (this.buffer.length > 2_000_000) throw new Error('Investigation event exceeds the size limit.')
    const frames = this.buffer.split('\n\n')
    this.buffer = frames.pop() ?? ''
    return frames.flatMap(frame => {
      const lines = frame.split('\n')
      const data = lines.filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n')
      if (!data) return []
      const rawId = lines.find(line => line.startsWith('id:'))?.slice(3).trim()
      if (!rawId || !/^\d+$/.test(rawId)) throw new Error('Invalid investigation replay cursor.')
      const id = Number(rawId)
      if (!Number.isSafeInteger(id)) throw new Error('Invalid investigation replay cursor.')
      if (id <= this.sequence) return []
      const event = EventSchemas.parse(JSON.parse(data))
      this.sequence = id
      return [{ id, event }]
    })
  }
}

const outputSchema = z.object({ text: z.string().max(12000), version: z.number().int().positive(),
  evidence_ids: z.array(z.string()), needs_review: z.boolean() })
const snapshotSchema = z.object({
  chat_id: z.string(), case_id: z.string(), connector: z.literal('demo'), revision: z.number().int().positive(),
  current_stage: z.enum(stages), original_alert: z.object({ id: z.string(), priority: z.string(), trigger: z.string() }),
  shared_facts: z.object({ beneficiary_description: z.string() }),
  outputs: z.record(z.enum(stages), outputSchema),
  review: z.object({ reviewed: z.boolean(), rationale: z.string(), prepared_note: z.string().nullable() }),
  sources: z.array(z.object({ source_id: z.string(), title: z.string(), status: z.string(),
    snapshot_at: z.string().nullable(), version: z.string().nullable(), coverage: z.string(),
    retrieved_at: z.string().optional(), data: z.record(z.string(), z.unknown()).optional() })).max(7),
  transactions: z.array(z.object({ id: z.string(), timestamp: z.string(), direction: z.string(),
    amount_gbp: z.number(), counterparty: z.string(), reference: z.string() })).max(100),
  evidence: z.array(z.object({ id: z.string(), kind: z.string(), title: z.string(), text: z.string(),
    source_ids: z.array(z.string()), locators: z.array(z.string()) })).max(20),
  history: z.array(z.object({ actor: z.string(), action: z.string(), revision: z.number().int(),
    timestamp: z.number(), reason: z.string().optional(), before: z.string().optional(),
    after: z.string().optional(), stage_id: z.enum(stages).optional() })),
  clarification: z.record(z.string(), z.unknown()).nullable(),
  external_status: z.literal('unconfirmed'), prepared: z.boolean(),
  calculations: z.record(z.string(), z.union([z.number(), z.string()])),
})
export function validateInvestigation(value: unknown): Investigation { return snapshotSchema.parse(value) }

const delay = (signal: AbortSignal) => new Promise<void>(resolve => {
  const done = () => { window.clearTimeout(timer); signal.removeEventListener('abort', done); resolve() }
  const timer = window.setTimeout(done, 1500)
  signal.addEventListener('abort', done, { once: true })
})

export async function* subscribeInvestigation(chat: string, sequence: number, signal: AbortSignal) {
  const decoder = new InvestigationEventDecoder(sequence)
  while (!signal.aborted) {
    let response: Response
    try { response = await fetch(`${API_BASE}/api/chats/${chat}/investigation/events?after=${decoder.sequence}`, { signal }) }
    catch (error) { if (signal.aborted) return; await delay(signal); if (error instanceof TypeError) continue; throw error }
    if (response.status === 409) {
      const saved = await investigations.get(chat, signal)
      const snapshot = validateInvestigation(saved.snapshot)
      decoder.sequence = saved.sequence
      yield { type: 'STATE_SNAPSHOT' as const, snapshot }
      continue
    }
    if (!response.ok || !response.body) throw new Error(`Investigation stream unavailable (${response.status}). Reopen the session.`)
    const reader = response.body.getReader()
    const text = new TextDecoder()
    try {
      while (!signal.aborted) {
        const { done, value } = await reader.read()
        if (done) break
        for (const { event } of decoder.push(text.decode(value, { stream: true }))) {
          if (event.type === 'STATE_SNAPSHOT') {
            const snapshot = validateInvestigation(event.snapshot)
            if (snapshot.chat_id !== chat) throw new Error('Investigation stream scope mismatch.')
            yield { ...event, snapshot }
          } else if (event.type === 'ACTIVITY_SNAPSHOT') yield event
        }
      }
    } catch (error) {
      if (signal.aborted) return
      if (!(error instanceof TypeError)) throw error
    } finally { await reader.cancel().catch(() => {}); reader.releaseLock(); decoder.discardPartialFrame() }
    if (!signal.aborted) await delay(signal)
  }
}
