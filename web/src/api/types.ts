export interface ModelChoice { id: string; label: string }
export interface Skill { id: string; name: string; description: string }
export type State = 'routing' | 'pending' | 'queued' | 'running' | 'cancel_requested' | 'succeeded' | 'failed' | 'cancelled' | 'interrupted'
export interface TurnRequest {
  client_request_id: string; message: string; model_id: string; attachment_ids: string[];
  skill_id: string | null; artifact_version_id: string | null
}
export interface Turn { id: string; request: TurnRequest; state: State; mode: string; answer: string; error: string | null }
export interface Attachment { id: string; filename: string; state: string; warnings: string[]; error: string | null }
export interface Task { id: string; turn_id: string; state: State; stage: string; error: string | null }
export interface Artifact { id: string; title: string; version: number; text_content: string; parent_version_id: string | null; turn_id?: string }
export interface ChatSummary {
  id: string; title: string; model_id: string;
  investigation?: { case_id: string; current_stage: string; connector: 'demo' } | null
}
export interface Chat extends ChatSummary { turns: Turn[]; attachments: Attachment[]; tasks: Task[]; artifacts: Artifact[] }
export interface Receipt { turn_id: string; mode: string; task_id: string | null; events_url: string }
export interface TurnEvent {
  id: number; type: 'text_delta' | 'stage' | 'tool_status' | 'artifact' | 'completed' | 'error' | 'promoted';
  data: { text?: string; state?: string; artifact_id?: string; title?: string; version?: number }
}
export const isActive = (state: State) => ['routing', 'pending', 'queued', 'running', 'cancel_requested'].includes(state)
