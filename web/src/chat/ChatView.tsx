import { useEffect, useRef } from 'react'
import { ArrowUpRight, FileText, LoaderCircle, Sparkles, Square } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { isActive } from '../api/types'
import type { Artifact, Chat, Skill } from '../api/types'
import { TaskCard } from './TaskCard'

export function ChatView({ chat, status, onStop, onRetry, onArtifact, onStarter, skills }: {
  chat: Chat | null; status: string; onStop: (turnId: string) => void; onRetry: (taskId: string) => void;
  onArtifact: (artifact: Artifact) => void; onStarter: (text: string, skill: Skill | null) => void; skills: Skill[]
}) {
  const end = useRef<HTMLDivElement>(null)
  const latest = chat?.turns.at(-1)
  useEffect(() => { end.current?.scrollIntoView?.({ block: 'end' }) }, [latest?.answer, latest?.state, status])
  if (!chat?.turns.length) return <section className="welcome">
    <span className="welcome-mark"><Sparkles size={30} strokeWidth={1.5} /></span>
    <h1>What are we working on?</h1><p>Bring a question or a document.<br />Leave with a useful first draft.</p>
    <div className="starter-list">
      <button onClick={() => onStarter('Draft a response presentation from the attached RFP.', skills.find(skill => skill.id === 'rfp-response') ?? null)}><FileText size={18} /><span><strong>Draft an RFP response</strong><small>From requirements to presentation</small></span><ArrowUpRight size={16} /></button>
      <button onClick={() => onStarter('Analyze the mandatory requirements in the attached PDF.', null)}><Sparkles size={18} /><span><strong>Understand a document</strong><small>Find requirements and open questions</small></span><ArrowUpRight size={16} /></button>
    </div>
  </section>
  return <div className="messages">
    {chat.turns.map((turn, index) => {
      const task = chat.tasks.find(item => item.turn_id === turn.id)
      return <section className="turn" key={turn.id}>
        <div className="user-message">
          {turn.request.attachment_ids?.map(id => <span className="attachment-tag" key={id}><FileText size={16} />{chat.attachments.find(file => file.id === id)?.filename ?? 'PDF attachment'}</span>)}
          {turn.request.skill_id && <span className="inline-skill">/{turn.request.skill_id}</span>}
          <p>{turn.request.message}</p>
        </div>
        <div className="assistant-message">
          <div className="assistant-label"><Sparkles size={15} /><strong>Workroom</strong></div>
          {task && <TaskCard task={task} onStop={() => onStop(turn.id)} onRetry={() => onRetry(task.id)} />}
          {turn.answer && <div className="markdown" data-testid={index === chat.turns.length - 1 ? 'latest-assistant-message' : undefined}>
            <ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml>{turn.answer}</ReactMarkdown>
          </div>}
          {isActive(turn.state) && !task && <div className="live-status" role="status"><LoaderCircle className="spin" size={16} /><span>{status || 'Preparing your response...'}</span><button className="icon-button" aria-label="Stop response" onClick={() => onStop(turn.id)}><Square size={13} /></button></div>}
          {turn.error && !task && <p className="error-copy">{turn.error}</p>}
          {chat.artifacts.filter(item => item.turn_id === turn.id).map(artifact => <button className="artifact-card" key={artifact.id} onClick={() => onArtifact(artifact)}>
            <span className="artifact-icon"><FileText size={22} /></span><span><strong>{artifact.title}</strong><small>HTML slides / Version {artifact.version}</small></span><ArrowUpRight size={18} />
          </button>)}
        </div>
      </section>
    })}
    <div ref={end} />
  </div>
}
