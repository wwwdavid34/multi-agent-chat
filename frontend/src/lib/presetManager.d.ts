import type { PanelistConfigPayload } from "../types";
export interface PanelistPreset {
    id: string;
    name: string;
    description: string;
    panelists: PanelistConfigPayload[];
    isDefault?: boolean;
}
/**
 * Default presets showcasing different use cases
 */
export declare const DEFAULT_PRESETS: PanelistPreset[];
/**
 * Load all presets (default + user-saved)
 */
export declare function loadPresets(): PanelistPreset[];
/**
 * Save a new preset
 */
export declare function savePreset(preset: Omit<PanelistPreset, "id" | "isDefault">): PanelistPreset;
/**
 * Update an existing user preset
 */
export declare function updatePreset(presetId: string, updates: Partial<Omit<PanelistPreset, "id" | "isDefault">>): void;
/**
 * Delete a user preset
 */
export declare function deletePreset(presetId: string): void;
/**
 * Get a specific preset by ID
 */
export declare function getPreset(presetId: string): PanelistPreset | undefined;
/**
 * Export a preset as JSON
 */
export declare function exportPreset(presetId: string): string;
/**
 * Import a preset from JSON
 */
export declare function importPreset(jsonString: string): PanelistPreset;
