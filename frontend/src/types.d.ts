export type PanelResponses = Record<string, string>;
export interface ScoreEvent {
    category: string;
    points: number;
    reason: string;
}
export interface RoundScore {
    panelist_name: string;
    round_number: number;
    events: ScoreEvent[];
    round_total: number;
    cumulative_total: number;
}
export interface StanceData {
    panelist_name: string;
    stance: string;
    core_claim: string;
    confidence: number;
    changed_from_previous: boolean;
    change_explanation?: string;
}
export interface DebateRound {
    round_number: number;
    panel_responses: PanelResponses;
    consensus_reached: boolean;
    user_message?: string;
    stances?: Record<string, StanceData>;
    scores?: Record<string, RoundScore>;
}
export type StanceMode = "free" | "adversarial" | "assigned";
export type DebateMode = "autonomous" | "supervised" | "participatory";
export interface AssignedRole {
    panelist_name: string;
    role: "PRO" | "CON" | "DEVIL_ADVOCATE" | "NEUTRAL";
    position_statement: string;
    constraints: string[];
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
    debate_history?: DebateRound[];
    debate_paused?: boolean;
    usage?: TokenUsage;
}
export interface AskRequestBody {
    thread_id: string;
    question: string;
    attachments?: string[];
    panelists?: PanelistConfigPayload[];
    provider_keys?: ProviderKeyMap;
    debate_mode?: DebateMode;
    max_debate_rounds?: number;
    continue_debate?: boolean;
    tagged_panelists?: string[];
    user_message?: string;
    exit_debate?: boolean;
    stance_mode?: StanceMode;
    assigned_roles?: Record<string, AssignedRole>;
}
