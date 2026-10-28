import { lazy, StrictMode, Suspense } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

const InvestigationPrototype = import.meta.env.DEV
  ? lazy(() => import('./chat/InvestigationPrototype.tsx'))
  : null
const prototype = new URLSearchParams(window.location.search).get('prototype') === 'investigation'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {prototype && InvestigationPrototype
      ? <Suspense fallback={<p>Opening investigation prototype...</p>}><InvestigationPrototype /></Suspense>
      : <App />}
  </StrictMode>,
)
