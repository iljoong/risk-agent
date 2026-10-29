import { afterEach, expect, it, vi } from 'vitest'
import { createRequestId } from '../api/requestId'

afterEach(() => vi.unstubAllGlobals())

it('generates distinct UUIDv4 request IDs without the secure-context randomUUID API', () => {
  vi.stubGlobal('crypto', { getRandomValues: crypto.getRandomValues.bind(crypto) })
  const ids = Array.from({ length: 32 }, () => createRequestId())
  for (const id of ids) {
    expect(id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/)
  }
  expect(new Set(ids).size).toBe(ids.length)
})

it('preserves random bytes except for the UUID version and variant bits', () => {
  vi.stubGlobal('crypto', {
    getRandomValues: (bytes: Uint8Array) => {
      bytes.set([0, 1, 2, 3, 4, 5, 6, 7, 255, 9, 10, 11, 12, 13, 14, 15])
      return bytes
    },
  })
  expect(createRequestId()).toBe('00010203-0405-4607-bf09-0a0b0c0d0e0f')
})
