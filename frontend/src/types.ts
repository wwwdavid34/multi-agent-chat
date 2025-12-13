export type PanelResponses = Record<string, string>;

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
}

export interface AskRequestBody {
  thread_id: string;
  question: string;
  attachments?: string[];
  panelists?: PanelistConfigPayload[];
  provider_keys?: ProviderKeyMap;
}
