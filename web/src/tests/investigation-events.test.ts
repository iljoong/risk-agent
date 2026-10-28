import { afterEach, expect, it, vi } from 'vitest'
import { InvestigationEventDecoder, subscribeInvestigation, validateInvestigation } from '../investigations/events'
import { investigations } from '../investigations/client'
import { fixture } from './investigation-fixture'

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals() })

it('reassembles AG-UI state frames and drops replayed delivery IDs', () => {
  const decoder = new InvestigationEventDecoder(10)
  expect(decoder.push('id: 11\ndata: {"type":"STATE_')).toEqual([])
  expect(decoder.push('SNAPSHOT","snapshot":{"revision":2}}\n\n')[0].id).toBe(11)
  expect(decoder.push('id: 11\ndata: {"type":"STATE_SNAPSHOT","snapshot":{}}\n\n')).toEqual([])
  decoder.discardPartialFrame()
  expect(() => decoder.push('id: 12\ndata: {"type":"STATE_SNAPSHOT"}\n\n')).toThrow()
})

it('does not accept an invalid event type or a nonnumeric replay cursor', () => {
  expect(() => new InvestigationEventDecoder(0).push('id: junk\ndata: {"type":"STATE_SNAPSHOT","snapshot":{}}\n\n')).toThrow()
  expect(() => new InvestigationEventDecoder(0).push('id: 1\ndata: {"type":"pretend_success"}\n\n')).toThrow()
  expect(() => validateInvestigation({ revision: 1, outputs: {} })).toThrow()
  const state = fixture()
  state.sources = [{ source_id: 'SRC-04', title: 'Prior case', status: 'restricted',
    snapshot_at: null, version: null, coverage: 'Authorized access required.' }]
  expect(validateInvestigation(state).sources[0].source_id).toBe('SRC-04')
})

it('keeps independent replay cursors and handles a split CRLF', () => {
  const first = new InvestigationEventDecoder(50)
  const second = new InvestigationEventDecoder(0)
  const frame = 'id: 2\r\ndata: {"type":"STATE_SNAPSHOT","snapshot":{}}\r\n\r'
  expect(second.push(frame)).toEqual([])
  expect(second.push('\n')[0].id).toBe(2)
  expect(first.push(frame + '\n')).toEqual([])
})

it('rehydrates an invalid checkpoint without starting another execution', async () => {
  const fetcher = vi.fn().mockResolvedValue(new Response(null, { status: 409 }))
  vi.stubGlobal('fetch', fetcher)
  vi.spyOn(investigations, 'get').mockResolvedValue({ snapshot: fixture(), sequence: 72 })
  const controller = new AbortController()
  const stream = subscribeInvestigation('case-chat', 999, controller.signal)
  expect((await stream.next()).value).toMatchObject({ type: 'STATE_SNAPSHOT', snapshot: { revision: 1 } })
  expect(fetcher.mock.calls[0][0]).toContain('/investigation/events?after=999')
  expect(fetcher).toHaveBeenCalledTimes(1)
  controller.abort()
  await stream.return(undefined)
})
