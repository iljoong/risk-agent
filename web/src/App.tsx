import { useCallback, useEffect, useRef, useState } from 'react'
import { FileText, PanelLeft, PanelRight, X } from 'lucide-react'
import { api } from './api/client'
import { subscribeTurn } from './api/events'
import { isActive } from './api/types'
import type { Artifact, Attachment, Chat, ChatSummary, ModelChoice, Skill } from './api/types'
import { ChatSidebar } from './chat/ChatSidebar'
import { ChatView } from './chat/ChatView'
import { Composer } from './chat/Composer'
import { ModelPicker } from './chat/ModelPicker'
import { ArtifactPanel } from './artifacts/ArtifactPanel'
import { AccountDialog } from './account/AccountDialog'
import './styles.css'

export default function App() {
  const [models, setModels] = useState<ModelChoice[]>([])
  const [skills, setSkills] = useState<Skill[]>([])
  const [history, setHistory] = useState<ChatSummary[]>([])
  const [chat, setChat] = useState<Chat | null>(null)
  const [model, setModel] = useState('')
  const [text, setText] = useState('')
  const [skill, setSkill] = useState<Skill | null>(null)
  const [files, setFiles] = useState<Attachment[]>([])
  const [artifact, setArtifact] = useState<Artifact | null>(null)
  const [contextCleared, setContextCleared] = useState(false)
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  const [sending, setSending] = useState(false)
  const [sidebar, setSidebar] = useState(window.innerWidth > 800)
  const [account, setAccount] = useState(false)
  const current = useRef<string | null>(null)
  const active = chat?.turns.find(turn => isActive(turn.state))
  const chatId = chat?.id
  const activeTurnId = active?.id
  const contextArtifact = contextCleared ? null : artifact ?? chat?.artifacts.at(-1) ?? null
  const report = useCallback((cause: unknown) => setError(cause instanceof Error ? cause.message : 'Request failed. Try again.'), [])

  useEffect(() => {
    let cancelled = false
    Promise.all([api.models(), api.skills(), api.chats()]).then(([config, registry, chats]) => {
      if (cancelled) return
      setModels(config.models); setModel(config.default_model_id); setSkills(registry); setHistory(chats)
    }).catch(report)
    return () => { cancelled = true }
  }, [report])

  const refresh = useCallback(async (id: string) => {
    const saved = await api.chat(id)
    if (current.current === id) setChat(saved)
    setHistory(await api.chats())
    return saved
  }, [])

  useEffect(() => {
    if (!chatId || !activeTurnId) return
    const controller = new AbortController()
    const id = chatId
    const turnId = activeTurnId
    let streamed = ''
    void (async () => {
      try {
        for await (const event of subscribeTurn(id, turnId, controller.signal)) {
          if (current.current !== id) return
          if (event.type === 'text_delta') {
            streamed += event.data.text ?? ''
            setChat(previous => previous?.id === id ? {
              ...previous, turns: previous.turns.map(turn => turn.id === turnId ? { ...turn, answer: streamed } : turn),
            } : previous)
          } else if (event.type === 'stage' || event.type === 'tool_status' || event.type === 'promoted') {
            setStatus(event.data.text ?? 'Working...')
          } else { await refresh(id) }
        }
        if (!controller.signal.aborted) await refresh(id)
      } catch (cause) { if (!controller.signal.aborted) report(cause) }
    })()
    const polling = window.setInterval(() => { void refresh(id).catch(report) }, 2500)
    return () => { controller.abort(); window.clearInterval(polling) }
  }, [chatId, activeTurnId, refresh, report])

  async function openChat(id: string) {
    current.current = id; setError(''); setArtifact(null); setContextCleared(false); setFiles([]); setSkill(null); setText(''); setChat(null)
    try {
      const saved = await api.chat(id)
      if (current.current !== id) return
      setChat(saved); setModel(saved.model_id)
      if (window.innerWidth < 800) setSidebar(false)
    } catch (cause) { report(cause) }
  }
  async function ensureChat() {
    if (current.current) return current.current
    const created = await api.create(model)
    current.current = created.id
    const saved = await api.chat(created.id)
    setChat(saved); setHistory(await api.chats())
    return created.id
  }
  async function send(message: string, selected: Skill | null) {
    setSending(true); setError('')
    try {
      const id = await ensureChat()
      await api.send(id, {
        client_request_id: crypto.randomUUID(), message, model_id: model,
        skill_id: selected?.id ?? null, attachment_ids: files.map(file => file.id),
        artifact_version_id: contextArtifact?.id ?? null,
      })
      if (chat?.title === 'New chat' || !chat) await api.patch(id, { title: message.slice(0, 60) })
      setText(''); setFiles([]); setSkill(null); setStatus('')
      await refresh(id)
    } catch (cause) { report(cause); if (current.current) await refresh(current.current).catch(report) }
    finally { setSending(false) }
  }
  async function attach(incoming: File[]) {
    setError('')
    try {
      const id = await ensureChat()
      const uploaded: Attachment[] = []
      for (const file of incoming) uploaded.push(await api.upload(id, file))
      if (current.current === id) setFiles(previous => [...previous, ...uploaded])
      await refresh(id)
    } catch (cause) { report(cause) }
  }
  async function selectModel(id: string) {
    try {
      if (chat) { await api.patch(chat.id, { model_id: id }); await refresh(chat.id) }
      setModel(id)
    } catch (cause) { report(cause) }
  }
  const newChat = () => { current.current = null; setChat(null); setText(''); setSkill(null); setFiles([]); setArtifact(null); setContextCleared(false); setError('') }
  return <div className={`app-shell ${sidebar ? 'with-sidebar' : ''}`}>
    <ChatSidebar chats={history} current={chat?.id ?? null} open={sidebar} onNew={newChat} onOpen={id => { void openChat(id) }}
      onClose={() => setSidebar(false)} onAccount={() => setAccount(true)}
      onRename={async (id, title) => { try { await api.patch(id, { title }); setHistory(await api.chats()); if (chat?.id === id) await refresh(id) } catch (cause) { report(cause) } }}
      onDelete={async id => { try { await api.delete(id); if (current.current === id) newChat(); setHistory(await api.chats()) } catch (cause) { report(cause) } }} />
    <main className="main-chat">
      <header className="chat-header">
        <button className="icon-button" aria-label="Toggle history" onClick={() => setSidebar(!sidebar)}><PanelLeft size={19} /></button>
        <span className="conversation-title">{chat?.title ?? 'New conversation'}</span>
        <div className="header-right"><ModelPicker models={models} value={model} disabled={Boolean(active) || sending} onChange={id => { void selectModel(id) }} />
          {chat?.artifacts.length ? <button className="icon-button" aria-label="Toggle preview" onClick={() => setArtifact(artifact ? null : chat.artifacts.at(-1) ?? null)}><PanelRight size={19} /></button> : null}</div>
      </header>
      {error && <div className="error-banner" role="alert"><span>{error}</span><button className="icon-button" aria-label="Dismiss error" onClick={() => setError('')}><X size={16} /></button></div>}
      <div className="conversation-scroll">
        <ChatView chat={chat} status={status} skills={skills} onStarter={(message, chosen) => { setText(message); setSkill(chosen) }}
          onStop={turn => { if (chat) void api.cancel(chat.id, turn).then(() => refresh(chat.id)).catch(report) }}
          onRetry={task => { if (chat) void api.retry(chat.id, task).then(() => refresh(chat.id)).catch(report) }}
          onArtifact={selected => { setArtifact(selected); setContextCleared(false) }} />
      </div>
      {contextArtifact && <div className="context-selection"><FileText size={14} />Using {contextArtifact.title}, Version {contextArtifact.version} as context<button aria-label="Clear artifact context" onClick={() => setContextCleared(true)}><X size={13} /></button></div>}
      <Composer text={text} onText={setText} skills={skills} selected={skill} onSkill={setSkill} attachments={files}
        onRemove={id => setFiles(files.filter(file => file.id !== id))} onFiles={attach} onSend={send}
        disabled={Boolean(active) || sending || !models.length} onError={setError} />
    </main>
    {artifact && chat && <ArtifactPanel chatId={chat.id} artifact={artifact} onClose={() => setArtifact(null)} />}
    {account && <AccountDialog onClose={() => setAccount(false)} />}
  </div>
}
