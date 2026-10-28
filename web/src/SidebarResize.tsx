import { useRef } from 'react'

export function SidebarResize({ label, controls, width, min, max, side, onResize }: {
  label: string; controls: string; width: number; min: number; max: number;
  side: 'left' | 'right'; onResize: (width: number) => void
}) {
  const drag = useRef<{ x: number; width: number } | null>(null)
  const direction = side === 'left' ? 1 : -1
  const resize = (value: number) => onResize(Math.max(min, Math.min(max, value)))
  return <div className="sidebar-resize" role="separator" aria-label={label} aria-controls={controls}
    aria-orientation="vertical" aria-valuemin={min} aria-valuemax={max} aria-valuenow={width} tabIndex={0}
    onPointerDown={event => {
      if (event.button !== 0) return
      event.preventDefault()
      event.currentTarget.focus()
      event.currentTarget.setPointerCapture(event.pointerId)
      drag.current = { x: event.clientX, width }
    }}
    onPointerMove={event => {
      if (drag.current) resize(drag.current.width + (event.clientX - drag.current.x) * direction)
    }}
    onPointerUp={() => { drag.current = null }}
    onPointerCancel={() => { drag.current = null }}
    onLostPointerCapture={() => { drag.current = null }}
    onKeyDown={event => {
      if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
        event.preventDefault()
        resize(width + (event.key === 'ArrowRight' ? 20 : -20) * direction)
      } else if (event.key === 'Home' || event.key === 'End') {
        event.preventDefault()
        resize(event.key === 'Home' ? min : max)
      }
    }} />
}
