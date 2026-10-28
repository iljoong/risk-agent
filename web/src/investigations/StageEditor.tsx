import { useState } from 'react'
import type { Investigation, OnCommand, RevisionRecord, Stage } from './types'
import { stageNames, stages } from './types'
import { investigations } from './client'

function AmendmentEditor({ value, revision, label, reasonLabel, button, maxLength, busy, onApply }: {
  value: string; revision: number; label: string; reasonLabel: string; button: string; maxLength: number;
  busy: boolean; onApply: (text: string, reason: string, revision: number) => Promise<void>
}) {
  const [text, setText] = useState(value)
  const [reason, setReason] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [base, setBase] = useState({ value, revision })
  // Retain a dirty draft and its original revision when another tab publishes.
  const dirty = text !== base.value
  if (!dirty && (base.value !== value || base.revision !== revision)) {
    setBase({ value, revision })
    if (text !== value) setText(value)
  }
  return <form className="investigation-form" onSubmit={event => {
    event.preventDefault(); setSaving(true); setError('')
    void onApply(text, reason, base.revision).then(() => {
      setBase({ value: text, revision: base.revision + 1 })
      setReason('')
    }).catch(cause => setError(cause instanceof Error ? cause.message : 'Amendment failed. Your draft is retained.'))
      .finally(() => setSaving(false))
  }}>
    <label>{label}<textarea value={text} onChange={event => setText(event.target.value)} maxLength={maxLength} rows={6} /></label>
    <label>{reasonLabel}<input value={reason} onChange={event => setReason(event.target.value)} maxLength={2000} /></label>
    {dirty && revision !== base.revision && <p className="investigation-warning">A newer revision is available. Your draft is retained; compare it with the latest saved output before reapplying.</p>}
    {error && <p role="alert">{error}</p>}
    {error && revision !== base.revision && <details><summary>Compare with latest saved output</summary><p className="preserve-lines">{value}</p>
      <button type="button" onClick={() => { setBase({ value, revision }); setError('') }}>Keep draft and use latest revision</button></details>}
    <button className="investigation-primary" disabled={busy || saving || !dirty || !text.trim() || !reason.trim()}>{button}</button>
  </form>
}

export function StageEditor({ snapshot, stage, busy, onCommand }: {
  snapshot: Investigation; stage: Stage; busy: boolean; onCommand: OnCommand
}) {
  const output = snapshot.outputs[stage]
  if (stage === 'detect' && snapshot.original_alert.question) {
    const alert = snapshot.original_alert
    return <section className="investigation-output">
      <h2>{stageNames.detect} <small>Read-only</small></h2>
      <p>Alert {alert.id}: <strong>{alert.priority}</strong> priority. {alert.trigger}.</p>
      <p>Detection came from the existing fictional AML system, so nothing needs review here. The original priority cannot be changed.</p>
      <button disabled={busy || snapshot.current_stage === 'investigate'} onClick={() => { void onCommand('select_stage', { stage_id: 'investigate' }, snapshot.revision).catch(() => {}) }}>Continue to Investigate</button>
    </section>
  }
  return <section className="investigation-output">
    <h2>{stageNames[stage]} output <small>Version {output.version}</small></h2>
    <p>{output.needs_review ? 'Re-review required' : 'Acknowledged'}; evidence: {output.evidence_ids.join(', ') || 'No references yet'}</p>
    {stages.map(id => <div key={id} hidden={id !== stage}>
      <AmendmentEditor value={snapshot.outputs[id].text} revision={snapshot.revision} label="Stage output" reasonLabel="Reason for stage amendment"
        button="Apply stage amendment" maxLength={12000} busy={busy} onApply={(text, reason, revision) => onCommand('amend_output', { stage_id: id, text, reason }, revision)} />
    </div>)}
    <button disabled={busy || !output.needs_review} onClick={() => { void onCommand('acknowledge_stage', { stage_id: stage }, snapshot.revision).catch(() => {}) }}>Acknowledge this output</button>
    <button disabled={busy || snapshot.current_stage === stage} onClick={() => { void onCommand('select_stage', { stage_id: stage }, snapshot.revision).catch(() => {}) }}>Make current stage</button>
    <details><summary>Shared fact across all stages</summary>
      <AmendmentEditor value={snapshot.shared_facts.beneficiary_description} revision={snapshot.revision}
        label="Shared beneficiary description" reasonLabel="Reason for shared fact amendment" button="Apply shared fact amendment" maxLength={1000} busy={busy}
        onApply={(beneficiary_description, reason, revision) => onCommand('amend_fact', { beneficiary_description, reason }, revision)} />
    </details>
    <RevisionHistory key={snapshot.revision} chatId={snapshot.chat_id} />
  </section>
}

function RevisionHistory({ chatId }: { chatId: string }) {
  const [records, setRecords] = useState<RevisionRecord[] | null>(null)
  const [before, setBefore] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  async function load(cursor?: number) {
    setLoading(true); setError('')
    try {
      const page = await investigations.history(chatId, cursor)
      setRecords(previous => cursor === undefined ? page.records : [...(previous ?? []), ...page.records])
      setBefore(page.next_before)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'History could not be loaded.') }
    finally { setLoading(false) }
  }
  return <details aria-label="Investigation revision history" onToggle={event => {
    if (event.currentTarget.open && records === null && !loading) void load()
  }}><summary>Revision history</summary>
      {error && <p role="alert">{error}<button onClick={() => { void load() }}>Reload history</button></p>}
      <ol>{records?.map(item => <li key={item.revision}>
        Revision {item.revision}: {item.actor} / {item.action}{item.reason ? ` / ${item.reason}` : ''}
        {item.before && <details><summary>Previous text</summary><p className="preserve-lines">{item.before}</p></details>}
        {item.after && <details><summary>Saved text</summary><p className="preserve-lines">{item.after}</p></details>}
      </li>)}</ol>
      {loading && <p role="status">Loading revision history...</p>}
      {before !== null && <button disabled={loading} onClick={() => { void load(before) }}>Load older revisions</button>}
    </details>
}
