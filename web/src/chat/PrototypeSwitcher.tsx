import { useEffect } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'

const prototypeVariants = [
  { key: 'A', name: 'Guided workbench' },
  { key: 'B', name: 'Workflow rail' },
  { key: 'C', name: 'Evidence desk' },
] as const
export type PrototypeVariant = typeof prototypeVariants[number]['key']

export function PrototypeSwitcher({ current, onChange }: {
  current: PrototypeVariant
  onChange: (variant: PrototypeVariant) => void
}) {
  const index = prototypeVariants.findIndex(item => item.key === current)
  useEffect(() => {
    function cycle(event: KeyboardEvent) {
      if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return
      if (event.target instanceof Element && event.target.closest('input, textarea, select, [contenteditable], [role="tablist"]')) return
      if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return
      event.preventDefault()
      onChange(prototypeVariants[(index + (event.key === 'ArrowRight' ? 1 : 2)) % 3].key)
    }
    window.addEventListener('keydown', cycle)
    return () => window.removeEventListener('keydown', cycle)
  }, [index, onChange])
  if (!import.meta.env.DEV) return null
  return <nav className="ip-switcher" aria-label="Prototype variations">
    <span>Throwaway prototype</span>
    <button aria-label="Previous variant" onClick={() => onChange(prototypeVariants[(index + 2) % 3].key)}><ChevronLeft size={18} /></button>
    <strong>{current} / {prototypeVariants[index].name}</strong>
    <button aria-label="Next variant" onClick={() => onChange(prototypeVariants[(index + 1) % 3].key)}><ChevronRight size={18} /></button>
  </nav>
}
