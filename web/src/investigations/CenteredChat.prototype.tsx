// Three throwaway centered-chat layouts on /?prototype=centered-chat&variant=A|B|C.
// Question: which right-hand stage layout best supports an uninterrupted conversation?
import { useRef, useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import { ArrowUp, Check, ChevronRight, FileText, GripHorizontal, GripVertical, History, MessageSquare, Moon, PanelLeft, PanelRight, Plus, Search, ShieldCheck, Sparkles, Sun, X } from 'lucide-react'
import type { Chat, ChatSummary, ModelChoice, Skill } from '../api/types'
import { PrototypeSwitcher } from '../PrototypeSwitcher.prototype'
import { stages, stageNames } from './types'
import type { Investigation, Stage } from './types'
import { prototypeCase, prototypeMessages, prototypeSkills, prototypeVariants } from './CenteredChat.prototype-data'
import type { PrototypeVariant } from './CenteredChat.prototype-data'
import './CenteredChat.prototype.css'

interface Props {
  snapshot: Investigation | null; chat: Chat | null; history: ChatSummary[];
  models: ModelChoice[]; skills: Skill[]; onOpen: (id: string) => void
}
type Message = { role: string; text: string }
type Tab = 'Output' | 'Evidence' | 'Review'
type Model = ReturnType<typeof usePrototype>

function usePrototype({ snapshot: source, chat, models, skills }: Props) {
  const [snapshot, setSnapshot] = useState(() => structuredClone(source ?? prototypeCase))
  const [stage, setStage] = useState<Stage>(snapshot.current_stage)
  const [drafts, setDrafts] = useState<Record<string, string>>(() => Object.fromEntries(stages.map(id => [id, snapshot.outputs[id].text])))
  const [reasons, setReasons] = useState<Record<string, string>>({})
  const [messages, setMessages] = useState<Message[]>(() => source && chat?.turns.length ? chat.turns.flatMap(turn => [
    { role: 'user', text: turn.request.message }, ...(turn.answer ? [{ role: 'assistant', text: turn.answer }] : []),
  ]) : prototypeMessages)
  const [text, setText] = useState('')
  const [tab, setTab] = useState<Tab>('Output')
  const [sourceId, setSourceId] = useState<string | null>(null)
  const [notice, setNotice] = useState('Read-only layout preview. All edits and replies stay in memory.')
  const [selectedSkill, setSelectedSkill] = useState('')
  const [model, setModel] = useState(models[0]?.id ?? 'preview')
  const [left, setLeft] = useState(220)
  const [right, setRight] = useState(380)
  const [dock, setDock] = useState(55)
  const [leftOpen, setLeftOpen] = useState(window.innerWidth > 1000)
  const [rightOpen, setRightOpen] = useState(window.innerWidth > 1000)
  const [dark, setDark] = useState(document.documentElement.dataset.theme === 'dark')
  const [variant, setVariant] = useState<PrototypeVariant>(() => {
    const key = new URLSearchParams(location.search).get('variant')
    return prototypeVariants.some(item => item.key === key) ? key as PrototypeVariant : 'A'
  })
  function changeVariant(value: PrototypeVariant) {
    const url = new URL(location.href)
    url.searchParams.set('variant', value)
    window.history.replaceState(null, '', url)
    setVariant(value)
  }
  function resize(side: 'left' | 'right', size: number) {
    const mobile = window.innerWidth <= 1000
    const other = side === 'left' ? (rightOpen ? right : 0) : (leftOpen ? left : 0)
    const maximum = mobile ? window.innerWidth - 32 : window.innerWidth - other - 456
    const minimum = side === 'left' ? 180 : 300
    const next = Math.max(Math.min(minimum, maximum), Math.min(maximum, Math.min(side === 'left' ? 360 : 600, size)))
    if (side === 'left') setLeft(next)
    else setRight(next)
  }
  function amend() {
    setSnapshot(previous => ({
      ...previous, revision: previous.revision + 1,
      outputs: Object.fromEntries(Object.entries(previous.outputs).map(([id, output]) => [id, {
        ...output, needs_review: true, ...(id === stage ? { text: drafts[stage], version: output.version + 1 } : {}),
      }])),
      review: { ...previous.review, reviewed: false, prepared_note: null },
    }))
    setNotice('Amendment preview applied locally. Reviews invalidated; no saved investigation was changed.')
  }
  function send() {
    if (!text.trim()) return
    setMessages(previous => [...previous, { role: 'user', text }, {
      role: 'assistant', text: `Prototype response only. No agent or tool was called.\n\nYour direction would use the current ${stageNames[stage]} output and saved amendments. Missing invoice and restricted prior-case contents remain unresolved.`,
    }])
    setText('')
    setNotice('Local message added. No inference, task submission or backend write.')
  }
  return {
    snapshot, stage, setStage, drafts, setDrafts, reasons, setReasons, messages, text, setText,
    tab, setTab, sourceId, setSourceId, notice, setNotice, selectedSkill, setSelectedSkill,
    model, setModel, models, skills, left, right, dock, setDock, leftOpen, setLeftOpen,
    rightOpen, setRightOpen, dark, setDark, variant, changeVariant, resize, amend, send,
    source: source ? 'Existing investigation snapshot (read-only)' : 'Packaged fictional CASE-1041 preview',
  }
}

function ResizeHandle({ label, value, onResize, side = 'left', horizontal = false }: {
  label: string; value: number; onResize: (value: number) => void; side?: 'left' | 'right'; horizontal?: boolean
}) {
  const origin = useRef<{ position: number; value: number } | null>(null)
  return <div className={`cp-resize ${horizontal ? 'cp-resize-horizontal' : ''}`} role="separator" tabIndex={0}
    aria-label={label} aria-orientation={horizontal ? 'horizontal' : 'vertical'} aria-valuenow={Math.round(value)}
    title={`${label}: drag or use arrow keys`} onPointerDown={event => {
      if (event.button !== 0) return
      event.preventDefault()
      event.currentTarget.focus()
      event.currentTarget.setPointerCapture(event.pointerId)
      origin.current = { position: horizontal ? event.clientY : event.clientX, value }
    }} onPointerMove={event => {
      if (!origin.current) return
      const delta = (horizontal ? event.clientY : event.clientX) - origin.current.position
      onResize(origin.current.value + delta * (horizontal ? 100 / (window.innerHeight - 144) : side === 'right' ? -1 : 1))
    }} onPointerUp={() => { origin.current = null }} onPointerCancel={() => { origin.current = null }}
    onLostPointerCapture={() => { origin.current = null }} onKeyDown={event => {
      const decrease = horizontal ? 'ArrowUp' : 'ArrowLeft'
      const increase = horizontal ? 'ArrowDown' : 'ArrowRight'
      if (event.key !== decrease && event.key !== increase) return
      event.preventDefault()
      onResize(value + (event.key === increase ? 1 : -1) * (horizontal ? 3 : side === 'right' ? -16 : 16))
    }}>
    {horizontal ? <GripHorizontal size={16} /> : <GripVertical size={16} />}
  </div>
}

function HistoryRail({ ui, history, onOpen }: { ui: Model; history: ChatSummary[]; onOpen: Props['onOpen'] }) {
  const [search, setSearch] = useState('')
  const sessions = history.filter(item => item.investigation && item.title.toLowerCase().includes(search.toLowerCase()))
  return <aside className={`cp-history ${ui.leftOpen ? 'cp-open' : ''}`} aria-label="Investigation sessions">
    <header><span>Investigation sessions</span><button aria-label="Close sessions" onClick={() => ui.setLeftOpen(false)}><X size={16} /></button></header>
    <button className="cp-primary cp-new" onClick={() => {
      ui.setNotice('This is a throwaway preview. Reload to reset it; creating a real investigation is disabled.')
    }}><Plus size={16} /> New investigation</button>
    <label className="cp-search"><Search size={15} /><input placeholder="Find a session" aria-label="Find a session" value={search} onChange={event => setSearch(event.target.value)} /></label>
    <nav>
      {'harbour components ltd / case-1041'.includes(search.toLowerCase()) && <button className="cp-session cp-active" onClick={() => ui.setNotice('Showing the current in-memory preview.')}><FileText size={16} /><span><strong>Harbour Components Ltd</strong><small>CASE-1041 / {stageNames[ui.snapshot.current_stage]}</small></span></button>}
      {sessions.filter(item => item.id !== ui.snapshot.chat_id).map(item => <button className="cp-session" key={item.id} onClick={() => { onOpen(item.id); if (window.innerWidth <= 1000) ui.setLeftOpen(false) }}>
        <History size={15} /><span><strong>{item.title}</strong><small>Open read-only snapshot</small></span>
      </button>)}
    </nav>
    <footer><span className="cp-status-dot" /> Local layout preview<p>No saved data is modified.</p></footer>
  </aside>
}

function StageTracker({ ui, vertical = false }: { ui: Model; vertical?: boolean }) {
  return <nav className={`cp-stages ${vertical ? 'cp-stages-vertical' : ''}`} aria-label="Investigation workflow">
    {stages.map((stage, index) => <button key={stage} aria-pressed={ui.stage === stage}
      aria-current={ui.snapshot.current_stage === stage ? 'step' : undefined}
      onClick={() => { ui.setStage(stage); ui.setTab('Output') }}>
      <span className="cp-stage-number">{index + 1}</span><span>{stageNames[stage]}{vertical && <small>{ui.snapshot.current_stage === stage ? 'Current stage' : ui.snapshot.outputs[stage].needs_review ? 'Re-review required' : 'Acknowledged'}</small>}</span>
      {vertical && <ChevronRight size={14} />}
    </button>)}
  </nav>
}

function ChatThread({ ui, compact = false }: { ui: Model; compact?: boolean }) {
  const end = useRef<HTMLDivElement>(null)
  return <>
    <div className="cp-thread" aria-label="Investigation conversation">
      <div className="cp-thread-inner">
        <p className="cp-conversation-context"><ShieldCheck size={14} /> Fictional case / evidence and drafts, not an approved decision</p>
        {ui.messages.map((message, index) => <article className={`cp-message cp-${message.role}`} key={index}>
          <div className="cp-message-label">{message.role === 'assistant' ? <Sparkles size={16} /> : <span className="cp-you">A</span>}<strong>{message.role === 'assistant' ? 'RCI Agent' : 'You'}</strong></div>
          <p>{message.text}</p>
          {message.role === 'assistant' && index === 1 && <div className="cp-citations">
            {['E-01', 'E-03', 'GAP-01'].map(id => <button key={id} onClick={() => {
              const evidence = ui.snapshot.evidence.find(item => item.id === id)
              ui.setSourceId(evidence?.source_ids[0] ?? null); ui.setTab('Evidence'); ui.setRightOpen(true)
            }}><FileText size={12} />{id}</button>)}
            <button onClick={() => { ui.setRightOpen(true); ui.setTab('Output') }}>Inspect stage output <ChevronRight size={13} /></button>
          </div>}
        </article>)}
        <div ref={end} />
      </div>
    </div>
    <div className="cp-compose-area">
      {!compact && <div className="cp-directions">
        {['Challenge this concern', 'Check policy requirements'].map(label => <button key={label} onClick={() => ui.setText(label === 'Challenge this concern'
          ? 'Challenge the interpretation. Compare supporting evidence, counterevidence and remaining gaps.'
          : 'Check the supplied fictional policy requirements. Keep policy, law and approval status distinct.')}>{label}<ChevronRight size={13} /></button>)}
      </div>}
      <form className="cp-composer" onSubmit={event => {
        event.preventDefault(); ui.send(); requestAnimationFrame(() => end.current?.scrollIntoView({ block: 'nearest' }))
      }}>
        <label className="cp-visually-hidden" htmlFor={`cp-message-${ui.variant}`}>Direct this investigation</label>
        <textarea id={`cp-message-${ui.variant}`} value={ui.text} onChange={event => ui.setText(event.target.value)} rows={2}
          placeholder="Direct the investigation. Ask a question or challenge a finding..."
          onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); event.currentTarget.form?.requestSubmit() } }} />
        <div><select aria-label="Skill" value={ui.selectedSkill} onChange={event => ui.setSelectedSkill(event.target.value)}>
          <option value="">Skills</option>{(ui.skills.length ? ui.skills.map(item => item.id) : prototypeSkills).map(id => <option key={id} value={id}>{id}</option>)}
        </select><span>Preview only</span><button className="cp-primary" aria-label="Send preview message" disabled={!ui.text.trim()}><ArrowUp size={18} /></button></div>
      </form>
      <p className="cp-disclaimer">No inference or external action. Original alert priority stays {ui.snapshot.original_alert.priority}.</p>
    </div>
  </>
}

function OutputEditor({ ui }: { ui: Model }) {
  const output = ui.snapshot.outputs[ui.stage]
  return <section className="cp-output" aria-label="Stage output editor">
    <div className="cp-section-title"><h3>{stageNames[ui.stage]} output</h3><span>v{output.version}</span></div>
    <p className="cp-muted">Editable analyst draft / {output.needs_review ? 're-review required' : 'acknowledged'}</p>
    <label>Stage output<textarea rows={9} value={ui.drafts[ui.stage]} onChange={event => ui.setDrafts({ ...ui.drafts, [ui.stage]: event.target.value })} /></label>
    <label>Reason for amendment<input value={ui.reasons[ui.stage] ?? ''} onChange={event => ui.setReasons({ ...ui.reasons, [ui.stage]: event.target.value })} placeholder="What changed, and why?" /></label>
    <button className="cp-primary" disabled={ui.drafts[ui.stage] === output.text || !ui.drafts[ui.stage].trim() || !ui.reasons[ui.stage]?.trim()} onClick={ui.amend}>Preview amendment</button>
    <p className="cp-muted">Amendments remain local in this prototype. All outputs require renewed review.</p>
    <details><summary>Shared finding</summary><p>{ui.snapshot.shared_facts.beneficiary_description}</p></details>
  </section>
}

function EvidenceInspector({ ui }: { ui: Model }) {
  const source = ui.snapshot.sources.find(item => item.source_id === ui.sourceId)
  return <section className="cp-evidence" aria-label="Stage evidence">
    <h3>Source-linked evidence</h3>
    <p className="cp-muted">Selected records only. Inaccessible sources stay inaccessible.</p>
    {ui.snapshot.evidence.map(item => <article key={item.id} className="cp-evidence-item">
      <small>{item.id} / {item.kind}</small><h4>{item.title}</h4><p>{item.text}</p>
      <div>{item.source_ids.map(id => <button key={id} onClick={() => ui.setSourceId(id)}><FileText size={12} />{id}</button>)}</div>
    </article>)}
    {source && <div className="cp-source" aria-label={`Source ${source.source_id}`}>
      <div className="cp-section-title"><strong>{source.source_id}</strong><button aria-label="Close source" onClick={() => ui.setSourceId(null)}><X size={16} /></button></div>
      <h4>{source.title}</h4><p>{source.status} / {source.version ?? 'No version available'}</p><p>{source.coverage}</p>
      <small>Snapshot: {source.snapshot_at ?? 'unavailable'}</small>
    </div>}
    <details><summary>Transaction timeline</summary><ol className="cp-transactions">{ui.snapshot.transactions.map(item => <li key={item.id}>
      <time>{item.timestamp.slice(11, 16)}</time><span>{item.counterparty}<small>{item.id}</small></span><strong>{new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', maximumFractionDigits: 0 }).format(item.amount_gbp)}</strong>
    </li>)}</ol></details>
    <div className="cp-warning">Invoice missing [GAP-01]. Previous case restricted [GAP-02]. Timing does not establish intent or fund lineage.</div>
  </section>
}

function ReviewSummary({ ui }: { ui: Model }) {
  return <section className="cp-review" aria-label="Review status"><h3>Before a recommendation</h3>
    <p>Separate facts, interpretations and uncertainty.</p>
    <ul><li>Corroborate the supplier invoice.</li><li>Request authorized prior-case access.</li><li>Validate the applicable policy and approval path.</li><li>Review amended outputs and record analyst rationale.</li></ul>
    <div className="cp-warning">Not ready for approval. Required evidence remains unresolved.</div>
    <p className="cp-muted">Original {ui.snapshot.original_alert.priority} priority is unchanged. No case is closed, no note is exported, and external saving / approval remains unconfirmed.</p>
  </section>
}

function RailHeader({ ui, children }: { ui: Model; children?: ReactNode }) {
  return <header className="cp-rail-heading"><div><small>Stage {stages.indexOf(ui.stage) + 1} of 6</small><h2>{stageNames[ui.stage]}</h2></div>
    {children}<button aria-label="Close stage details" onClick={() => ui.setRightOpen(false)}><PanelRight size={17} /></button></header>
}
function LeftResize({ ui }: { ui: Model }) {
  return ui.leftOpen ? <ResizeHandle label="Resize sessions sidebar" value={ui.left} onResize={size => ui.resize('left', size)} /> : null
}
function RightResize({ ui }: { ui: Model }) {
  return ui.rightOpen ? <ResizeHandle label="Resize stage sidebar" side="right" value={ui.right} onResize={size => ui.resize('right', size)} /> : null
}
function CaseHeading({ ui }: { ui: Model }) {
  return <header className="cp-case-heading"><div><small>{ui.snapshot.case_id} / fictional investigation</small><h1>Harbour Components Ltd</h1></div>
    <span className="cp-priority">Original alert: {ui.snapshot.original_alert.priority}</span></header>
}

export function VariantA({ ui, history, onOpen }: { ui: Model; history: ChatSummary[]; onOpen: Props['onOpen'] }) {
  return <div className="cp-body cp-variant-a">
    <HistoryRail ui={ui} history={history} onOpen={onOpen} /><LeftResize ui={ui} />
    <main className="cp-main"><CaseHeading ui={ui} /><StageTracker ui={ui} /><ChatThread ui={ui} /></main>
    <RightResize ui={ui} />
    <aside className={`cp-inspector ${ui.rightOpen ? 'cp-open' : ''}`} aria-label="Stage details">
      <RailHeader ui={ui} /><div className="cp-tabs" role="tablist" aria-label="Stage details view">
        {(['Output', 'Evidence', 'Review'] as const).map(tab => <button key={tab} role="tab" id={`cp-tab-${tab}`} aria-controls="cp-details-panel" aria-selected={ui.tab === tab} onClick={() => ui.setTab(tab)}>{tab}</button>)}
      </div>
      <div className="cp-rail-scroll" id="cp-details-panel" role="tabpanel" aria-labelledby={`cp-tab-${ui.tab}`}>
        {ui.tab === 'Output' ? <OutputEditor ui={ui} /> : ui.tab === 'Evidence' ? <EvidenceInspector ui={ui} /> : <ReviewSummary ui={ui} />}
      </div>
      <footer className="cp-rail-footer">Inspecting {stageNames[ui.stage]}. Current: {stageNames[ui.snapshot.current_stage]}.</footer>
    </aside>
  </div>
}

export function VariantB({ ui, history, onOpen }: { ui: Model; history: ChatSummary[]; onOpen: Props['onOpen'] }) {
  return <div className="cp-body cp-variant-b">
    <HistoryRail ui={ui} history={history} onOpen={onOpen} /><LeftResize ui={ui} />
    <main className="cp-main"><CaseHeading ui={ui} /><div className="cp-brief-line"><MessageSquare size={15} />Conversation stays in focus<span>{stageNames[ui.snapshot.current_stage]} in progress</span></div><ChatThread ui={ui} compact /></main>
    <RightResize ui={ui} />
    <aside className={`cp-inspector ${ui.rightOpen ? 'cp-open' : ''}`} aria-label="Stage details">
      <RailHeader ui={ui} /><div className="cp-rail-scroll"><h3 className="cp-outline-title">Workflow outline</h3><StageTracker ui={ui} vertical />
        <div className="cp-outline-output"><OutputEditor ui={ui} /></div>
        <details open={ui.tab === 'Evidence'} onToggle={event => { if (event.currentTarget.open) ui.setTab('Evidence') }}><summary>Evidence and source context</summary><EvidenceInspector ui={ui} /></details>
        <details open={ui.tab === 'Review'} onToggle={event => { if (event.currentTarget.open) ui.setTab('Review') }}><summary>Review requirements</summary><ReviewSummary ui={ui} /></details>
      </div>
    </aside>
  </div>
}

export function VariantC({ ui, history, onOpen }: { ui: Model; history: ChatSummary[]; onOpen: Props['onOpen'] }) {
  return <div className="cp-body cp-variant-c">
    <HistoryRail ui={ui} history={history} onOpen={onOpen} /><LeftResize ui={ui} />
    <main className="cp-main"><CaseHeading ui={ui} /><div className="cp-case-ribbon"><span>Stage {stages.indexOf(ui.stage) + 1} / {stageNames[ui.stage]}</span><button onClick={() => { ui.setRightOpen(true); ui.setTab('Review') }}>Review requirements <ChevronRight size={14} /></button></div>
      <ChatThread ui={ui} /><div className="cp-chat-footnote"><ShieldCheck size={14} />The conversation is separate from the editable case record.</div></main>
    <RightResize ui={ui} />
    <aside className={`cp-inspector cp-split-dock ${ui.rightOpen ? 'cp-open' : ''}`} aria-label="Stage details">
      <RailHeader ui={ui} /><label className="cp-stage-select">Inspect stage<select aria-label="Inspect stage" value={ui.stage} onChange={event => ui.setStage(event.target.value as Stage)}>
        {stages.map((stage, index) => <option key={stage} value={stage}>{index + 1}. {stageNames[stage]}</option>)}
      </select></label>
      <div className="cp-dock-top" style={{ flex: `0 0 ${ui.dock}%` }}><OutputEditor ui={ui} /></div>
      <ResizeHandle label="Resize output and evidence dock" horizontal value={ui.dock} onResize={size => ui.setDock(Math.max(25, Math.min(68, size)))} />
      <div className="cp-dock-bottom"><div className="cp-dock-caption"><strong>{ui.tab === 'Review' ? 'Review requirements' : 'Evidence alongside the draft'}</strong><button onClick={() => ui.setTab(ui.tab === 'Review' ? 'Evidence' : 'Review')}>{ui.tab === 'Review' ? 'Evidence' : 'Review'}</button></div>
        {ui.tab === 'Review' ? <ReviewSummary ui={ui} /> : <EvidenceInspector ui={ui} />}
      </div>
    </aside>
  </div>
}

export default function CenteredChatPrototype(props: Props) {
  const ui = usePrototype(props)
  const Variant = ui.variant === 'B' ? VariantB : ui.variant === 'C' ? VariantC : VariantA
  return <div className={`cp-shell ${ui.leftOpen ? 'cp-left-open' : ''} ${ui.rightOpen ? 'cp-right-open' : ''}`} data-mode={ui.dark ? 'dark' : 'light'}
    style={{ '--proto-left': `${ui.left}px`, '--proto-right': `${ui.right}px` } as CSSProperties}>
    <header className="cp-topbar">
      <div className="cp-brand"><span><ShieldCheck size={21} /></span><strong>RCI Agent</strong></div>
      <button className="cp-icon" aria-label="Toggle sessions sidebar" aria-expanded={ui.leftOpen} onClick={() => { ui.setLeftOpen(!ui.leftOpen); if (window.innerWidth <= 1000) ui.setRightOpen(false) }}><PanelLeft size={18} /></button>
      <span className="cp-topbar-caption">Investigation workspace</span>
      <div className="cp-topbar-actions"><span className="cp-prototype-badge">Layout prototype</span>
        <select aria-label="Preview model" value={ui.model} onChange={event => ui.setModel(event.target.value)}>{[{ id: 'preview', label: 'No inference / preview' }, ...ui.models].map(item => <option key={item.id} value={item.id}>{item.label}</option>)}</select>
        <button className="cp-icon" aria-label="Dark mode" aria-pressed={ui.dark} onClick={() => ui.setDark(!ui.dark)}>{ui.dark ? <Sun size={18} /> : <Moon size={18} />}</button>
        <button className="cp-icon" aria-label="Toggle stage sidebar" aria-expanded={ui.rightOpen} onClick={() => { ui.setRightOpen(!ui.rightOpen); if (window.innerWidth <= 1000) ui.setLeftOpen(false) }}><PanelRight size={18} /></button>
      </div>
    </header>
    <Variant ui={ui} history={props.history} onOpen={props.onOpen} />
    <div className="cp-notice" role="status"><Check size={12} /><span>{ui.notice}</span></div>
    <PrototypeSwitcher variant={ui.variant} onChange={ui.changeVariant} state={{
      variant: ui.variant, source: ui.source, viewedStage: ui.stage, currentStage: ui.snapshot.current_stage,
      localRevision: ui.snapshot.revision, leftWidth: ui.left, rightWidth: ui.right, dockPercent: ui.dock,
      leftOpen: ui.leftOpen, rightOpen: ui.rightOpen, theme: ui.dark ? 'dark' : 'light', tab: ui.tab,
      sourceId: ui.sourceId, selectedSkill: ui.selectedSkill, model: ui.model, drafts: ui.drafts, reasons: ui.reasons,
      messages: ui.messages, composerText: ui.text, backendWrites: 0,
    }} />
  </div>
}
