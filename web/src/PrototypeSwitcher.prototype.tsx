import { useEffect } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { prototypeVariants } from './investigations/CenteredChat.prototype-data'
import type { PrototypeVariant } from './investigations/CenteredChat.prototype-data'

export function PrototypeSwitcher({ variant, onChange, state }: {
  variant: PrototypeVariant; onChange: (variant: PrototypeVariant) => void; state: Record<string, unknown>
}) {
  const index = prototypeVariants.findIndex(item => item.key === variant)
  function cycle(direction: number) {
    onChange(prototypeVariants[(index + direction + prototypeVariants.length) % prototypeVariants.length].key)
  }
  useEffect(() => {
    function keydown(event: KeyboardEvent) {
      if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey ||
        (event.target instanceof Element && event.target.closest('input, textarea, select, [role=separator], [contenteditable]'))) return
      if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
        event.preventDefault()
        cycle(event.key === 'ArrowLeft' ? -1 : 1)
      }
    }
    window.addEventListener('keydown', keydown)
    return () => window.removeEventListener('keydown', keydown)
  })
  if (!import.meta.env.DEV) return null
  return <div className="cp-switcher" aria-label="Prototype variants">
    <button aria-label="Previous variant" onClick={() => cycle(-1)}><ChevronLeft size={18} /></button>
    <span><small>Throwaway layout prototype</small><strong>{variant} / {prototypeVariants[index].name}</strong></span>
    <button aria-label="Next variant" onClick={() => cycle(1)}><ChevronRight size={18} /></button>
    <details className="cp-state"><summary>State</summary><pre>{JSON.stringify(state, null, 2)}</pre></details>
  </div>
}
