import type { Investigation } from '../investigations/types'

export function fixture(): Investigation {
  const outputs = Object.fromEntries(['detect', 'investigate', 'gather_evidence', 'analyze', 'human_review', 'decision']
    .map(stage => [stage, { text: `${stage} original output`, version: 1, evidence_ids: [], needs_review: true }]))
  return {
    chat_id: 'case-chat', case_id: 'CASE-1041', connector: 'demo', revision: 1,
    current_stage: 'investigate', original_alert: { id: 'ALT-2041', priority: 'High', trigger: 'Rapid movement' },
    sources: [], shared_facts: { beneficiary_description: 'Not observed in available 90-day history' },
    outputs, history: [], review: { reviewed: false, rationale: '', prepared_note: null },
    clarification: null, external_status: 'unconfirmed', prepared: false, transactions: [], evidence: [], calculations: {},
  }
}
