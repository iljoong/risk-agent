import { Check, CircleAlert, LoaderCircle, RotateCcw, Square } from 'lucide-react'
import { isActive } from '../api/types'
import type { Task } from '../api/types'

export function TaskCard({ task, onStop, onRetry }: { task: Task; onStop: () => void; onRetry: () => void }) {
  const active = isActive(task.state)
  return <div className={`task-card task-${task.state}`}>
    <div className="task-heading">{active ? <LoaderCircle className="spin" size={17} /> : task.state === 'succeeded' ? <Check size={17} /> : <CircleAlert size={17} />}
      <strong>{task.stage}</strong><span className="task-state">{task.state.replace('_', ' ')}</span></div>
    {active && <p>You can switch chats or close this tab. Your task keeps running.</p>}
    {task.error && <p className="error-copy">{task.error}</p>}
    {active ? <button className="text-button" onClick={onStop} disabled={task.state === 'cancel_requested'}><Square size={12} /> Stop task</button>
      : task.state !== 'succeeded' && <button className="text-button" onClick={onRetry}><RotateCcw size={14} /> Retry task</button>}
  </div>
}
