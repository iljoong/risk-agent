import { useState } from 'react'
import type { Investigation } from './types'

const money = (amount: number) => new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', maximumFractionDigits: 0 }).format(amount)
export function EvidencePanel({ snapshot }: { snapshot: Investigation }) {
  const [sourceId, setSourceId] = useState<string | null>(null)
  const source = snapshot.sources.find(item => item.id === sourceId)
  return <section className="evidence-desk" aria-label="Investigation evidence">
    <div><h2>Transaction timeline</h2>
      {!snapshot.prepared && <p>Prepare the investigation to collect the permitted fictional source records.</p>}
      <ol className="transaction-timeline">{snapshot.transactions.map(item => <li key={item.id}>
        <time>{item.timestamp.slice(11, 16)} UTC</time><strong>{item.direction === 'incoming' ? '+' : '-'}{money(item.amount_gbp)}</strong>
        <span>{item.counterparty}<small>{item.id} / {item.reference}</small></span>
      </li>)}</ol>
      {snapshot.prepared && <p className="investigation-warning">Timing and amount comparison is not proof of fund lineage or intent. Balances are not supplied.</p>}
      <p><strong>Shared finding:</strong> {snapshot.shared_facts.beneficiary_description}</p>
    </div>
    <div><h2>Evidence register</h2>
      <div className="evidence-register">{snapshot.evidence.map(item => <article key={item.id}>
        <small>{item.id} / {item.kind}</small><h3>{item.title}</h3><p>{item.text}</p>
        <p>{item.locators.join(', ')}</p>
        {item.source_ids.map(id => <button key={id} onClick={() => setSourceId(id)}>Inspect {id}</button>)}
      </article>)}</div>
      <details><summary>All sources ({snapshot.sources.length})</summary>{snapshot.sources.map(item =>
        <button key={item.id} onClick={() => setSourceId(item.id)}>{item.id}: {item.status}</button>)}</details>
      {source && <section className="source-inspection" aria-label={`Source ${source.id}`}>
        <button onClick={() => setSourceId(null)}>Close source</button>
        <h3>{source.id}: {source.title}</h3><p>Status: {source.status}</p>
        <p>Fixture snapshot: {source.snapshot_at ?? 'Unavailable'}; version: {source.version ?? 'Unavailable'}</p>
        <p>Retrieved: {source.retrieved_at ?? 'Not retrieved'}</p><p>{source.coverage}</p>
        <pre>{JSON.stringify(source.data ?? {}, null, 2)}</pre>
      </section>}
    </div>
  </section>
}
