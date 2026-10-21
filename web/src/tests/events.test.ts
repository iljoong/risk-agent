import { afterEach, describe, expect, it, vi } from 'vitest'
import { EventDecoder, subscribeTurn } from '../api/events'

afterEach(() => vi.unstubAllGlobals())

describe('stream events', () => {
  it('reassembles split frames and ignores replayed event IDs', () => {
    const decoder = new EventDecoder()
    expect(decoder.push('id: 1\r\nevent: text_delta\r\ndata: {"te')).toEqual([])
    expect(decoder.push('xt":"Hello"}\r\n\r\n')).toEqual([{ id: 1, type: 'text_delta', data: { text: 'Hello' } }])
    expect(decoder.push('id: 1\nevent: text_delta\ndata: {"text":"Hello"}\n\n')).toEqual([])
    expect(decoder.push('id: 2\nevent: completed\ndata: {"state":"succeeded"}\n\n')[0].type).toBe('completed')
  })

  it('rejects malformed server events rather than showing false completion', () => {
    expect(() => new EventDecoder().push('id: 1\nevent: completed\ndata: "bad"\n\n')).toThrow()
    expect(() => new EventDecoder().push('id: 1\nevent: text_delta\ndata: {"text":{}}\n\n')).toThrow()
    expect(() => new EventDecoder().push('id: 1\nevent: completed\ndata: {"state":5}\n\n')).toThrow()
  })

  it('discards a disconnected partial frame while replaying after the last complete event', async () => {
    const frames = [
      'id: 1\nevent: text_delta\ndata: {"text":"A"}\n\nid: 2\nevent: text_delta\ndata: {"te',
      'id: 2\nevent: text_delta\ndata: {"text":"B"}\n\nid: 3\nevent: completed\ndata: {"state":"succeeded"}\n\n',
    ]
    const fetch = vi.fn(async (_input: string) => new Response(new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(frames.shift() ?? ''))
        controller.close()
      },
    })))
    vi.stubGlobal('fetch', fetch)
    const events = []
    for await (const event of subscribeTurn('chat1', 'turn1', new AbortController().signal)) events.push(event)
    expect(events.map(event => event.id)).toEqual([1, 2, 3])
    expect(events.filter(event => event.type === 'text_delta').map(event => event.data.text).join('')).toBe('AB')
    expect(fetch.mock.calls[1][0]).toContain('after=1')
  })
})
