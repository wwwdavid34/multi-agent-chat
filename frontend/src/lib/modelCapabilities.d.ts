import type { LLMProvider } from "../types";
/**
 * Model capability flags
 */
export interface ModelCapabilities {
    supportsVision: boolean;
    deprecated: boolean;
    tier: "flagship" | "standard" | "fast" | "legacy";
}
/**
 * Get capabilities for a specific model
 */
export declare function getModelCapabilities(provider: LLMProvider, modelId: string): ModelCapabilities;
/**
 * Filter models by capability requirements
 */
export declare function filterModelsByCapabilities(models: Array<{
    id: string;
    label: string;
}>, provider: LLMProvider, options?: {
    requireVision?: boolean;
    excludeDeprecated?: boolean;
    tiers?: Array<"flagship" | "standard" | "fast" | "legacy">;
}): Array<{
    id: string;
    label: string;
}>;
/**
 * Check if a model supports vision/image inputs
 */
export declare function supportsVision(provider: LLMProvider, modelId: string): boolean;
/**
 * Check if a model is deprecated
 */
export declare function isDeprecated(provider: LLMProvider, modelId: string): boolean;
