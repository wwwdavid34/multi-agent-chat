import type { AskRequestBody, AskResponse } from "./types";
export declare function askPanel(body: AskRequestBody): Promise<AskResponse>;
/**
 * Stream-based API call with real-time status updates
 */
export declare function askPanelStream(body: AskRequestBody, callbacks: {
    onStatus?: (message: string) => void;
    onResult?: (result: AskResponse) => void;
    onError?: (error: Error) => void;
}): Promise<void>;
/**
 * Fetch initial API keys from environment variables
 */
export declare function fetchInitialKeys(): Promise<Record<string, string>>;
