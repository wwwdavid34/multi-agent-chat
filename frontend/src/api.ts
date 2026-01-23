import type { AskRequestBody, AskResponse, DebateRound, StanceData, TokenUsage, PanelistConfigPayload } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? `${window.location.protocol}//${window.location.hostname}:8000`;

// ============================================================================
// Conversation Message Types (for server-side persistence)
// ============================================================================

export interface MessageEntry {
  id: string;
  question: string;
  attachments: string[];
  summary: string | null;
  panel_responses: Record<string, string>;
  panelists: PanelistConfigPayload[];
  debate_history?: DebateRound[] | null;
  debate_mode?: string | null;
  max_debate_rounds?: number | null;
  debate_paused?: boolean;
  stopped?: boolean;
  usage?: TokenUsage | null;
  tagged_panelists?: string[] | null;
}

export interface ConversationResponse {
  thread_id: string;
  messages: MessageEntry[];
}

export interface AllConversationsResponse {
  conversations: Record<string, MessageEntry[]>;
}

// ============================================================================
// Quota Check Types
// ============================================================================

export interface QuotaStatus {
  available: boolean;
  error: string | null;
  provider: string;
}

export interface QuotaCheckResponse {
  results: Record<string, QuotaStatus>;
}

/**
 * Get authentication headers including JWT token if available
 */
function getAuthHeaders(): HeadersInit {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  // Add Authorization header if token exists
  const token = localStorage.getItem("auth_token");
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  return headers;
}

export async function askPanel(body: AskRequestBody): Promise<AskResponse> {
  const res = await fetch(`${API_BASE_URL}/ask`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const message = await res.text();
    throw new Error(message || "Request failed");
  }

  return (await res.json()) as AskResponse;
}

export interface SearchSource {
  url: string;
  title: string;
}

/**
 * Stream-based API call with real-time status updates
 */
export async function askPanelStream(
  body: AskRequestBody,
  callbacks: {
    onStatus?: (message: string) => void;
    onSearchSource?: (source: SearchSource) => void;
    onPanelistResponse?: (panelist: string, response: string) => void;
    onDebateRound?: (round: DebateRound) => void;
    onStanceExtracted?: (panelist: string, stance: StanceData) => void;
    onRolesAssigned?: (roles: Record<string, string>) => void;
    onResult?: (result: AskResponse) => void;
    onDebatePaused?: (result: Partial<AskResponse>) => void;
    onError?: (error: Error) => void;
  },
  signal?: AbortSignal
): Promise<void> {
  console.log("[SSE] Starting askPanelStream request...");

  const res = await fetch(`${API_BASE_URL}/ask-stream`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(body),
    signal,
  });

  console.log("[SSE] Fetch response received:", { ok: res.ok, status: res.status, statusText: res.statusText });

  if (!res.ok) {
    const message = await res.text();
    console.error("[SSE] Response not OK:", message);
    throw new Error(message || "Request failed");
  }

  const reader = res.body?.getReader();
  if (!reader) {
    console.error("[SSE] Response body not readable");
    throw new Error("Response body is not readable");
  }

  console.log("[SSE] Reader obtained, starting to read stream...");

  const decoder = new TextDecoder();
  let buffer = "";
  let eventCount = 0;

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        console.log("[SSE] Stream ended (done=true) after", eventCount, "events");
        break;
      }

      // Decode the chunk and add to buffer
      buffer += decoder.decode(value, { stream: true });

      // Process complete events from buffer
      const lines = buffer.split("\n");
      buffer = lines.pop() || ""; // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6); // Remove "data: " prefix

          try {
            const event = JSON.parse(data);
            eventCount++;
            console.log("[SSE] Event received:", { type: event.type, eventCount, message: event.message || event.panelist || "" });

            if (event.type === "status" && callbacks.onStatus) {
              callbacks.onStatus(event.message);
            } else if (event.type === "search_source" && callbacks.onSearchSource) {
              callbacks.onSearchSource({
                url: event.url,
                title: event.title,
              });
            } else if (event.type === "panelist_response" && callbacks.onPanelistResponse) {
              callbacks.onPanelistResponse(event.panelist, event.response);
            } else if (event.type === "debate_round" && callbacks.onDebateRound) {
              callbacks.onDebateRound(event.round);
            } else if (event.type === "stance_extracted" && callbacks.onStanceExtracted) {
              callbacks.onStanceExtracted(event.panelist, {
                panelist_name: event.panelist,
                stance: event.stance,
                confidence: event.confidence,
                changed_from_previous: event.changed,
                core_claim: event.core_claim || "",
              });
            } else if (event.type === "roles_assigned" && callbacks.onRolesAssigned) {
              callbacks.onRolesAssigned(event.roles);
            } else if (event.type === "debate_paused" && callbacks.onDebatePaused) {
              callbacks.onDebatePaused({
                thread_id: event.thread_id,
                panel_responses: event.panel_responses,
                debate_history: event.debate_history,
                usage: event.usage,
              });
            } else if (event.type === "result" && callbacks.onResult) {
              callbacks.onResult({
                thread_id: event.thread_id,
                summary: event.summary,
                panel_responses: event.panel_responses,
                debate_history: event.debate_history,
                usage: event.usage,
              });
            } else if (event.type === "error" && callbacks.onError) {
              console.error("[SSE] Error event from server:", event.message);
              callbacks.onError(new Error(event.message));
            } else if (event.type === "done") {
              // Stream complete
              console.log("[SSE] Done event received, stream complete after", eventCount, "events");
              return;
            }
          } catch (e) {
            console.error("[SSE] Failed to parse SSE event:", data, e);
          }
        }
      }
    }
  } catch (error) {
    console.error("[SSE] Catch block triggered:", error);
    // Re-throw abort errors so caller can handle UI cleanup
    if (error instanceof Error && error.name === 'AbortError') {
      console.log('[SSE] Request aborted by user');
      throw error;  // Re-throw so App.tsx catch block can reset UI state
    }

    if (callbacks.onError) {
      callbacks.onError(error instanceof Error ? error : new Error(String(error)));
    }
    throw error;
  } finally {
    console.log("[SSE] Finally block - releasing reader lock");
    reader.releaseLock();
  }
}

/**
 * Fetch storage mode information from backend
 */
export async function fetchStorageInfo(): Promise<{
  mode: string;
  persistent: string;
  description: string;
}> {
  try {
    const res = await fetch(`${API_BASE_URL}/storage-info`);
    if (!res.ok) {
      console.warn("Failed to fetch storage info:", res.statusText);
      return { mode: "unknown", persistent: "false", description: "Unknown storage mode" };
    }
    return await res.json();
  } catch (error) {
    console.warn("Failed to fetch storage info:", error);
    return { mode: "unknown", persistent: "false", description: "Unknown storage mode" };
  }
}

/**
 * Fetch initial API keys from environment variables
 * Retries up to 5 times with exponential backoff if backend isn't ready yet
 */
export async function fetchInitialKeys(): Promise<Record<string, string>> {
  const maxRetries = 5;
  const baseDelay = 500; // Start with 500ms delay

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const res = await fetch(`${API_BASE_URL}/initial-keys`);
      if (!res.ok) {
        console.warn(`[API Keys] Attempt ${attempt + 1}/${maxRetries}: Failed to fetch initial keys:`, res.statusText);

        // If this is not the last attempt, wait and retry
        if (attempt < maxRetries - 1) {
          const delay = baseDelay * Math.pow(2, attempt); // Exponential backoff
          console.log(`[API Keys] Retrying in ${delay}ms...`);
          await new Promise(resolve => setTimeout(resolve, delay));
          continue;
        }

        console.error('[API Keys] All retry attempts failed');
        return {};
      }
      const data = (await res.json()) as Record<string, string>;
      console.log(`[API Keys] Successfully fetched on attempt ${attempt + 1}`);
      return data;
    } catch (error) {
      console.warn(`[API Keys] Attempt ${attempt + 1}/${maxRetries}: Failed to fetch initial keys:`, error);

      // If this is not the last attempt, wait and retry
      if (attempt < maxRetries - 1) {
        const delay = baseDelay * Math.pow(2, attempt); // Exponential backoff
        console.log(`[API Keys] Retrying in ${delay}ms...`);
        await new Promise(resolve => setTimeout(resolve, delay));
        continue;
      }

      console.error('[API Keys] All retry attempts failed');
      return {};
    }
  }

  return {};
}

/**
 * Generate a conversation title from the first message
 */
export async function generateTitle(firstMessage: string): Promise<string> {
  try {
    const res = await fetch(`${API_BASE_URL}/generate-title`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ first_message: firstMessage }),
    });

    if (!res.ok) {
      console.warn("Failed to generate title:", res.statusText);
      return ""; // Return empty to keep placeholder
    }

    const data = await res.json();
    return data.title || "";
  } catch (error) {
    console.warn("Failed to generate title:", error);
    return "";
  }
}

// ============================================================================
// Conversation Persistence API
// ============================================================================

/**
 * Save a single conversation message to the server
 */
export async function saveConversationMessage(
  threadId: string,
  message: MessageEntry
): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/conversations/${threadId}/messages`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({
      thread_id: threadId,
      message,
    }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to save message: ${text}`);
  }
}

/**
 * Save multiple conversation messages in a batch
 */
export async function saveConversationMessages(
  threadId: string,
  messages: MessageEntry[]
): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/conversations/${threadId}/messages/batch`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({
      thread_id: threadId,
      messages,
    }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to save messages: ${text}`);
  }
}

/**
 * Get all messages for a specific conversation thread
 */
export async function getConversation(threadId: string): Promise<ConversationResponse> {
  const res = await fetch(`${API_BASE_URL}/conversations/${threadId}`, {
    method: "GET",
    headers: getAuthHeaders(),
  });

  if (!res.ok) {
    if (res.status === 404) {
      // Thread not found or empty - return empty conversation
      return { thread_id: threadId, messages: [] };
    }
    const text = await res.text();
    throw new Error(`Failed to get conversation: ${text}`);
  }

  return await res.json();
}

/**
 * Get all conversations for the current user
 */
export async function getAllConversations(): Promise<AllConversationsResponse> {
  const res = await fetch(`${API_BASE_URL}/conversations/`, {
    method: "GET",
    headers: getAuthHeaders(),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to get conversations: ${text}`);
  }

  return await res.json();
}

/**
 * Delete a specific message from a conversation
 */
export async function deleteConversationMessage(
  threadId: string,
  messageId: string
): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/conversations/${threadId}/messages/${messageId}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });

  if (!res.ok && res.status !== 404) {
    const text = await res.text();
    throw new Error(`Failed to delete message: ${text}`);
  }
}

/**
 * Delete an entire conversation
 */
export async function deleteConversation(threadId: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/conversations/${threadId}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });

  if (!res.ok && res.status !== 404) {
    const text = await res.text();
    throw new Error(`Failed to delete conversation: ${text}`);
  }
}

// ============================================================================
// Quota Check API
// ============================================================================

/**
 * Check API quota availability for specified providers.
 * Returns status for each provider indicating if it can be used.
 */
export async function checkProvidersQuota(providers: string[]): Promise<QuotaCheckResponse> {
  const res = await fetch(`${API_BASE_URL}/providers/check-quota`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ providers }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to check quota: ${text}`);
  }

  return await res.json();
}
