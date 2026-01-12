const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? `${window.location.protocol}//${window.location.hostname}:8000`;
/**
 * Get authentication headers including JWT token if available
 */
function getAuthHeaders() {
    const headers = {
        "Content-Type": "application/json",
    };
    // Add Authorization header if token exists
    const token = localStorage.getItem("auth_token");
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }
    return headers;
}
export async function askPanel(body) {
    const res = await fetch(`${API_BASE_URL}/ask`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify(body),
    });
    if (!res.ok) {
        const message = await res.text();
        throw new Error(message || "Request failed");
    }
    return (await res.json());
}
/**
 * Stream-based API call with real-time status updates
 */
export async function askPanelStream(body, callbacks, signal) {
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
            if (done)
                break;
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
                        }
                        else if (event.type === "search_source" && callbacks.onSearchSource) {
                            callbacks.onSearchSource({
                                url: event.url,
                                title: event.title,
                            });
                        }
                        else if (event.type === "panelist_response" && callbacks.onPanelistResponse) {
                            callbacks.onPanelistResponse(event.panelist, event.response);
                        }
                        else if (event.type === "debate_round" && callbacks.onDebateRound) {
                            callbacks.onDebateRound(event.round);
                        }
                        else if (event.type === "stance_extracted" && callbacks.onStanceExtracted) {
                            callbacks.onStanceExtracted(event.panelist, {
                                panelist_name: event.panelist,
                                stance: event.stance,
                                confidence: event.confidence,
                                changed_from_previous: event.changed,
                                core_claim: event.core_claim || "",
                            });
                        }
                        else if (event.type === "roles_assigned" && callbacks.onRolesAssigned) {
                            callbacks.onRolesAssigned(event.roles);
                        }
                        else if (event.type === "debate_paused" && callbacks.onDebatePaused) {
                            callbacks.onDebatePaused({
                                thread_id: event.thread_id,
                                panel_responses: event.panel_responses,
                                debate_history: event.debate_history,
                                usage: event.usage,
                            });
                        }
                        else if (event.type === "result" && callbacks.onResult) {
                            callbacks.onResult({
                                thread_id: event.thread_id,
                                summary: event.summary,
                                panel_responses: event.panel_responses,
                                debate_history: event.debate_history,
                                usage: event.usage,
                            });
                        }
                        else if (event.type === "error" && callbacks.onError) {
                            callbacks.onError(new Error(event.message));
                        }
                        else if (event.type === "done") {
                            // Stream complete
                            return;
                        }
                    }
                    catch (e) {
                        console.error("Failed to parse SSE event:", data, e);
                    }
                }
            }
        }
    }
    catch (error) {
        // Re-throw abort errors so caller can handle UI cleanup
        if (error instanceof Error && error.name === 'AbortError') {
            console.log('Request aborted by user');
            throw error; // Re-throw so App.tsx catch block can reset UI state
        }
        if (callbacks.onError) {
            callbacks.onError(error instanceof Error ? error : new Error(String(error)));
        }
        throw error;
    }
    finally {
        reader.releaseLock();
    }
}
/**
 * Fetch storage mode information from backend
 */
export async function fetchStorageInfo() {
    try {
        const res = await fetch(`${API_BASE_URL}/storage-info`);
        if (!res.ok) {
            console.warn("Failed to fetch storage info:", res.statusText);
            return { mode: "unknown", persistent: "false", description: "Unknown storage mode" };
        }
        return await res.json();
    }
    catch (error) {
        console.warn("Failed to fetch storage info:", error);
        return { mode: "unknown", persistent: "false", description: "Unknown storage mode" };
    }
}
/**
 * Fetch initial API keys from environment variables
 * Retries up to 5 times with exponential backoff if backend isn't ready yet
 */
export async function fetchInitialKeys() {
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
            const data = (await res.json());
            console.log(`[API Keys] Successfully fetched on attempt ${attempt + 1}`);
            return data;
        }
        catch (error) {
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
export async function generateTitle(firstMessage) {
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
    }
    catch (error) {
        console.warn("Failed to generate title:", error);
        return "";
    }
}
