import type { Investigation } from './types'

export const prototypeVariants = [
  { key: 'A', name: 'Stage inspector' },
  { key: 'B', name: 'Workflow outline' },
  { key: 'C', name: 'Split review dock' },
] as const
export type PrototypeVariant = typeof prototypeVariants[number]['key']

// Throwaway layout fixture, based on the packaged fictional CASE-1041 records.
const texts = {
  detect: 'Original alert ALT-2041: High AML priority. Rapid movement of funds to a newly observed beneficiary. The original source priority is unchanged.',
  investigate: 'Harbour Components Ltd is an industrial component wholesaler. Supplier payments are consistent with its recorded business profile [SRC-02]. Meridian Supply was not observed in the available 90-day history [SRC-03]; this does not prove a new commercial relationship.',
  gather_evidence: 'Selected ledger records and customer context are available. Invoice MS-882 is missing [GAP-01]. Previous case CASE-0812 is restricted [GAP-02]. Neither gap has been resolved.',
  analyze: 'Selected records show GBP 48,000 incoming and GBP 45,500 outgoing; 94.79% within 56 minutes [E-01]. Timing and amount do not establish wrongdoing or fund lineage.\n\nSupplier payments fit the business profile [E-03]. The invoice reference suggests a possible legitimate explanation, but this payment remains unverified [E-04, GAP-01]. Restricted case contents are not adverse evidence [GAP-02].',
  human_review: 'Draft only. Check supporting evidence and counterevidence, record missing invoice corroboration, and follow the applicable authorized access process. Fictional policy excerpts do not supply a real bank approval path.',
  decision: 'No disposition is approved. Missing evidence remains unresolved. External saving / approval: unconfirmed.',
}

export const prototypeCase: Investigation = {
  chat_id: 'prototype-case-1041', case_id: 'CASE-1041', connector: 'demo', revision: 4,
  current_stage: 'analyze', prepared: true, external_status: 'unconfirmed',
  original_alert: { id: 'ALT-2041', priority: 'High', trigger: 'Rapid movement of funds to a newly observed beneficiary' },
  shared_facts: { beneficiary_description: 'Meridian Supply not observed in the available 90-day history; commercial relationship age unknown.' },
  outputs: Object.fromEntries(Object.entries(texts).map(([stage, text]) => [stage, {
    text, version: 2, needs_review: true, evidence_ids: ['E-01', 'E-03', 'E-04', 'GAP-01', 'GAP-02'],
  }])),
  history: [{ actor: 'demo connector', action: 'prepare', revision: 4, timestamp: 0 }],
  review: { reviewed: false, rationale: '', prepared_note: null }, clarification: null,
  calculations: { incoming_gbp: 48000, outgoing_gbp: 45500, ratio_percent: '94.79', elapsed_minutes: 56 },
  transactions: [
    { id: 'TX-781', timestamp: '2026-10-28T09:12:00Z', direction: 'incoming', amount_gbp: 18000, counterparty: 'Alder Industrial', reference: 'Order H-441' },
    { id: 'TX-782', timestamp: '2026-10-28T09:31:00Z', direction: 'incoming', amount_gbp: 16000, counterparty: 'Beacon Assembly', reference: 'Order H-442' },
    { id: 'TX-783', timestamp: '2026-10-28T09:54:00Z', direction: 'incoming', amount_gbp: 14000, counterparty: 'Cedar Parts', reference: 'Order H-443' },
    { id: 'TX-784', timestamp: '2026-10-28T10:08:00Z', direction: 'outgoing', amount_gbp: 45500, counterparty: 'Meridian Supply', reference: 'Invoice MS-882' },
  ],
  sources: [
    { source_id: 'SRC-01', title: 'Selected transaction ledger records', status: 'available', snapshot_at: '2026-10-28T10:15:00Z', version: 'demo-ledger-v1', coverage: 'Selected records only. Balances not supplied.' },
    { source_id: 'SRC-02', title: 'Customer / account / KYC', status: 'available', snapshot_at: '2026-10-28', version: 'KYC-1041-v3', coverage: 'Industrial component wholesaler. KYC reviewed 17 Sep 2026.' },
    { source_id: 'SRC-03', title: 'Available beneficiary history', status: 'available', snapshot_at: '2026-10-28T10:15:00Z', version: 'demo-history-v1', coverage: 'Available 90-day history assertion only; not proof of relationship age.' },
    { source_id: 'SRC-04', title: 'Previous case CASE-0812', status: 'restricted', snapshot_at: null, version: null, coverage: 'Contents inaccessible. Request authorized access; infer no adverse content.' },
    { source_id: 'SRC-05', title: 'Fictional Group Investigation Standard', status: 'available', snapshot_at: '2026-10-01', version: 'G-AML-07 v3', coverage: 'Fictional policy, not law. Agent findings require investigator validation.' },
    { source_id: 'SRC-06', title: 'Fictional Local Supplement', status: 'available', snapshot_at: '2026-10-01', version: 'L-01 v2', coverage: 'Demo applicability only. Business purpose needs corroboration.' },
    { source_id: 'SRC-07', title: 'Supplier invoice MS-882', status: 'missing', snapshot_at: null, version: null, coverage: 'Invoice unavailable. Payment-reference text is not corroboration.' },
  ],
  evidence: [
    { id: 'E-01', kind: 'Supports concern', title: 'Closely timed movement', source_ids: ['SRC-01'], locators: ['TX-781', 'TX-782', 'TX-783', 'TX-784'], text: 'Closely timed amounts; not proof of intent or fund lineage.' },
    { id: 'E-02', kind: 'Supports concern', title: 'Beneficiary history', source_ids: ['SRC-03'], locators: ['Available 90-day history'], text: 'Not observed in available history; not proof of a new relationship.' },
    { id: 'E-03', kind: 'Counterevidence', title: 'Plausible trade activity', source_ids: ['SRC-01', 'SRC-02'], locators: ['KYC-1041-v3', 'TX-701', 'TX-702'], text: 'Supplier payments fit the business profile; this payment is not verified.' },
    { id: 'E-04', kind: 'Alternative explanation', title: 'Invoice settlement reference', source_ids: ['SRC-01'], locators: ['TX-784 / Invoice MS-882'], text: 'Business purpose remains uncorroborated.' },
    { id: 'GAP-01', kind: 'Missing information', title: 'Invoice unavailable', source_ids: ['SRC-07'], locators: ['MS-882'], text: 'No invoice corroboration has occurred.' },
    { id: 'GAP-02', kind: 'Access limitation', title: 'Previous case restricted', source_ids: ['SRC-04'], locators: ['CASE-0812'], text: 'Use authorized access only. Do not infer adverse content.' },
  ],
}

export const prototypeSkills = [
  'aml-case-context', 'aml-transaction-behaviour', 'aml-hypothesis-review',
  'aml-policy-applicability', 'aml-investigation-readiness', 'aml-case-narrative',
]

export const prototypeMessages = [
  { role: 'user', text: 'Review the movement to Meridian Supply. Challenge the concern before recommending a next step.' },
  { role: 'assistant', text: 'The prepared fictional records show GBP 48,000 incoming and GBP 45,500 outgoing within 56 minutes [E-01]. Timing alone does not establish intent or fund lineage.\n\nA supplier payment is plausible for this business [E-03]. The reference mentions invoice MS-882, but the invoice is missing [E-04, GAP-01]. Meridian Supply was not observed in the available history; that does not establish a new commercial relationship [E-02].\n\nNext permitted check: seek invoice corroboration and authorized access to the prior case. Do not treat inaccessible case contents as adverse evidence [GAP-02].' },
]
