import { expect, it } from 'vitest'
import { InvestigationEventDecoder, validateInvestigation } from '../investigations/events'

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
})

it('keeps independent replay cursors and handles a split CRLF', () => {
  const first = new InvestigationEventDecoder(50)
  const second = new InvestigationEventDecoder(0)
  const frame = 'id: 2\r\ndata: {"type":"STATE_SNAPSHOT","snapshot":{}}\r\n\r'
  expect(second.push(frame)).toEqual([])
  expect(second.push('\n')[0].id).toBe(2)
  expect(first.push(frame + '\n')).toEqual([])
})
