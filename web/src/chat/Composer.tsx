import { useRef, useState } from 'react'
import { ArrowUp, FileText, LoaderCircle, Paperclip, Slash, X } from 'lucide-react'
import type { Attachment, Skill } from '../api/types'

export function Composer({ text, onText, skills, selected, onSkill, attachments, onRemove, onFiles, onSend, disabled, onError }: {
  text: string; onText: (text: string) => void; skills: Skill[]; selected: Skill | null;
  onSkill: (skill: Skill | null) => void; attachments: Attachment[]; onRemove: (id: string) => void;
  onFiles: (files: File[]) => Promise<void>; onSend: (message: string, skill: Skill | null) => Promise<void>;
  disabled: boolean; onError: (message: string) => void
}) {
  const [menu, setMenu] = useState(false)
  const [uploading, setUploading] = useState(false)
  const input = useRef<HTMLTextAreaElement>(null)
  const filter = text.startsWith('/') ? text.slice(1).split(/\s/)[0].toLowerCase() : ''
  const choices = skills.filter(skill => skill.id.includes(filter))
  const pick = (skill: Skill) => {
    onSkill(skill); setMenu(false)
    if (text.startsWith('/')) onText(text.replace(/^\/[^\s]*/, '').trimStart())
    input.current?.focus()
  }
  async function send() {
    if (disabled || uploading) return
    let message = text.trim()
    let skill = selected
    const command = message.match(/^\/([a-z0-9_-]+)(?:\s|$)/)
    if (command) {
      skill = skills.find(item => item.id === command[1]) ?? null
      if (!skill) { onError('Unknown skill. Choose an available skill from the menu.'); return }
      message = message.slice(command[0].length).trim()
    }
    if (!message && (skill || attachments.length)) message = skill ? 'Run this skill on the attached PDFs.' : 'Analyze the attached PDF.'
    if (message) await onSend(message, skill)
  }
  return <div className="composer-wrap">
    <div className="composer">
      {(attachments.length > 0 || selected) && <div className="composer-chips">
        {selected && <span className="skill-chip">/{selected.id}<button aria-label="Clear skill" onClick={() => onSkill(null)}><X size={13} /></button></span>}
        {attachments.map(file => <span key={file.id} className="file-chip"><FileText size={15} />{file.filename}
          <button aria-label={`Remove ${file.filename}`} onClick={() => onRemove(file.id)}><X size={13} /></button></span>)}
      </div>}
      <textarea ref={input} aria-label="Message" placeholder="Ask a question, attach an RFP, or type / for a skill"
        rows={2} value={text} disabled={disabled} onChange={event => { onText(event.target.value); setMenu(event.target.value.startsWith('/')) }}
        onKeyDown={event => {
          if (event.key === 'Escape') setMenu(false)
          if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void send() }
        }} />
      <div className="composer-actions">
        <div className="composer-tools">
          <label className="icon-button attach-button" title="Attach PDF">
            <Paperclip size={19} /><span className="sr-only">Attach PDF</span>
            <input type="file" aria-label="Attach PDF" accept=".pdf,application/pdf" multiple disabled={disabled || uploading}
              onChange={async event => {
                const files = Array.from(event.target.files ?? []); event.target.value = ''
                if (files.some(file => !file.name.toLowerCase().endsWith('.pdf'))) { onError('Only PDF attachments are supported.'); return }
                setUploading(true)
                try { await onFiles(files) } finally { setUploading(false) }
              }} />
          </label>
          <button className={`skill-button ${menu ? 'selected' : ''}`} aria-label="Choose a skill" aria-expanded={menu}
            onClick={() => setMenu(!menu)} disabled={disabled}><Slash size={16} /> Skills</button>
          {uploading && <span className="muted"><LoaderCircle className="spin" size={15} /> Uploading PDF</span>}
        </div>
        <button className="send-button" aria-label="Send message" disabled={disabled || uploading || (!text.trim() && !selected && !attachments.length)}
          onClick={() => { void send() }}><ArrowUp size={20} /></button>
      </div>
      {menu && <div className="skill-menu" role="listbox" aria-label="Available skills">
        <div className="menu-heading">Choose a skill</div>
        {choices.map(skill => <button key={skill.id} role="option" aria-selected={selected?.id === skill.id} onClick={() => pick(skill)}>
          <span className="skill-menu-icon"><Slash size={18} /></span><span><strong>{skill.name}</strong><small>{skill.description}</small></span>
        </button>)}
        {!choices.length && <p>No matching skills. Add developer skills and restart the app.</p>}
      </div>}
    </div>
    <p className="composer-note">Drafts need your review. Check important facts against the source.</p>
  </div>
}
