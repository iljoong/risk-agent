import { useEffect, useRef } from 'react'
import { LockKeyhole, X } from 'lucide-react'

export function AccountDialog({ onClose }: { onClose: () => void }) {
  const done = useRef<HTMLButtonElement>(null)
  useEffect(() => { done.current?.focus() }, [])
  return <div className="dialog-overlay" onKeyDown={event => {
    if (event.key === 'Escape') onClose()
    if (event.key === 'Tab') { event.preventDefault(); done.current?.focus() }
  }}>
    <section className="dialog" role="dialog" aria-modal="true" aria-labelledby="account-title">
      <div className="dialog-heading"><h2 id="account-title">Account & access</h2><button className="icon-button" aria-label="Close account panel" onClick={onClose}><X size={18} /></button></div>
      <p>You are using a local, single-user workspace.</p>
      <div className="setting-row"><span><strong>Current identity</strong><small>Local user on this device</small></span><span className="local-pill">Active</span></div>
      <div className="setting-row"><span><strong>Sign in</strong><small>Authentication comes later</small></span><button disabled>Sign in</button></div>
      <div className="setting-row"><span><strong>Workspace members</strong><small>Multi-user access is not enabled</small></span><button disabled>Manage members</button></div>
      <div className="setting-row"><span><strong>Switch account</strong><small>Available after authentication is added</small></span><button disabled>Switch</button></div>
      <p className="privacy-note"><LockKeyhole size={16} />This app is for local use. Data separation is not a substitute for sign-in or secure shared hosting.</p>
      <div className="dialog-actions"><button ref={done} onClick={onClose}>Done</button></div>
    </section>
  </div>
}
