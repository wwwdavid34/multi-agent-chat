import type { AskRequestBody, AskResponse, DebateRound } from "./types";
export declare function askPanel(body: AskRequestBody): Promise<AskResponse>;
/**
 * Stream-based API call with real-time status updates
 */
export declare function askPanelStream(body: AskRequestBody, callbacks: {
    onStatus?: (message: string) => void;
    onDebateRound?: (round: DebateRound) => void;
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
