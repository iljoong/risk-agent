import { useState } from 'react'
import type { Investigation, OnCommand, Stage } from './types'
import { stageNames } from './types'

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
  return <section className="investigation-output">
    <h2>{stageNames[stage]} output <small>Version {output.version}</small></h2>
    <p>{output.needs_review ? 'Re-review required' : 'Acknowledged'}; evidence: {output.evidence_ids.join(', ') || 'No references yet'}</p>
    <AmendmentEditor key={stage} value={output.text} revision={snapshot.revision} label="Stage output" reasonLabel="Reason for stage amendment"
      button="Apply stage amendment" maxLength={12000} busy={busy} onApply={(text, reason, revision) => onCommand('amend_output', { stage_id: stage, text, reason }, revision)} />
    <button disabled={busy || !output.needs_review} onClick={() => { void onCommand('acknowledge_stage', { stage_id: stage }, snapshot.revision).catch(() => {}) }}>Acknowledge this output</button>
    <button disabled={busy || snapshot.current_stage === stage} onClick={() => { void onCommand('select_stage', { stage_id: stage }, snapshot.revision).catch(() => {}) }}>Make current stage</button>
    <details><summary>Shared fact across all stages</summary>
      <AmendmentEditor value={snapshot.shared_facts.beneficiary_description} revision={snapshot.revision}
        label="Shared beneficiary description" reasonLabel="Reason for shared fact amendment" button="Apply shared fact amendment" maxLength={1000} busy={busy}
        onApply={(beneficiary_description, reason, revision) => onCommand('amend_fact', { beneficiary_description, reason }, revision)} />
    </details>
    <details><summary>Revision history ({snapshot.history.length})</summary>
      <ol>{snapshot.history.slice().reverse().map(item => <li key={item.revision}>
        Revision {item.revision}: {item.actor} / {item.action}{item.reason ? ` / ${item.reason}` : ''}
        {item.before && <details><summary>Previous text</summary><p className="preserve-lines">{item.before}</p></details>}
      </li>)}</ol>
    </details>
  </section>
}
