import { useState } from 'react'
import type { Investigation, OnCommand } from './types'

export function ReviewPanel({ snapshot, busy, onCommand }: { snapshot: Investigation; busy: boolean; onCommand: OnCommand }) {
  const [rationale, setRationale] = useState(snapshot.review.rationale)
  const [copied, setCopied] = useState('')
  const stale = Object.values(snapshot.outputs).some(output => output.needs_review)
  return <section className="investigation-review">
    <h2>Review & record</h2>
    <p>Original AML priority: {snapshot.original_alert.priority}. Agent recommendations do not change this alert.</p>
    <p>Remaining gaps: invoice unavailable (GAP-01); previous case restricted (GAP-02). No external case decision is executed.</p>
    {stale && <p className="investigation-warning">Acknowledge all affected stage outputs before reviewing the note.</p>}
    <label>Analyst rationale<textarea value={rationale} onChange={event => setRationale(event.target.value)} maxLength={4000} rows={3} /></label>
    <button disabled={busy || stale || !rationale.trim()} onClick={() => { void onCommand('review_note', { rationale }, snapshot.revision).catch(() => {}) }}>Mark note reviewed</button>
    <button disabled={busy || !snapshot.review.reviewed} onClick={() => { void onCommand('prepare_note', {}, snapshot.revision).catch(() => {}) }}>Prepare case note</button>
    <p>External saving / approval: unconfirmed</p>
    {snapshot.review.prepared_note && <>
      <pre className="prepared-note">{snapshot.review.prepared_note}</pre>
      <button onClick={() => { void navigator.clipboard.writeText(snapshot.review.prepared_note!).then(() => setCopied('Copied. External saving / approval remains unconfirmed.')).catch(() => setCopied('Copy unavailable. Select and copy the note text.')) }}>Copy case note</button>
      <p role="status">{copied}</p>
    </>}
  </section>
}
