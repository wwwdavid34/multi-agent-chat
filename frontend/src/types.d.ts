export type PanelResponses = Record<string, string>;
export interface AskResponse {
    thread_id: string;
    summary: string;
    panel_responses: PanelResponses;
}
export interface AskRequestBody {
    thread_id: string;
    question: string;
    attachments?: string[];
}
