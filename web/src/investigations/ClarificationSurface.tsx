import { Component, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { A2uiSurface, createBinderlessComponentImplementation, useSignalValue } from '@a2ui/react/v0_9'
import { Catalog, ChildListSchema, MessageProcessor, componentId } from '@a2ui/web_core/v0_9'
import { z } from 'zod'
import { clarificationIdentity, scopeCatalogId, validateScopeOperations } from './surface'

const column = createBinderlessComponentImplementation({
  name: 'Column', schema: z.object({ children: ChildListSchema }).strict(),
}, ({ context, buildChild }) => <div>{(context.componentModel.properties.children as string[]).map(id => <div key={id}>{buildChild(id)}</div>)}</div>)
const text = createBinderlessComponentImplementation({
  name: 'Text', schema: z.object({ text: z.string().max(2000) }).strict(),
}, ({ context }) => <p>{String(context.componentModel.properties.text)}</p>)
const input = createBinderlessComponentImplementation({
  name: 'TextInput', schema: z.object({ label: z.literal('Investigation scope'), value: z.object({ path: z.literal('/answer') }).strict() }).strict(),
}, function ScopeInput({ context }) {
  const value = useSignalValue(context.dataContext.dataModel.getSignal<string>('/answer')) ?? ''
  return <label>Investigation scope<textarea value={value} maxLength={16384} rows={3}
    onChange={event => context.dataContext.set('/answer', event.target.value)} /></label>
})
const button = createBinderlessComponentImplementation({
  name: 'Button', schema: z.object({ child: componentId(),
    action: z.object({ event: z.object({ name: z.literal('submit_scope'),
      context: z.object({ answer: z.object({ path: z.literal('/answer') }).strict() }).strict() }).strict() }).strict() }).strict(),
}, ({ context, buildChild }) => <button type="button" onClick={() => {
  void context.dispatchAction({ event: { name: 'submit_scope', context: { answer: context.dataContext.dataModel.get<string>('/answer') } } }).catch(() => {})
}}>
  {buildChild(String(context.componentModel.properties.child))}
</button>)
const catalog = new Catalog(scopeCatalogId, 'v0.9', [column, text, input, button], [])

class SurfaceBoundary extends Component<{ children: ReactNode; fallback: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() { return this.state.failed ? this.props.fallback : this.props.children }
}

function Renderer({ activity, onAnswer, fallback }: { activity: Record<string, unknown>; onAnswer: (answer: string) => Promise<void>; fallback: ReactNode }) {
  const [runtime] = useState(() => {
    let processor: MessageProcessor<ReturnType<typeof createBinderlessComponentImplementation>> | undefined
    try {
      const identity = clarificationIdentity.parse(activity)
      const operations = validateScopeOperations(activity.operations, identity.id, identity.surface_revision, identity.question)
      processor = new MessageProcessor([catalog])
      processor.processMessages(operations)
      const surface = processor.getSurface(identity.id)
      if (!surface) throw new Error('Clarification surface was not created.')
      return { processor, surface }
    } catch { processor?.dispose(); return null }
  })
  useEffect(() => {
    const subscription = runtime?.surface.onAction.subscribe(async action => {
      if (action.name !== 'submit_scope' || action.surfaceId !== runtime.surface.id || action.sourceComponentId !== 'submit' ||
        Object.keys(action.context).some(key => key !== 'answer') || typeof action.context.answer !== 'string') {
        throw new Error('Unsupported clarification action.')
      }
      await onAnswer(action.context.answer)
    })
    return () => subscription?.unsubscribe()
  }, [runtime, onAnswer])
  useEffect(() => () => { runtime?.processor.dispose() }, [runtime])
  return runtime ? <SurfaceBoundary fallback={fallback}><A2uiSurface surface={runtime.surface} /></SurfaceBoundary> : fallback
}

export function ClarificationSurface({ activity, busy, onResolve, onCancel }: {
  activity: Record<string, unknown>; busy: boolean;
  onResolve: (payload: Record<string, unknown>) => Promise<void>; onCancel: (payload: Record<string, unknown>) => Promise<void>
}) {
  const [answer, setAnswer] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const identity = clarificationIdentity.safeParse(activity)
  if (!identity.success) return <p role="alert">Invalid scope clarification. Reopen this session to reload it.</p>
  const data = identity.data
  if (data.status !== 'pending') return <p>Scope clarification {data.status}.</p>
  const payload = { clarification_id: data.id, surface_revision: data.surface_revision }
  async function resolve(value: string) {
    if (busy || submitting) return
    if (!value.trim() || new TextEncoder().encode(value).length > 16384) { setError('Enter an investigation scope of at most 16 KiB.'); return }
    setSubmitting(true); setError('')
    try { await onResolve({ ...payload, answer: value.trim() }) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Scope could not be applied. Your answer is retained.') }
    finally { setSubmitting(false) }
  }
  const fallback = <form onSubmit={event => { event.preventDefault(); void resolve(answer) }}>
    <p>Plain form fallback: the dynamic surface could not be rendered.</p><p>{data.question}</p>
    <label>Investigation scope<textarea value={answer} maxLength={16384} rows={3} onChange={event => setAnswer(event.target.value)} /></label>
    <button disabled={!answer.trim()}>Apply scope and ask agent</button>
  </form>
  return <section className="investigation-review" aria-label="Scope clarification">
    <h2>Clarify investigation scope</h2>
    <fieldset disabled={busy || submitting}><Renderer key={`${data.id}-${data.surface_revision}`} activity={activity} onAnswer={resolve} fallback={fallback} /></fieldset>
    {error && <p role="alert">{error}</p>}
    <button disabled={busy || submitting} onClick={() => {
      setSubmitting(true)
      void onCancel(payload).catch(cause => setError(cause instanceof Error ? cause.message : 'Cancellation failed.')).finally(() => setSubmitting(false))
    }}>Cancel scope clarification</button>
  </section>
}
