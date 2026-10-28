export const stages = ['detect', 'investigate', 'gather_evidence', 'analyze', 'human_review', 'decision'] as const
export type Stage = typeof stages[number]
export const stageNames: Record<Stage, string> = {
  detect: 'Detect', investigate: 'Investigate', gather_evidence: 'Gather evidence',
  analyze: 'Analyze', human_review: 'Human review', decision: 'Decision',
}
export interface StageOutput { text: string; version: number; evidence_ids: string[]; needs_review: boolean }
export interface Source {
  id: string; title: string; status: string; snapshot_at: string | null; version: string | null;
  coverage: string; retrieved_at?: string; data?: Record<string, unknown>
}
export interface Investigation {
  chat_id: string; case_id: string; connector: 'demo'; revision: number; current_stage: Stage;
  original_alert: { id: string; priority: string; trigger: string };
  sources: Source[]; shared_facts: { beneficiary_description: string };
  outputs: Record<string, StageOutput>;
  history: { actor: string; action: string; revision: number; timestamp: number; reason?: string; before?: string; after?: string; stage_id?: Stage }[];
  review: { reviewed: boolean; rationale: string; prepared_note: string | null };
  clarification: Record<string, unknown> | null; external_status: 'unconfirmed'; prepared: boolean;
  transactions: { id: string; timestamp: string; direction: string; amount_gbp: number; counterparty: string; reference: string }[];
  evidence: { id: string; kind: string; title: string; source_ids: string[]; locators: string[]; text: string }[];
  calculations: Record<string, number | string>;
}
export type InvestigationAction = 'amend_output' | 'amend_fact' | 'acknowledge_stage' | 'select_stage' |
  'review_note' | 'prepare_note' | 'prepare' | 'request_clarification' | 'resolve_clarification' | 'cancel_clarification'
export type OnCommand = (action: InvestigationAction, payload: Record<string, unknown>, revision: number) => Promise<void>
export interface StateEnvelope { snapshot: Investigation; sequence: number }
