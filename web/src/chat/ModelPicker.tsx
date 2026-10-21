import { ChevronDown } from 'lucide-react'
import type { ModelChoice } from '../api/types'

export function ModelPicker({ models, value, disabled, onChange }: {
  models: ModelChoice[]; value: string; disabled: boolean; onChange: (id: string) => void
}) {
  return <label className="model-picker">
    <span className="sr-only">Model</span>
    <select value={value} disabled={disabled} onChange={event => onChange(event.target.value)}>
      {!models.some(model => model.id === value) && value && <option value={value}>Model unavailable - choose another</option>}
      {models.map(model => <option key={model.id} value={model.id}>{model.label}</option>)}
    </select><ChevronDown size={14} aria-hidden />
  </label>
}
