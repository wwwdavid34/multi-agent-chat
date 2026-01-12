import type { AskRequestBody, AskResponse, DebateRound, StanceData } from "./types";
export declare function askPanel(body: AskRequestBody): Promise<AskResponse>;
export interface SearchSource {
    url: string;
    title: string;
}
/**
 * Stream-based API call with real-time status updates
 */
export declare function askPanelStream(body: AskRequestBody, callbacks: {
    onStatus?: (message: string) => void;
    onSearchSource?: (source: SearchSource) => void;
    onPanelistResponse?: (panelist: string, response: string) => void;
    onDebateRound?: (round: DebateRound) => void;
    onStanceExtracted?: (panelist: string, stance: StanceData) => void;
    onRolesAssigned?: (roles: Record<string, string>) => void;
    onResult?: (result: AskResponse) => void;
    onDebatePaused?: (result: Partial<AskResponse>) => void;
    onError?: (error: Error) => void;
}, signal?: AbortSignal): Promise<void>;
/**
 * Fetch storage mode information from backend
 */
export declare function fetchStorageInfo(): Promise<{
    mode: string;
    persistent: string;
    description: string;
}>;
/**
 * Fetch initial API keys from environment variables
 * Retries up to 5 times with exponential backoff if backend isn't ready yet
 */
export declare function fetchInitialKeys(): Promise<Record<string, string>>;
/**
 * Generate a conversation title from the first message
 */
export declare function generateTitle(firstMessage: string): Promise<string>;
