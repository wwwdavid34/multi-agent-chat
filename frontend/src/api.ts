import type {
  AskRequestBody,
  AskResponse,
  DecisionRequestBody,
  DecisionPhase,
  ExpertTask,
  ExpertOutput,
  Conflict,
  Recommendation,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? `${window.location.protocol}//${window.location.hostname}:8000`;

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
    onResult?: (result: AskResponse) => void;
    onError?: (error: Error) => void;
  },
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/ask-stream`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(body),
    signal,
  });

  if (!res.ok) {
    const message = await res.text();
    throw new Error(message || "Request failed");
  }

  const reader = res.body?.getReader();
  if (!reader) {
    throw new Error("Response body is not readable");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) break;

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

            if (event.type === "status" && callbacks.onStatus) {
              callbacks.onStatus(event.message);
            } else if (event.type === "search_source" && callbacks.onSearchSource) {
              callbacks.onSearchSource({
                url: event.url,
                title: event.title,
              });
            } else if (event.type === "panelist_response" && callbacks.onPanelistResponse) {
              callbacks.onPanelistResponse(event.panelist, event.response);
            } else if (event.type === "result" && callbacks.onResult) {
              callbacks.onResult({
                thread_id: event.thread_id,
                summary: event.summary,
                panel_responses: event.panel_responses,
                usage: event.usage,
              });
            } else if (event.type === "error" && callbacks.onError) {
              callbacks.onError(new Error(event.message));
            } else if (event.type === "done") {
              // Stream complete
              return;
            }
          } catch (e) {
            console.error("Failed to parse SSE event:", data, e);
          }
        }
      }
    }
  } catch (error) {
    // Re-throw abort errors so caller can handle UI cleanup
    if (error instanceof Error && error.name === 'AbortError') {
      console.log('Request aborted by user');
      throw error;  // Re-throw so App.tsx catch block can reset UI state
    }

    if (callbacks.onError) {
      callbacks.onError(error instanceof Error ? error : new Error(String(error)));
    }
    throw error;
  } finally {
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
// Conversation persistence (PostgreSQL storage)
// ============================================================================

/**
 * Load all conversations for the authenticated user from the server.
 * Returns a map of thread_id -> messages.
 */
export async function loadAllConversations(): Promise<Record<string, any[]>> {
  const token = localStorage.getItem("auth_token");
  if (!token) return {};

  const res = await fetch(`${API_BASE_URL}/auth/conversations`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    console.warn("[Conversations] Failed to load:", res.status, res.statusText);
    return {};
  }

  const data = await res.json();
  return data.conversations ?? {};
}

/**
 * Save a single conversation message to the server.
 * Best-effort: errors are caught and logged, never thrown.
 */
export async function saveConversationMessage(
  threadId: string,
  message: Record<string, unknown>
): Promise<void> {
  try {
    const token = localStorage.getItem("auth_token");
    if (!token) return; // guest — skip

    await fetch(
      `${API_BASE_URL}/auth/conversations/${encodeURIComponent(threadId)}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(message),
      }
    );
  } catch (err) {
    console.warn("[Conversations] Failed to save message:", err);
  }
}

/**
 * Stream-based decision assistant API call with real-time phase updates
 */
export async function decisionStream(
  body: DecisionRequestBody,
  callbacks: {
    onPhaseUpdate?: (phase: DecisionPhase) => void;
    onOptionsIdentified?: (options: string[], expertTasks: ExpertTask[]) => void;
    onExpertComplete?: (expertRole: string, output: ExpertOutput) => void;
    onConflictsDetected?: (conflicts: Conflict[], openQuestions: string[]) => void;
    onAwaitingInput?: (data: unknown) => void;
    onRecommendation?: (recommendation: Recommendation) => void;
    onError?: (error: Error) => void;
  },
  signal?: AbortSignal
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/decision-stream`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    throw new Error(`Decision stream failed: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        try {
          const event = JSON.parse(line.slice(6));
          switch (event.type) {
            case "phase_update":
              callbacks.onPhaseUpdate?.(event.phase);
              break;
            case "options_identified":
              callbacks.onOptionsIdentified?.(event.options, event.expert_tasks);
              break;
            case "expert_complete":
              callbacks.onExpertComplete?.(event.expert_role, event.output);
              break;
            case "conflicts_detected":
              callbacks.onConflictsDetected?.(event.conflicts, event.open_questions);
              break;
            case "awaiting_input":
              callbacks.onAwaitingInput?.(event.data);
              break;
            case "recommendation":
              callbacks.onRecommendation?.(event.recommendation);
              break;
            case "error":
              callbacks.onError?.(new Error(event.message));
              break;
            case "done":
              return;
          }
        } catch (e) {
          console.warn("Failed to parse SSE event:", line, e);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
