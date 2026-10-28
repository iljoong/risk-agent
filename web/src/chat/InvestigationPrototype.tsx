// Throwaway: compare three investigation layouts on /?prototype=investigation&variant=A|B|C.
// React owns the workflow; agent replies and shared-state updates are local simulations, not AG-UI/A2UI.
import { useCallback, useEffect, useState } from 'react'
import {
  ArrowDown, ArrowRight, ArrowUp, Check, ChevronRight, Clipboard, FileText,
  FlaskConical, History, PanelLeft, Plus, RotateCcw, ShieldCheck, Sparkles, X,
} from 'lucide-react'
import { PrototypeSwitcher } from './PrototypeSwitcher'
import type { PrototypeVariant } from './PrototypeSwitcher'
import './investigation-prototype.css'

const stages = ['Detect', 'Investigate', 'Gather Evidence', 'Analyze', 'Human Review', 'Decision']
const initialOutputs = [
  'ALT-2041 / CASE-1041. Original AML trigger: rapid movement of funds to a newly observed beneficiary. Original priority: High.',
  'Assess the payment pattern and plausible supplier explanation using the supplied fictional ledger, KYC, available history and applicable demonstration policies.',
  'E-01: TX-781 through TX-784, SRC-01. E-02: available 90-day history, SRC-03. E-03: KYC-1041-v3 and TX-701/TX-702. E-04: invoice reference MS-882. GAP-01: missing invoice. GAP-02: restricted CASE-0812.',
  'Timing and amounts warrant assessment, not a finding of wrongdoing. Supplier payments fit the business profile [E-03]. Invoice purpose remains unverified [E-04, GAP-01]. Inaccessible case contents are not adverse evidence [GAP-02].',
  'Validate material claims and the beneficiary description. Preserve counterevidence and acknowledge both gaps. Record an analyst rationale before preparing a reviewed note.',
  'Proposed disposition: refer for further investigation through the existing approval workflow. No closure, escalation approval, filing or account restriction is performed here.',
]
const transactions = [
  ['09:12', 'TX-781', 'Alder Industrial', '+18,000', 'Order H-441'],
  ['09:31', 'TX-782', 'Beacon Assembly', '+16,000', 'Order H-442'],
  ['09:54', 'TX-783', 'Cedar Parts', '+14,000', 'Order H-443'],
  ['10:08', 'TX-784', 'Meridian Supply', '-45,500', 'Invoice MS-882'],
]
const evidence = [
  { id: 'E-01', kind: 'Supports concern', title: 'Closely timed movement', source: 'SRC-01 / TX-781 through TX-784', text: 'GBP 48,000 incoming; GBP 45,500 outgoing within 56 minutes. Timing does not establish fund lineage or intent.' },
  { id: 'E-02', kind: 'Supports concern', title: 'Beneficiary history', source: 'SRC-03 / available 90-day history', text: 'Meridian Supply is absent from the available history. Stipulated scenario fact, not derivable from the four displayed transactions.' },
  { id: 'E-03', kind: 'Counterevidence', title: 'Plausible trade activity', source: 'SRC-02 / KYC-1041-v3; SRC-01 / TX-701, TX-702', text: 'Supplier payments fit the recorded business profile. Historical payments were GBP 22,000 and GBP 27,500; neither verifies this payment.' },
  { id: 'E-04', kind: 'Alternative explanation', title: 'Invoice settlement reference', source: 'SRC-01 / TX-784', text: 'The reference reads "Invoice MS-882". A payment reference is not corroboration of an invoice or business purpose.' },
  { id: 'GAP-01', kind: 'Missing information', title: 'Invoice not supplied', source: 'SRC-07 / MS-882', text: 'Supporting invoice unavailable. No completed corroboration check is claimed.' },
  { id: 'GAP-02', kind: 'Restricted source', title: 'Prior case inaccessible', source: 'SRC-04 / CASE-0812', text: 'Request authorized access or specialist review. Do not infer adverse content or bypass restrictions.' },
]
const policies = [
  ['G-AML-07 / 4.2', 'Assess supporting and contradicting evidence; record material information gaps.'],
  ['G-AML-07 / 5.1', 'Agent-generated findings are drafts requiring investigator validation.'],
  ['G-AML-07 / 6.3', 'Record disposition rationale and evidence references; retain human approvals.'],
  ['L-01 / 2.4', 'Corroborate the newly observed beneficiary business purpose before recommending closure.'],
]
type Revision = { sequence: number; stage: number; before: string; after: string; rationale: string }
type Message = { role: 'agent' | 'analyst'; text: string; revision: number }
type View = 'stage' | 'evidence' | 'policy' | 'record'
const variantKeys: PrototypeVariant[] = ['A', 'B', 'C']

export default function InvestigationPrototype() {
  const [variant, setVariant] = useState<PrototypeVariant>(() => {
    const key = new URLSearchParams(window.location.search).get('variant')
    return variantKeys.find(item => item === key) ?? 'A'
  })
  const [selected, setSelected] = useState(1)
  const [current, setCurrent] = useState(1)
  const [outputs, setOutputs] = useState(initialOutputs)
  const [versions, setVersions] = useState([1, 1, 1, 1, 1, 1])
  const [stale, setStale] = useState<number[]>([])
  const [reviewedStages, setReviewedStages] = useState<number[]>([])
  const [sequence, setSequence] = useState(1)
  const [revisions, setRevisions] = useState<Revision[]>([])
  const [events, setEvents] = useState<string[]>([])
  const [beneficiary, setBeneficiary] = useState('Beneficiary not observed in the available 90-day history')
  const [beneficiaryEdit, setBeneficiaryEdit] = useState(beneficiary)
  const [draft, setDraft] = useState(outputs[selected])
  const [rationale, setRationale] = useState('')
  const [reviewRationale, setReviewRationale] = useState('')
  const [reviewed, setReviewed] = useState(false)
  const [prepared, setPrepared] = useState(false)
  const [record, setRecord] = useState<string | null>(null)
  const [view, setView] = useState<View>('stage')
  const [source, setSource] = useState<string | null>(null)
  const [sidebar, setSidebar] = useState(window.innerWidth > 800)
  const [notice, setNotice] = useState('')
  const [prompt, setPrompt] = useState('')
  const [messages, setMessages] = useState<Message[]>([{
    role: 'agent', revision: 1,
    text: 'This is a fictional investigation preview. Prepare the investigation to simulate the evidence-gathering handoff, or inspect and amend any stage. No sources have been retrieved live.',
  }])

  const chooseVariant = useCallback((key: PrototypeVariant) => {
    const url = new URL(window.location.href)
    url.searchParams.set('variant', key)
    window.history.replaceState(null, '', url)
    setVariant(key)
  }, [])
  useEffect(() => {
    function restoreVariant() {
      const key = new URLSearchParams(window.location.search).get('variant')
      setVariant(variantKeys.find(item => item === key) ?? 'A')
    }
    window.addEventListener('popstate', restoreVariant)
    return () => window.removeEventListener('popstate', restoreVariant)
  }, [])

  function selectStage(index: number) {
    if ((draft !== outputs[selected] || beneficiaryEdit !== beneficiary) && !window.confirm('Discard the unsaved stage edit?')) return false
    setSelected(index)
    setDraft(outputs[index])
    setBeneficiaryEdit(beneficiary)
    setRationale('')
    setView('stage')
    return true
  }
  function invalidate(indices: number[]) {
    setStale(previous => [...new Set([...previous, ...indices])])
    setReviewedStages(previous => previous.filter(index => !indices.includes(index)))
    setReviewed(false)
    setRecord(null)
  }
  function amendOutput() {
    const changedFact = beneficiaryEdit.trim() !== beneficiary
    const changedOutput = draft.trim() !== outputs[selected]
    if (!rationale.trim() || (!changedFact && !changedOutput)) return
    const next = sequence + 1
    const affected = stages.map((_, index) => index).filter(index => changedFact || index > selected)
    const before = changedFact ? `${outputs[selected]}\nShared fact: ${beneficiary}` : outputs[selected]
    const after = changedFact ? `${draft.trim()}\nShared fact: ${beneficiaryEdit.trim()}` : draft.trim()
    setOutputs(previous => previous.map((item, index) => index === selected ? draft.trim() : item))
    setDraft(draft.trim())
    setVersions(previous => previous.map((item, index) => index === selected ? item + 1 : item))
    setBeneficiary(beneficiaryEdit.trim())
    setBeneficiaryEdit(beneficiaryEdit.trim())
    setRevisions(previous => [...previous, { sequence: next, stage: selected, before, after, rationale: rationale.trim() }])
    setSequence(next)
    invalidate(affected)
    setReviewedStages(previous => previous.filter(index => index !== selected))
    setEvents(previous => [...previous, `r${next}: Analyst amended ${stages[selected]}; dependent outputs require re-review. Rationale: ${rationale.trim()}`])
    setNotice(`Applied to shared workflow r${next}. Dependent context and the note now use your amendment; historical messages retain their original revision.`)
    setRationale('')
  }
  function prepareInvestigation() {
    if (!selectStage(2)) return
    setPrepared(true)
    setCurrent(2)
    setEvents(previous => [...previous, `r${sequence}: Simulated preparation using supplied fixtures only. Invoice missing; previous case restricted.`])
    setMessages(previous => [...previous, {
      role: 'agent', revision: sequence,
      text: `Simulated preparation: the supplied evidence pack contains E-01 through E-04, a missing invoice (GAP-01) and inaccessible case contents (GAP-02). Current shared description: ${beneficiary}. No live source retrieval occurred.`,
    }])
  }
  function agentReply(question: string, action: 'challenge' | 'policy' | 'custom') {
    if (!question.trim()) return
    if (action === 'challenge' && selected === 3 && draft !== outputs[selected]) {
      setNotice('Apply or discard your unsaved Analyze output before requesting a simulated update.')
      return
    }
    const context = outputs.map((output, index) => `${stages[index]}: ${output}`).join('\n\n')
    let response: string
    if (action === 'challenge') {
      response = `Supplier payments fit KYC-1041-v3 and the historical TX-701/TX-702 examples [E-03]. "Invoice MS-882" offers a possible explanation, not corroboration [E-04]. ${beneficiary}. Neither the invoice nor restricted case has been verified.`
      const next = sequence + 1
      const updated = `${outputs[3]}\n\nSimulated counterevidence update: ${response}`
      setOutputs(previous => previous.map((item, index) => index === 3 ? updated : item))
      if (selected === 3) setDraft(updated)
      setVersions(previous => previous.map((item, index) => index === 3 ? item + 1 : item))
      setRevisions(previous => [...previous, { sequence: next, stage: 3, before: outputs[3], after: updated, rationale: question }])
      setSequence(next)
      invalidate([3, 4, 5])
      setEvents(previous => [...previous, `r${next}: Simulated agent added counterevidence to Analyze. Human Review and Decision require re-review.`])
    } else if (action === 'policy') {
      response = 'Fictional G-AML-07 v3 sections 4.2, 5.1 and 6.3 require balanced evidence, human validation and rationale. L-01 v2 section 2.4 calls for corroborating business purpose before recommending closure. GAP-01 and GAP-02 remain unresolved; access restrictions must not be bypassed.'
      setView('policy')
    } else {
      response = `No live model is connected. Your direction is recorded for this in-memory demo. The next real agent run would receive this complete amended context, not only your last message:\n\n${beneficiary}\n\n${context}`
    }
    setMessages(previous => [...previous,
      { role: 'analyst', text: question, revision: sequence },
      { role: 'agent', text: response, revision: action === 'challenge' ? sequence + 1 : sequence },
    ])
    setPrompt('')
  }
  function reviewStage() {
    setStale(previous => previous.filter(index => index !== selected))
    setReviewedStages(previous => [...new Set([...previous, selected])])
    setEvents(previous => [...previous, `r${sequence}: Analyst acknowledged ${stages[selected]} output v${versions[selected]} against current shared context.`])
    if (selected < 5) {
      setCurrent(selected + 1)
      selectStage(selected + 1)
    }
  }
  const note = [
    `CASE-1041 / Harbour Components Ltd / shared revision ${sequence}`,
    'Fictional demonstration data. Draft for human review.',
    `Beneficiary description: ${beneficiary}.`,
    'Selected records: GBP 48,000 incoming, GBP 45,500 outgoing; 94.79%; 56 minutes [SRC-01, TX-781 through TX-784]. These do not establish intent or fund lineage.',
    ...outputs.map((output, index) => `${stages[index]} / v${versions[index]}${stale.includes(index) ? ' / RE-REVIEW REQUIRED' : ''}\n${output}`),
    `Analyst rationale: ${reviewRationale || 'Not recorded'}`,
    'References: E-01 through E-04; GAP-01; GAP-02; G-AML-07 v3; L-01 v2. Both gaps remain open.',
    `Human review: ${reviewed ? 'Reviewed in this local demo' : 'Not reviewed against current revision'}. External save / approval: UNCONFIRMED.`,
  ].join('\n\n')

  const stageTracker = <nav className="ip-stages" aria-label="Investigation workflow">
    {stages.map((name, index) => <button key={name}
      className={`${selected === index ? 'selected' : ''} ${current === index ? 'current-stage' : ''}`}
      aria-current={current === index ? 'step' : undefined} onClick={() => selectStage(index)}>
      <span className="ip-step-number">{reviewedStages.includes(index) ? <Check size={14} /> : index + 1}</span>
      <span>{name}<small>{stale.includes(index) ? 'Re-review needed' : current === index ? 'Current stage' : reviewedStages.includes(index) ? 'Acknowledged' : 'Draft'}</small></span>
      <ChevronRight className="ip-stage-chevron" size={16} />
    </button>)}
  </nav>

  const tabs = <nav className="ip-tabs" aria-label="Investigation views">
    {([['stage', 'Stage output'], ['evidence', 'Evidence & gaps'], ['policy', 'Policy'], ['record', 'Review & record']] as const).map(([key, label]) =>
      <button key={key} aria-pressed={view === key} onClick={() => setView(key)}>{label}{key === 'evidence' && <span>6</span>}</button>)}
  </nav>

  const stageEditor = <section className="ip-stage-editor">
    <div className="ip-section-heading"><div><span className="ip-muted">Stage {selected + 1} of 6 / output v{versions[selected]}</span><h2>{stages[selected]}</h2></div>
      <span className={`ip-status ${stale.includes(selected) ? 'warning' : ''}`}>{stale.includes(selected) ? 'Requires re-review' : 'Editable draft'}</span></div>
    <p>{[
      'Preserve the original alert. Amend the analyst interpretation without overwriting the AML source record.',
      'Set the investigation question and permitted scope before gathering evidence.',
      'Keep supporting evidence, counterevidence and unavailable sources distinct.',
      'Challenge the concern. Separate observed facts, calculations and interpretations.',
      'Validate material claims, amend the note and record your judgment.',
      'Prepare a proposed disposition for the existing authorized human approval workflow.',
    ][selected]}</p>
    <label className="ip-field">Stage output<textarea aria-label="Stage output" rows={6} value={draft} onChange={event => setDraft(event.target.value)} /></label>
    <label className="ip-field">Shared beneficiary description<input value={beneficiaryEdit} onChange={event => setBeneficiaryEdit(event.target.value)} /></label>
    <p className="ip-hint">Shared facts appear in every stage and the reviewed note. Changing a fact flags all outputs for re-review; changing an output flags downstream stages. Source records stay unchanged.</p>
    <label className="ip-field">Reason for amendment<input placeholder="Explain what changed and why" value={rationale} onChange={event => setRationale(event.target.value)} /></label>
    <div className="ip-editor-actions"><button className="ip-primary" disabled={!draft.trim() || !beneficiaryEdit.trim() || !rationale.trim() || (draft.trim() === outputs[selected] && beneficiaryEdit.trim() === beneficiary)} onClick={amendOutput}>Apply across workflow<ArrowRight size={15} /></button>
      <button className="ip-secondary" disabled={draft !== outputs[selected] || beneficiaryEdit !== beneficiary} onClick={reviewStage}>{selected === 5 ? 'Acknowledge stage' : 'Acknowledge & continue'}</button></div>
    <details className="ip-context"><summary>Shared context received by this stage / r{sequence}</summary><p>{beneficiary}</p>{outputs.map((output, index) => <div key={index}><strong>{stages[index]} / v{versions[index]}</strong><p>{output}</p></div>)}</details>
  </section>

  const evidencePanel = <section className="ip-evidence">
    <div className="ip-section-heading"><div><span className="ip-muted">Supplied scenario fixtures</span><h2>Follow the evidence</h2></div><span className="ip-status warning">2 open gaps</span></div>
    <p>Coverage: available 90-day history. Supplied snapshot: 28 Oct 2026, 10:15 UTC; ledger activity through 10:08. Not a live retrieval.</p>
    <div className="ip-evidence-grid">{evidence.map(item => <button key={item.id} className={`ip-evidence-item ${item.id.startsWith('GAP') ? 'gap' : ''}`} onClick={() => setSource(item.id)}>
      <span className="ip-evidence-kind">{item.kind}</span><strong>{item.title}</strong><p>{item.text}</p><small>{item.id} / {item.source}</small><span className="ip-source-link">Inspect supplied source<ChevronRight size={13} /></span>
    </button>)}</div>
  </section>

  const policyPanel = <section className="ip-policy">
    <span className="ip-status warning">Fictional policies, not legal requirements</span><h2>Applicable demonstration guidance</h2>
    <p>G-AML-07 v3 and L-01 v2, both effective 1 Oct 2026. Applicability is stipulated for this fictional case only.</p>
    {policies.map(([locator, passage]) => <blockquote key={locator}><strong>{locator}</strong><p>{passage}</p></blockquote>)}
    <p className="ip-callout">Still outstanding: invoice corroboration (GAP-01) and authorized routing of the restricted-case gap (GAP-02). Missing evidence is not adverse evidence.</p>
  </section>

  const recordPanel = <section className="ip-record">
    <div className="ip-section-heading"><h2>Human review & proposed disposition</h2><span className={`ip-status ${reviewed ? '' : 'warning'}`}>{reviewed ? `Reviewed at r${sequence}` : 'Human review required'}</span></div>
    <p>Edit any stage output to change this note. Amendments remain in history and invalidate an earlier review.</p>
    <label className="ip-field">Analyst rationale<textarea rows={3} value={reviewRationale} placeholder="Record your judgment and acknowledge the open gaps" onChange={event => { setReviewRationale(event.target.value); setReviewed(false); setRecord(null) }} /></label>
    <p className="ip-hint">{stale.length ? `${stale.length} affected stages need acknowledgment before the note can be reviewed.` : 'Both material gaps remain open. Reviewing is not approving a consequential decision.'}</p>
    <div className="ip-editor-actions"><button className="ip-primary" disabled={!reviewRationale.trim() || Boolean(stale.length) || draft !== outputs[selected] || beneficiaryEdit !== beneficiary} onClick={() => {
      setReviewed(true); setRecord(null); setCurrent(4)
      setEvents(previous => [...previous, `r${sequence}: Analyst reviewed the note, acknowledged remaining gaps and recorded rationale: ${reviewRationale.trim()}`])
    }}><ShieldCheck size={15} />Mark note reviewed</button>
      <button className="ip-secondary" disabled={!reviewed} onClick={() => {
        setRecord(note); setCurrent(5)
        setEvents(previous => [...previous, `r${sequence}: Prepared copyable note. No external save or approval confirmed.`])
      }}><Clipboard size={15} />Prepare copyable note</button></div>
    <pre className="ip-note">{note}</pre>
    {record && <label className="ip-field">Prepared note / select and copy manually<textarea aria-label="Copyable reviewed note" readOnly rows={10} value={record} onFocus={event => event.target.select()} /></label>}
    <p className="ip-callout">External saving / approval: <strong>Not confirmed.</strong> Preparing or copying is not saving, closing, filing, restricting an account or approving escalation.</p>
  </section>

  const timeline = <section className="ip-timeline">
    <div className="ip-section-heading"><h2>Transaction timeline</h2><span className="ip-muted">28 Oct 2026 / UTC / GBP</span></div>
    <table><thead><tr><th>Time / record</th><th>Counterparty</th><th>Amount</th><th>Reference</th></tr></thead><tbody>
      {transactions.map(([time, id, party, amount, reference]) => <tr key={id}><td><button onClick={() => setSource('E-01')}>{time}<small>{id}</small></button></td><td>{party}</td><td className={amount.startsWith('-') ? 'ip-outgoing' : ''}>{amount}</td><td>{reference}</td></tr>)}
    </tbody></table>
    <div className="ip-calculation"><span>48,000 in <ArrowRight size={14} /> 45,500 out</span><strong>94.79%</strong><span>56-minute window</span></div>
    <p className="ip-hint">45,500 / 48,000 x 100. Selected records only, not a fund-lineage determination. No account balances are supplied.</p>
  </section>

  const conversation = <section className="ip-conversation">
    <div className="ip-section-heading"><div className="ip-agent-title"><Sparkles size={17} /><h2>Investigation teammate</h2></div><span className="ip-muted">Simulated agent</span></div>
    <div className="ip-messages" aria-live="polite">{messages.map((message, index) => <article key={index} className={`ip-message ${message.role}`}>
      <div><strong>{message.role === 'agent' ? 'RCI Agent / simulation' : 'You'}</strong><span>r{message.revision}{message.revision < sequence ? ' / historical context' : ''}</span></div><p>{message.text}</p>
    </article>)}</div>
    <div className="ip-quick-actions"><button onClick={() => agentReply('What evidence challenges this concern?', 'challenge')}>Challenge the concern</button><button onClick={() => agentReply('What checks are required before recommending closure or escalation?', 'policy')}>Check policy requirements</button></div>
    <form className="ip-composer" onSubmit={event => { event.preventDefault(); agentReply(prompt, 'custom') }}>
      <textarea aria-label="Direct the investigation" placeholder="Direct the investigation or challenge a finding..." rows={2} value={prompt} onChange={event => setPrompt(event.target.value)} />
      <div><small>Uses all applied amendments / r{sequence}</small><button aria-label="Send investigation direction" disabled={!prompt.trim()}><ArrowUp size={17} /></button></div>
    </form>
  </section>

  const sharedStrip = <div className="ip-shared-strip"><span><ShieldCheck size={15} />Shared workflow r{sequence}</span><p>{beneficiary}</p><span>{reviewed ? 'Note reviewed' : stale.length ? `${stale.length} stages need re-review` : 'Draft / awaiting human review'}</span></div>
  const content = view === 'evidence' ? evidencePanel : view === 'policy' ? policyPanel : view === 'record' ? recordPanel : stageEditor

  return <div className={`ip-root ip-variant-${variant}`}>
    <aside className={`sidebar ip-sidebar ${sidebar ? 'sidebar-open' : ''}`} aria-label="Investigation sessions">
      <div className="sidebar-brand"><div className="brand-mark"><FileText size={19} /></div><strong>RCI Agent</strong><button className="icon-button mobile-close" aria-label="Close investigations" onClick={() => setSidebar(false)}><X size={18} /></button></div>
      <button className="new-chat" onClick={() => { if (window.confirm('Reset all in-memory prototype changes?')) window.location.reload() }}><Plus size={17} />New investigation</button>
      <div className="history-label">Investigation sessions</div>
      <nav className="ip-sessions"><button className="ip-session selected" aria-current="page" onClick={() => setSidebar(window.innerWidth > 800)}><span>CASE-1041<span className="ip-priority">High</span></span><strong>Harbour Components Ltd</strong><small>Rapid movement of funds</small><span className="ip-session-stage">{stages[current]}<ChevronRight size={13} /></span></button></nav>
      <div className="ip-session-context"><strong>One case, one shared record</strong><p>Stage outputs, evidence and your amendments stay together as you move through the investigation.</p></div>
      <div className="sidebar-bottom"><span className="local-pill"><span />Local prototype</span><div className="ip-local-user"><span className="avatar">AM</span><span><strong>Alex Morgan</strong><small>Fictional investigator</small></span></div></div>
    </aside>
    <main className="ip-main">
      <div className="ip-prototype-notice"><FlaskConical size={14} /><span>Throwaway UI prototype / fictional data / memory only / no live agent or integrations</span><a href={window.location.pathname}>Return to chat app</a></div>
      <header className="ip-header"><button className="icon-button" aria-label="Toggle investigations" onClick={() => setSidebar(!sidebar)}><PanelLeft size={19} /></button>
        <div><span>Investigation session / CASE-1041</span><h1>Harbour Components Ltd</h1></div>
        <div className="ip-header-meta"><span className="ip-priority">High / original AML priority</span><span>ALT-2041</span></div>
        <button className="ip-secondary" onClick={() => setView('record')}><FileText size={15} />Reviewed note</button>
      </header>
      <div className="ip-layout-description">{variant === 'A' ? 'A / Guided workbench. Persistent journey, conversation on the left, editable stage output on the right. Recommended.' : variant === 'B' ? 'B / Workflow rail. Stage navigation at the side; output gets the canvas and the agent becomes a compact assistant.' : 'C / Evidence desk. Transactions and sources take the lead; conversation and stage output sit beneath.'}</div>
      {variant !== 'B' && stageTracker}
      {sharedStrip}
      <div className="ip-case-strip"><div><strong>Original alert</strong><span>Rapid movement to a newly observed beneficiary</span></div><div><strong>Proposed next action / not a decision</strong><span>Corroborate invoice purpose; route the access gap</span></div>
        <button className="ip-primary" onClick={prepareInvestigation} disabled={prepared}>{prepared ? <Check size={15} /> : <Sparkles size={15} />}{prepared ? 'Demo pack prepared' : 'Prepare investigation'}</button></div>
      {notice && <div className="ip-notice" role="status">{notice}<button className="icon-button" aria-label="Dismiss update" onClick={() => setNotice('')}><X size={14} /></button></div>}
      {variant === 'A' && <div className="ip-guided-layout">{conversation}<div className="ip-workspace">{tabs}{content}</div></div>}
      {variant === 'B' && <div className="ip-rail-layout"><div className="ip-workflow-rail">{stageTracker}<div className="ip-rail-guidance"><ShieldCheck size={19} /><p>The analyst owns the judgment. The agent prepares and updates the pack.</p></div></div><div className="ip-rail-canvas">{tabs}{content}</div><div className="ip-rail-agent">{conversation}</div></div>}
      {variant === 'C' && <div className="ip-desk-layout"><div className="ip-desk-evidence">{timeline}{evidencePanel}</div><div className="ip-desk-bottom"><div className="ip-workspace">{tabs}{content}</div>{conversation}</div></div>}
      <details className="ip-audit"><summary><History size={15} />Amendments & observable actions<span>{events.length} local events / {revisions.length} output revisions</span></summary>
        {!events.length && <p>No actions yet. Supplied scenario fixtures are not a live execution log.</p>}
        {events.map((event, index) => <p key={index}>{event}</p>)}
        {revisions.map(item => <details key={item.sequence}><summary>r{item.sequence} / {stages[item.stage]} / {item.rationale}</summary><div className="ip-revision"><div><strong>Before</strong><pre>{item.before}</pre></div><div><strong>After</strong><pre>{item.after}</pre></div></div></details>)}
      </details>
      <details className="ip-debug"><summary><RotateCcw size={14} />Inspect full prototype state / protocol design boundary<ArrowDown size={13} /></summary>
        <p>AG-UI is the future event/shared-state transport; A2UI is only for restricted dynamic forms. Neither protocol is connected here. Fixed React controls own navigation and review. A real implementation must validate and persist edits server-side before a new agent run, retain replay cursors, and release the worker while awaiting a person.</p>
        <pre>{JSON.stringify({ variant, caseId: 'CASE-1041', sequence, currentStage: stages[current], selectedStage: stages[selected], prepared, beneficiary, outputs, versions, staleStages: stale.map(index => stages[index]), acknowledgedStages: reviewedStages.map(index => stages[index]), reviewed, reviewRationale, externalStatus: 'unconfirmed', revisions, events, messages, unsavedEditor: { draft, beneficiaryEdit, rationale }, preparedRecord: record }, null, 2)}</pre>
      </details>
      <footer className="ip-footer">Fictional evidence and policy / no compliance determination / consequential decisions remain with authorized humans</footer>
    </main>
    <PrototypeSwitcher current={variant} onChange={chooseVariant} />
    {source && <div className="dialog-overlay" onClick={() => setSource(null)}><section className="dialog ip-source-dialog" role="dialog" aria-modal="true" aria-labelledby="ip-source-title" onClick={event => event.stopPropagation()} onKeyDown={event => { if (event.key === 'Escape') setSource(null) }}>
      <div className="dialog-heading"><h2 id="ip-source-title">{source} / supplied source</h2><button autoFocus className="icon-button" aria-label="Close source" onClick={() => setSource(null)}><X size={18} /></button></div>
      <p><strong>{evidence.find(item => item.id === source)?.source}</strong></p><p>{evidence.find(item => item.id === source)?.text}</p>
      {source === 'E-01' && timeline}
      <p>Source IDs are locators in the fictional scenario pack, not live system URLs. KYC reviewed 17 Sep 2026; supplied ledger/history snapshot 28 Oct 2026, 10:15 UTC. Unprovided balances and ledger rows are not verified here.</p>
      <p className="ip-callout">Access is not being attempted. Restricted and missing material remains unavailable in this demo.</p>
    </section></div>}
  </div>
}
