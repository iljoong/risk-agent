import { Download, FileText, X } from 'lucide-react'
import { artifactUrl } from '../api/client'
import type { Artifact } from '../api/types'

export function ArtifactPanel({ chatId, artifact, onClose }: { chatId: string; artifact: Artifact; onClose: () => void }) {
  return <aside className="artifact-panel" aria-label="Generated content">
    <div className="artifact-toolbar"><FileText size={17} /><span><strong>{artifact.title}</strong><small>Version {artifact.version}</small></span>
      <a className="icon-button" aria-label="Download HTML artifact" href={artifactUrl(chatId, artifact, 'download')} download><Download size={17} /></a>
      <button className="icon-button" aria-label="Close preview" onClick={onClose}><X size={18} /></button></div>
    <iframe title="HTML artifact preview" sandbox="" referrerPolicy="no-referrer" src={artifactUrl(chatId, artifact, 'preview')} />
    <footer>Saved in this conversation. Review assumptions before sharing.</footer>
  </aside>
}
