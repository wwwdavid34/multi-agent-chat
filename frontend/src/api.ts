import type { AskRequestBody, AskResponse } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function askPanel(body: AskRequestBody): Promise<AskResponse> {
  const res = await fetch(`${API_BASE_URL}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
    onResult?: (result: AskResponse) => void;
    onError?: (error: Error) => void;
  }
): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/ask-stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
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
            } else if (event.type === "result" && callbacks.onResult) {
              callbacks.onResult({
                thread_id: event.thread_id,
                summary: event.summary,
                panel_responses: event.panel_responses,
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
    if (callbacks.onError) {
      callbacks.onError(error instanceof Error ? error : new Error(String(error)));
    }
    throw error;
  } finally {
    reader.releaseLock();
  }
}

/**
 * Fetch initial API keys from environment variables
 */
export async function fetchInitialKeys(): Promise<Record<string, string>> {
  try {
    const res = await fetch(`${API_BASE_URL}/initial-keys`);
    if (!res.ok) {
      console.warn("Failed to fetch initial keys:", res.statusText);
      return {};
    }
    return (await res.json()) as Record<string, string>;
  } catch (error) {
    console.warn("Failed to fetch initial keys:", error);
    return {};
  }
}
