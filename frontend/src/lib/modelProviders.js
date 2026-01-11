const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? `${window.location.protocol}//${window.location.hostname}:8000`;
export const PROVIDERS = [
    {
        id: "openai",
        label: "OpenAI",
        description: "GPT-4o, GPT-4.1, o-series and fine-tunes",
        docs: "https://platform.openai.com/docs/models",
        keyHint: "Key usually starts with sk-...",
    },
    {
        id: "gemini",
        label: "Google Gemini",
        description: "Gemini 1.5, Flash, and experimental releases",
        docs: "https://ai.google.dev/gemini-api/docs/models",
        keyHint: "Use your Google AI Studio API key",
    },
    {
        id: "claude",
        label: "Anthropic Claude",
        description: "Claude 3 family and future releases",
        docs: "https://docs.anthropic.com/en/docs/models-overview",
        keyHint: "Key usually starts with sk-ant-...",
    },
    {
        id: "grok",
        label: "xAI Grok",
        description: "Grok beta models",
        docs: "https://docs.x.ai/docs/models",
        keyHint: "Key usually starts with xai-...",
    },
];
export const PROVIDER_LABELS = PROVIDERS.reduce((acc, provider) => {
    acc[provider.id] = provider.label;
    return acc;
}, {});
function extractErrorMessage(payload) {
    if (typeof payload === "string") {
        return payload;
    }
    if (payload && typeof payload === "object") {
        const maybe = payload;
        if (typeof maybe.detail === "string") {
            return maybe.detail;
        }
        if (maybe.error) {
            if (typeof maybe.error === "string") {
                return maybe.error;
            }
            if (typeof maybe.error === "object" && maybe.error && typeof maybe.error.message === "string") {
                return maybe.error.message;
            }
        }
        if (typeof maybe.message === "string") {
            return maybe.message;
        }
    }
    return null;
}
export async function fetchModelsForProvider(provider, apiKey) {
    if (!apiKey.trim()) {
        throw new Error("API key is required");
    }
    const response = await fetch(`${API_BASE_URL}/providers/${provider}/models`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: apiKey.trim() }),
    });
    if (!response.ok) {
        const text = await response.text();
        try {
            const parsed = JSON.parse(text);
            const message = extractErrorMessage(parsed);
            throw new Error(message || text || "Failed to fetch models");
        }
        catch {
            throw new Error(text || "Failed to fetch models");
        }
    }
    const data = await response.json();
    const models = Array.isArray(data?.models) ? data.models : [];
    return models;
}
