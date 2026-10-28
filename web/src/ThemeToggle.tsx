import { useState } from 'react'
import { Moon, Sun } from 'lucide-react'

export function ThemeToggle() {
  const [dark, setDark] = useState(() => document.documentElement.dataset.theme === 'dark')
  return <button className="icon-button theme-toggle" aria-label="Dark mode" aria-pressed={dark}
    title={dark ? 'Switch to light mode' : 'Switch to dark mode'} onClick={() => {
      const next = dark ? 'light' : 'dark'
      document.documentElement.dataset.theme = next
      setDark(!dark)
      try { localStorage.setItem('rci-theme', next) } catch {}
    }}>
    {dark ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
  </button>
}
