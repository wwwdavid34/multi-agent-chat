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
export function findBestModelMatch(
  targetModel: string,
  availableModels: ProviderModel[]
): ProviderModel | null {
  if (!targetModel || availableModels.length === 0) {
    return null;
  }

  const targetLower = targetModel.toLowerCase();

  // 1. Try exact match (case-insensitive)
  const exactMatch = availableModels.find(
    (model) => model.id.toLowerCase() === targetLower
  );
  if (exactMatch) {
    return exactMatch;
  }

  // 2. Try prefix match - target is prefix of available model
  // e.g., "gemini-1.5-pro" matches "gemini-1.5-pro-latest"
  const prefixMatch = availableModels.find((model) =>
    model.id.toLowerCase().startsWith(targetLower)
  );
  if (prefixMatch) {
    return prefixMatch;
  }

  // 3. Try contains match - available model contains target
  // e.g., "claude-sonnet" matches "claude-3-5-sonnet-20241022"
  const containsMatch = availableModels.find((model) =>
    model.id.toLowerCase().includes(targetLower)
  );
  if (containsMatch) {
    return containsMatch;
  }

  // 4. Try reverse contains - target contains available model
  // e.g., "gemini-1.5-pro-002" in target matches "gemini-1.5-pro"
  const reverseContainsMatch = availableModels.find((model) =>
    targetLower.includes(model.id.toLowerCase())
  );
  if (reverseContainsMatch) {
    return reverseContainsMatch;
  }

  // 5. Find best partial match by similarity score
  // Extract base model name (remove version numbers and dates)
  const targetBase = extractBaseModelName(targetLower);

  let bestMatch: ProviderModel | null = null;
  let bestScore = 0;

  for (const model of availableModels) {
    const modelBase = extractBaseModelName(model.id.toLowerCase());
    const score = calculateSimilarity(targetBase, modelBase);

    if (score > bestScore && score > 0.5) { // Require at least 50% similarity
      bestScore = score;
      bestMatch = model;
    }
  }

  return bestMatch;
}

/**
 * Extract base model name by removing version numbers, dates, and common suffixes
 */
function extractBaseModelName(modelId: string): string {
  return modelId
    .replace(/-\d{8}/g, "") // Remove dates like -20241022
    .replace(/-\d+\.\d+/g, "") // Remove versions like -1.5
    .replace(/-\d+/g, "") // Remove trailing numbers like -002
    .replace(/-latest$/i, "")
    .replace(/-preview$/i, "")
    .replace(/-exp$/i, "")
    .replace(/-beta$/i, "")
    .trim();
}

/**
 * Calculate similarity between two strings (0 to 1)
 * Uses Levenshtein distance normalized by length
 */
function calculateSimilarity(str1: string, str2: string): number {
  const longer = str1.length > str2.length ? str1 : str2;
  const shorter = str1.length > str2.length ? str2 : str1;

  if (longer.length === 0) {
    return 1.0;
  }

  const distance = levenshteinDistance(longer, shorter);
  return (longer.length - distance) / longer.length;
}

/**
 * Calculate Levenshtein distance between two strings
 */
function levenshteinDistance(str1: string, str2: string): number {
  const matrix: number[][] = [];

  for (let i = 0; i <= str2.length; i++) {
    matrix[i] = [i];
  }

  for (let j = 0; j <= str1.length; j++) {
    matrix[0][j] = j;
  }

  for (let i = 1; i <= str2.length; i++) {
    for (let j = 1; j <= str1.length; j++) {
      if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
        matrix[i][j] = matrix[i - 1][j - 1];
      } else {
        matrix[i][j] = Math.min(
          matrix[i - 1][j - 1] + 1, // substitution
          matrix[i][j - 1] + 1,     // insertion
          matrix[i - 1][j] + 1      // deletion
        );
      }
    }
  }

  return matrix[str2.length][str1.length];
}
