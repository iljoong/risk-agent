import { Check, FileText, MessageSquare, MoreHorizontal, Pencil, Plus, Trash2, UserRound, X } from 'lucide-react'
import { useState } from 'react'
import type { ChatSummary } from '../api/types'

export function ChatSidebar({ chats, current, open, onNew, onNewInvestigation, creating, onOpen, onRename, onDelete, onAccount, onClose }: {
  chats: ChatSummary[]; current: string | null; open: boolean; onNew: () => void; onOpen: (id: string) => void;
  onNewInvestigation: () => void; creating: boolean;
  onRename: (id: string, title: string) => Promise<void>; onDelete: (id: string) => Promise<void>;
  onAccount: () => void; onClose: () => void
}) {
  const [editing, setEditing] = useState<string | null>(null)
  const [title, setTitle] = useState('')
  const [menu, setMenu] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)
  return <aside className={`sidebar ${open ? 'sidebar-open' : ''}`} aria-label="Investigation sessions">
    <div className="sidebar-brand"><div className="brand-mark"><FileText size={19} /></div><strong>Workroom</strong>
      <button className="icon-button mobile-close" aria-label="Close history" onClick={onClose}><X size={18} /></button></div>
    <button className="new-chat" disabled={creating} onClick={onNewInvestigation}><Plus size={17} /> New investigation</button>
    <button className="new-conversation" onClick={onNew}>New conversation</button>
    <div className="history-label">Investigation sessions</div>
    <nav className="chat-list">
      {!chats.length && <p className="empty-history">Your conversations will appear here.</p>}
      {chats.map(chat => <div className={`history-row ${current === chat.id ? 'current' : ''}`} key={chat.id}>
        {editing === chat.id ? <form onSubmit={event => { event.preventDefault(); if (title.trim()) void onRename(chat.id, title.trim()).then(() => setEditing(null)) }}>
          <input aria-label="Chat title" value={title} onChange={event => setTitle(event.target.value)} autoFocus maxLength={200} />
          <button aria-label="Save title"><Check size={15} /></button></form> : <>
          <button className="history-link" onClick={() => onOpen(chat.id)}>{chat.investigation ? <FileText size={15} /> : <MessageSquare size={15} />}<span>{chat.title}</span></button>
          <button className="history-more icon-button" aria-label={`Options for ${chat.title}`} onClick={() => setMenu(menu === chat.id ? null : chat.id)}><MoreHorizontal size={15} /></button>
          {menu === chat.id && <div className="history-menu">
            <button onClick={() => { setEditing(chat.id); setTitle(chat.title); setMenu(null) }}><Pencil size={13} /> Rename</button>
            <button onClick={() => { setDeleting(chat.id); setMenu(null) }}><Trash2 size={13} /> Delete</button>
          </div>}
        </>}
      </div>)}
    </nav>
    <div className="sidebar-bottom"><span className="local-pill"><span /> Local mode</span>
      <button className="account-button" aria-label="Account & access" onClick={onAccount}>
        <span className="avatar"><UserRound size={17} /></span><span><strong>Local workspace</strong><small>Account & access</small></span><MoreHorizontal size={17} />
      </button>
    </div>
    {deleting && <div className="dialog-overlay"><section role="dialog" aria-modal="true" aria-labelledby="delete-title" className="dialog">
      <h2 id="delete-title">Delete this conversation?</h2><p>The conversation, attachments, and generated files will be removed. Stop any active work first.</p>
      <div className="dialog-actions"><button onClick={() => setDeleting(null)}>Cancel</button><button className="danger-button" onClick={() => { void onDelete(deleting).then(() => setDeleting(null)) }}>Delete conversation</button></div>
    </section></div>}
  </aside>
}
