export type PanelResponses = Record<string, string>;

export type LLMProvider = "openai" | "gemini" | "claude" | "grok";

export interface ProviderModel {
  id: string;
  label: string;
}

// Debate role for stance enforcement
export type DebateRole = "PRO" | "CON" | "DEVIL_ADVOCATE";

export interface PanelistConfigPayload {
  id: string;
  name: string;
  provider: LLMProvider;
  model: string;
  role?: DebateRole;  // Pre-assigned debate role (optional, auto-assigned if not set)
}

export type ProviderKeyMap = Partial<Record<LLMProvider, string>>;
export type ProviderModelsMap = Partial<Record<LLMProvider, ProviderModel[]>>;

export interface ProviderModelStatus {
  loading: boolean;
  error: string | null;
}

export type ProviderModelStatusMap = Partial<Record<LLMProvider, ProviderModelStatus>>;

export interface TokenUsage {
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  call_count?: number;
}

export interface AskResponse {
  thread_id: string;
  summary: string;
  panel_responses: PanelResponses;
  usage?: TokenUsage;
}

export interface AskRequestBody {
  thread_id: string;
  question: string;
  attachments?: string[];
  panelists?: PanelistConfigPayload[];
  provider_keys?: ProviderKeyMap;
  // Custom personas for preset mode panelists (name -> persona)
  preset_personas?: Record<string, string>;
  // Custom moderator prompt for report consolidation
  moderator_prompt?: string;
}

// Decision Assistant types
export interface ExpertTask {
  expert_role: string;
  deliverable: string;
}

export interface OptionAnalysis {
  option: string;
  claims: string[];
  numbers: Record<string, number | string>;
  risks: string[];
  score: number;
}

export interface ExpertOutput {
  expert_role: string;
  option_analyses: Record<string, OptionAnalysis>;
  assumptions: string[];
  sources: string[];
  confidence: number;
}

export interface Conflict {
  conflict_type: string;
  topic: string;
  experts: string[];
  values: string[];
}

export interface Recommendation {
  recommended_option: string;
  reasoning: string[];
  tradeoffs: Record<string, { pros: string[]; cons: string[] }>;
  risks: string[];
  what_would_change_mind: string[];
  confidence: number;
}

export interface HumanFeedback {
  action: "proceed" | "re_analyze" | "remove_option";
  approved_assumptions?: string[];
  rejected_assumptions?: string[];
  removed_options?: string[];
  updated_constraints?: Record<string, unknown>;
  additional_instructions?: string;
}

export interface DecisionRequestBody {
  thread_id: string;
  question: string;
  constraints?: Record<string, unknown>;
  max_iterations?: number;
  resume?: boolean;
  human_feedback?: HumanFeedback;
  panelists?: PanelistConfigPayload[];
  provider_keys?: ProviderKeyMap;
}

export type DecisionPhase = "planning" | "analysis" | "conflict" | "human" | "synthesis" | "done";
