export type PanelResponses = Record<string, string>;

export interface DebateRound {
  round_number: number;
  panel_responses: PanelResponses;
  consensus_reached: boolean;
}

export type LLMProvider = "openai" | "gemini" | "claude" | "grok";

export interface ProviderModel {
  id: string;
  label: string;
}

export interface PanelistConfigPayload {
  id: string;
  name: string;
  provider: LLMProvider;
  model: string;
}

export type ProviderKeyMap = Partial<Record<LLMProvider, string>>;
export type ProviderModelsMap = Partial<Record<LLMProvider, ProviderModel[]>>;

export interface ProviderModelStatus {
  loading: boolean;
  error: string | null;
}

export type ProviderModelStatusMap = Partial<Record<LLMProvider, ProviderModelStatus>>;

export interface AskResponse {
  thread_id: string;
  summary: string;
  panel_responses: PanelResponses;
  debate_history?: DebateRound[];
}

export interface AskRequestBody {
  thread_id: string;
  question: string;
  attachments?: string[];
  panelists?: PanelistConfigPayload[];
  provider_keys?: ProviderKeyMap;
  debate_mode?: boolean;
  max_debate_rounds?: number;
  step_review?: boolean;
  continue_debate?: boolean;
}
