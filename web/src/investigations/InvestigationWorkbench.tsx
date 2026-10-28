import { useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import { PanelRight, X } from 'lucide-react'
import { SidebarResize } from '../SidebarResize'
import { EvidencePanel } from './EvidencePanel'
import { ReviewPanel } from './ReviewPanel'
import { StageEditor } from './StageEditor'
import { ClarificationSurface } from './ClarificationSurface'
import { stages, stageNames } from './types'
import type { Investigation, OnCommand, Stage } from './types'
import './investigation.css'

const views = ['Output', 'Evidence', 'Review'] as const

export function InvestigationWorkbench({ snapshot, busy, onCommand, conversation, onDirection, onOpenConversation }: {
  snapshot: Investigation; busy: boolean; onCommand: OnCommand; conversation: ReactNode; onDirection: (text: string) => void;
  onOpenConversation?: () => void
}) {
  const [selected, setSelected] = useState<Stage>(snapshot.current_stage)
  const [view, setView] = useState<typeof views[number]>('Output')
  const [chatOpen, setChatOpen] = useState(window.innerWidth > 1000)
  const [chatWidth, setChatWidth] = useState(380)
  function openConversation() {
    setChatOpen(true)
    onOpenConversation?.()
  }
  function direct(text: string) {
    onDirection(text)
    openConversation()
  }
  return <div className="investigation-layout" style={{ '--chat-width': `${chatWidth}px` } as CSSProperties}>
    <section className="investigation-page" aria-label="Investigation stage workspace">
    <header className="investigation-heading"><div><h1>{snapshot.case_id} evidence desk</h1>
      <p>Demo connector / fictional records</p></div><div><span>Revision {snapshot.revision}</span>
      <button disabled={busy} onClick={() => { void onCommand('prepare', {}, snapshot.revision).catch(() => {}) }}>{snapshot.prepared ? 'Refresh demo evidence' : 'Prepare investigation'}</button>
      <button onClick={() => setView('Review')}>Review & record</button>
      <button aria-label="Toggle conversation sidebar" aria-expanded={chatOpen} aria-controls="investigation-assistant"
        onClick={() => { if (chatOpen) setChatOpen(false); else openConversation() }}><PanelRight size={17} /> Chat</button></div></header>
    <p className="original-alert">Original alert {snapshot.original_alert.id}: <strong>{snapshot.original_alert.priority}</strong> / {snapshot.original_alert.trigger}</p>
    {!snapshot.prepared && <p className="start-prompt" role="note">
      {snapshot.original_alert.question && <><strong>Question to answer:</strong> {snapshot.original_alert.question} </>}
      No evidence has been collected. Clarify the scope if needed, then prepare the investigation.</p>}
    <nav className="workflow-stages" aria-label="Investigation workflow">{stages.map((stage, index) =>
      <button key={stage} aria-current={snapshot.current_stage === stage ? 'step' : undefined}
        aria-pressed={selected === stage} onClick={() => { setSelected(stage); setView('Output') }}>
        <span>{index + 1} {stageNames[stage]}</span><small>{stage === 'detect' && snapshot.original_alert.question ? 'Read-only' : snapshot.outputs[stage].needs_review ? 'Re-review required' : 'Acknowledged'}</small>
      </button>)}</nav>
    <div className="investigation-tabs" role="tablist" aria-label="Stage details view">
      {views.map((tab, index) => <button key={tab} role="tab" id={`investigation-tab-${tab}`} aria-controls={`investigation-panel-${tab}`}
        aria-selected={view === tab} tabIndex={view === tab ? 0 : -1} onClick={() => setView(tab)}
        onKeyDown={event => {
          let next: number
          if (event.key === 'ArrowRight') next = (index + 1) % views.length
          else if (event.key === 'ArrowLeft') next = (index + views.length - 1) % views.length
          else if (event.key === 'Home') next = 0
          else if (event.key === 'End') next = views.length - 1
          else return
          event.preventDefault()
          setView(views[next])
          document.getElementById(`investigation-tab-${views[next]}`)?.focus()
        }}>{tab}</button>)}
    </div>
    <div role="tabpanel" id="investigation-panel-Output" aria-labelledby="investigation-tab-Output" hidden={view !== 'Output'}>
      <StageEditor snapshot={snapshot} stage={selected} busy={busy} onCommand={onCommand} />
    </div>
    <div role="tabpanel" id="investigation-panel-Evidence" aria-labelledby="investigation-tab-Evidence" hidden={view !== 'Evidence'}>
      <EvidencePanel snapshot={snapshot} />
    </div>
    <div role="tabpanel" id="investigation-panel-Review" aria-labelledby="investigation-tab-Review" hidden={view !== 'Review'}>
      <ReviewPanel snapshot={snapshot} busy={busy} onCommand={onCommand} />
    </div>
    <div className="investigation-scope">
    <button disabled={busy || snapshot.clarification?.status === 'pending'} onClick={() => { void onCommand('request_clarification', {}, snapshot.revision).catch(() => {}) }}>Clarify investigation scope</button>
    {snapshot.clarification && <ClarificationSurface key={`${snapshot.clarification.id}-${snapshot.clarification.surface_revision}`}
      activity={snapshot.clarification} busy={busy}
      onResolve={payload => onCommand('resolve_clarification', payload, snapshot.revision)}
      onCancel={payload => onCommand('cancel_clarification', payload, snapshot.revision)} />}
    </div>
    <footer className="investigation-stage-status">Inspecting {stageNames[selected]}. Current stage: {stageNames[snapshot.current_stage]}.</footer>
    </section>
    {chatOpen && <SidebarResize label="Resize chat sidebar" controls="investigation-assistant" width={chatWidth}
      min={300} max={600} side="right" onResize={setChatWidth} />}
    <aside id="investigation-assistant" className={`investigation-conversation ${chatOpen ? 'conversation-open' : ''}`} aria-label="Investigation assistant">
      <header className="investigation-assistant-heading"><div><small>{snapshot.case_id} / {stageNames[selected]}</small><h2>Investigation assistant</h2></div>
        <button className="icon-button" aria-label="Close conversation sidebar" onClick={() => setChatOpen(false)}><X size={18} /></button></header>
        <p>Direct the agent; proposals become stage output only after successful execution.</p>
        <div className="investigation-prompts">
        <button onClick={() => direct('Challenge the current interpretation. Separate supporting evidence, counterevidence and remaining gaps; propose a revised analysis with evidence references.')}>Draft a challenge</button>
        <button onClick={() => direct('Check the supplied fictional policy requirements. Cite the applicable passages, distinguish policy from law, and propose any needed stage output corrections.')}>Draft a policy check</button>
        </div>
        {conversation}
    </aside>
  </div>
}
