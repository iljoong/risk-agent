import { useState } from 'react'
import type { ReactNode } from 'react'
import { EvidencePanel } from './EvidencePanel'
import { ReviewPanel } from './ReviewPanel'
import { StageEditor } from './StageEditor'
import { stages, stageNames } from './types'
import type { Investigation, OnCommand, Stage } from './types'
import './investigation.css'

export function InvestigationWorkbench({ snapshot, busy, onCommand, conversation, onDirection }: {
  snapshot: Investigation; busy: boolean; onCommand: OnCommand; conversation: ReactNode; onDirection: (text: string) => void
}) {
  const [selected, setSelected] = useState<Stage>(snapshot.current_stage)
  const [review, setReview] = useState(false)
  return <div className="investigation-page">
    <header className="investigation-heading"><div><h1>{snapshot.case_id} evidence desk</h1>
      <p>Demo connector / fictional records</p></div><div><span>Revision {snapshot.revision}</span>
      <button disabled={busy} onClick={() => { void onCommand('prepare', {}, snapshot.revision).catch(() => {}) }}>{snapshot.prepared ? 'Refresh demo evidence' : 'Prepare investigation'}</button>
      <button onClick={() => setReview(!review)}>Review & record</button></div></header>
    <p className="original-alert">Original alert {snapshot.original_alert.id}: <strong>{snapshot.original_alert.priority}</strong> / {snapshot.original_alert.trigger}</p>
    <nav className="workflow-stages" aria-label="Investigation workflow">{stages.map((stage, index) =>
      <button key={stage} aria-current={snapshot.current_stage === stage ? 'step' : undefined}
        aria-pressed={selected === stage} onClick={() => { setSelected(stage); setReview(false) }}>
        <span>{index + 1} {stageNames[stage]}</span><small>{snapshot.outputs[stage].needs_review ? 'Re-review required' : 'Acknowledged'}</small>
      </button>)}</nav>
    <EvidencePanel snapshot={snapshot} />
    {review && <ReviewPanel snapshot={snapshot} busy={busy} onCommand={onCommand} />}
    <div className="investigation-working"><StageEditor snapshot={snapshot} stage={selected} busy={busy} onCommand={onCommand} />
      <section className="investigation-conversation" aria-label="Investigation conversation"><h2>Challenge the interpretation</h2>
        <p>Direct the agent; proposals become stage output only after successful execution.</p>
        <button onClick={() => onDirection('Challenge the current interpretation. Separate supporting evidence, counterevidence and remaining gaps; propose a revised analysis with evidence references.')}>Draft a challenge</button>
        {conversation}
      </section></div>
  </div>
}
