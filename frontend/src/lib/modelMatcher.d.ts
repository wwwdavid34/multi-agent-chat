import type { ProviderModel } from "../types";
/**
 * Find the best matching model from a list of available models
 *
 * Matching strategy:
 * 1. Exact match (case-insensitive)
 * 2. Starts with match (e.g., "gemini-1.5-pro" matches "gemini-1.5-pro-latest")
 * 3. Contains match (e.g., "claude-3-5-sonnet" matches "claude-3-5-sonnet-20241022")
 * 4. Partial match with highest similarity score
 */
export declare function findBestModelMatch(targetModel: string, availableModels: ProviderModel[]): ProviderModel | null;
