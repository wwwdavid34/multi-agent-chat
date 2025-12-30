/**
 * Model capability definitions by provider and model pattern
 *
 * This metadata helps:
 * - Filter models for image attachment support
 * - Avoid deprecated models in presets
 * - Suggest appropriate models for different use cases
 */
const MODEL_CAPABILITIES = {
    openai: {
        // GPT-4o family (flagship with vision)
        "gpt-4o": { supportsVision: true, deprecated: false, tier: "flagship" },
        "gpt-4o-2024-11-20": { supportsVision: true, deprecated: false, tier: "flagship" },
        "gpt-4o-2024-08-06": { supportsVision: true, deprecated: false, tier: "flagship" },
        "gpt-4o-2024-05-13": { supportsVision: true, deprecated: false, tier: "flagship" },
        "gpt-4o-mini": { supportsVision: true, deprecated: false, tier: "fast" },
        "gpt-4o-mini-2024-07-18": { supportsVision: true, deprecated: false, tier: "fast" },
        // o-series reasoning models (no vision yet)
        "o1": { supportsVision: false, deprecated: false, tier: "flagship" },
        "o1-2024-12-17": { supportsVision: false, deprecated: false, tier: "flagship" },
        "o1-mini": { supportsVision: false, deprecated: false, tier: "standard" },
        "o1-mini-2024-09-12": { supportsVision: false, deprecated: false, tier: "standard" },
        "o1-preview": { supportsVision: false, deprecated: false, tier: "flagship" },
        "o1-preview-2024-09-12": { supportsVision: false, deprecated: false, tier: "flagship" },
        "o3-mini": { supportsVision: false, deprecated: false, tier: "standard" },
        "o3-mini-2025-01-31": { supportsVision: false, deprecated: false, tier: "standard" },
        // GPT-4 Turbo (vision support)
        "gpt-4-turbo": { supportsVision: true, deprecated: false, tier: "standard" },
        "gpt-4-turbo-2024-04-09": { supportsVision: true, deprecated: false, tier: "standard" },
        "gpt-4-turbo-preview": { supportsVision: true, deprecated: false, tier: "standard" },
        "gpt-4-1106-preview": { supportsVision: true, deprecated: false, tier: "standard" },
        "gpt-4-0125-preview": { supportsVision: true, deprecated: false, tier: "standard" },
        "gpt-4-vision-preview": { supportsVision: true, deprecated: true, tier: "legacy" },
        // GPT-4 (no vision)
        "gpt-4": { supportsVision: false, deprecated: true, tier: "legacy" },
        "gpt-4-0613": { supportsVision: false, deprecated: true, tier: "legacy" },
        "gpt-4-32k": { supportsVision: false, deprecated: true, tier: "legacy" },
        "gpt-4-32k-0613": { supportsVision: false, deprecated: true, tier: "legacy" },
        // GPT-3.5 (deprecated)
        "gpt-3.5-turbo": { supportsVision: false, deprecated: true, tier: "legacy" },
        "gpt-3.5-turbo-0125": { supportsVision: false, deprecated: true, tier: "legacy" },
        "gpt-3.5-turbo-1106": { supportsVision: false, deprecated: true, tier: "legacy" },
        "gpt-3.5-turbo-16k": { supportsVision: false, deprecated: true, tier: "legacy" },
    },
    gemini: {
        // Gemini 2.0 (latest with vision)
        "gemini-2.0-flash-exp": { supportsVision: true, deprecated: false, tier: "flagship" },
        "gemini-2.0-flash": { supportsVision: true, deprecated: false, tier: "flagship" },
        // Gemini 1.5 Pro (flagship with vision)
        "gemini-1.5-pro": { supportsVision: true, deprecated: false, tier: "flagship" },
        "gemini-1.5-pro-latest": { supportsVision: true, deprecated: false, tier: "flagship" },
        "gemini-1.5-pro-002": { supportsVision: true, deprecated: false, tier: "flagship" },
        "gemini-1.5-pro-001": { supportsVision: true, deprecated: false, tier: "flagship" },
        // Gemini 1.5 Flash (fast with vision)
        "gemini-1.5-flash": { supportsVision: true, deprecated: false, tier: "fast" },
        "gemini-1.5-flash-latest": { supportsVision: true, deprecated: false, tier: "fast" },
        "gemini-1.5-flash-002": { supportsVision: true, deprecated: false, tier: "fast" },
        "gemini-1.5-flash-001": { supportsVision: true, deprecated: false, tier: "fast" },
        "gemini-1.5-flash-8b": { supportsVision: true, deprecated: false, tier: "fast" },
        "gemini-1.5-flash-8b-latest": { supportsVision: true, deprecated: false, tier: "fast" },
        // Gemini 1.0 (deprecated)
        "gemini-1.0-pro": { supportsVision: false, deprecated: true, tier: "legacy" },
        "gemini-1.0-pro-latest": { supportsVision: false, deprecated: true, tier: "legacy" },
        "gemini-1.0-pro-001": { supportsVision: false, deprecated: true, tier: "legacy" },
        "gemini-pro": { supportsVision: false, deprecated: true, tier: "legacy" },
    },
    claude: {
        // Claude 3.5 Sonnet (flagship with vision)
        "claude-3-5-sonnet-20241022": { supportsVision: true, deprecated: false, tier: "flagship" },
        "claude-3-5-sonnet-20240620": { supportsVision: true, deprecated: false, tier: "flagship" },
        "claude-3-5-sonnet-latest": { supportsVision: true, deprecated: false, tier: "flagship" },
        // Claude 3.5 Haiku (fast with vision)
        "claude-3-5-haiku-20241022": { supportsVision: true, deprecated: false, tier: "fast" },
        "claude-3-5-haiku-latest": { supportsVision: true, deprecated: false, tier: "fast" },
        // Claude 3 Opus (flagship with vision)
        "claude-3-opus-20240229": { supportsVision: true, deprecated: false, tier: "flagship" },
        "claude-3-opus-latest": { supportsVision: true, deprecated: false, tier: "flagship" },
        // Claude 3 Sonnet (standard with vision)
        "claude-3-sonnet-20240229": { supportsVision: true, deprecated: false, tier: "standard" },
        // Claude 3 Haiku (fast with vision)
        "claude-3-haiku-20240307": { supportsVision: true, deprecated: false, tier: "fast" },
        // Claude 2 (deprecated, no vision)
        "claude-2.1": { supportsVision: false, deprecated: true, tier: "legacy" },
        "claude-2.0": { supportsVision: false, deprecated: true, tier: "legacy" },
        "claude-instant-1.2": { supportsVision: false, deprecated: true, tier: "legacy" },
    },
    grok: {
        // Grok 2 (with vision)
        "grok-2-1212": { supportsVision: true, deprecated: false, tier: "flagship" },
        "grok-2-latest": { supportsVision: true, deprecated: false, tier: "flagship" },
        "grok-vision-beta": { supportsVision: true, deprecated: false, tier: "flagship" },
        // Grok 2 (no vision)
        "grok-2": { supportsVision: false, deprecated: false, tier: "flagship" },
        "grok-beta": { supportsVision: false, deprecated: false, tier: "flagship" },
        // Older Grok models
        "grok-1": { supportsVision: false, deprecated: true, tier: "legacy" },
    },
};
/**
 * Get capabilities for a specific model
 */
export function getModelCapabilities(provider, modelId) {
    const providerCapabilities = MODEL_CAPABILITIES[provider];
    // Direct match
    if (providerCapabilities[modelId]) {
        return providerCapabilities[modelId];
    }
    // Try to match by prefix (for fine-tuned models like "ft:gpt-4o-...")
    const baseModelMatch = Object.keys(providerCapabilities).find((key) => modelId.startsWith(key) || modelId.includes(key));
    if (baseModelMatch) {
        return providerCapabilities[baseModelMatch];
    }
    // Default: assume modern model with vision, not deprecated, standard tier
    return {
        supportsVision: true,
        deprecated: false,
        tier: "standard",
    };
}
/**
 * Filter models by capability requirements
 */
export function filterModelsByCapabilities(models, provider, options = {}) {
    const { requireVision, excludeDeprecated, tiers } = options;
    return models.filter((model) => {
        const capabilities = getModelCapabilities(provider, model.id);
        if (requireVision && !capabilities.supportsVision) {
            return false;
        }
        if (excludeDeprecated && capabilities.deprecated) {
            return false;
        }
        if (tiers && tiers.length > 0 && !tiers.includes(capabilities.tier)) {
            return false;
        }
        return true;
    });
}
/**
 * Check if a model supports vision/image inputs
 */
export function supportsVision(provider, modelId) {
    return getModelCapabilities(provider, modelId).supportsVision;
}
/**
 * Check if a model is deprecated
 */
export function isDeprecated(provider, modelId) {
    return getModelCapabilities(provider, modelId).deprecated;
}
