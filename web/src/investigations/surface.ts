import { z } from 'zod'

export const scopeCatalogId = 'urn:rci:scope-clarification:v1'
export function buildScopeOperations(id: string, revision: number, question: string) {
  return [
    { version: 'v0.9' as const, createSurface: { surfaceId: id, catalogId: scopeCatalogId } },
    { version: 'v0.9' as const, updateComponents: { surfaceId: id, components: [
      { id: 'root', component: 'Column', children: ['question', 'answer', 'submit'] },
      { id: 'question', component: 'Text', text: question },
      { id: 'answer', component: 'TextInput', label: 'Investigation scope', value: { path: '/answer' } },
      { id: 'submit-label', component: 'Text', text: 'Apply scope and ask agent' },
      { id: 'submit', component: 'Button', child: 'submit-label',
        action: { event: { name: 'submit_scope', context: { answer: { path: '/answer' } } } } },
    ] } },
    { version: 'v0.9' as const, updateDataModel: { surfaceId: id, path: '/', value: { answer: '', surfaceRevision: revision } } },
  ]
}
export const clarificationIdentity = z.object({
  id: z.string().min(1).max(100), surface_revision: z.number().int().positive(),
  status: z.enum(['pending', 'resolved', 'cancelled']), question: z.string().max(2000),
})

export function validateScopeOperations(value: unknown, id: string, revision: number, question: string) {
  const pending: [unknown, number][] = [[value, 0]]
  let count = 0
  while (pending.length) {
    const [item, depth] = pending.pop()!
    if (++count > 1000 || depth > 12) throw new Error('Clarification surface exceeds its structural limits.')
    if (item && typeof item === 'object') {
      const children = Object.values(item)
      if (children.length > 100) throw new Error('Clarification surface exceeds 100 components.')
      pending.push(...children.map(child => [child, depth + 1] as [unknown, number]))
    }
  }
  if (new TextEncoder().encode(JSON.stringify(value)).length > 65536) throw new Error('Clarification surface exceeds 64 KiB.')
  const expected = buildScopeOperations(id, revision, question)
  // Compare keys as well as values: no extra actions, URLs, bindings or components.
  function same(left: unknown, right: unknown): boolean {
    if (left === null || right === null || typeof left !== 'object' || typeof right !== 'object') return left === right
    const a = Object.entries(left).sort(([a], [b]) => a.localeCompare(b))
    const b = Object.entries(right).sort(([a], [b]) => a.localeCompare(b))
    return a.length === b.length && a.every(([key, item], index) => key === b[index][0] && same(item, b[index][1]))
  }
  if (!same(value, expected)) throw new Error('Unsupported clarification component, binding or action.')
  return expected
}
