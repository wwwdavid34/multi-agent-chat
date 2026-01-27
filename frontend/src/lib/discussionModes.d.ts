/**
 * Discussion Mode Configuration System
 *
 * Defines all available discussion modes with their settings, presets, and UI behavior.
 * This is the single source of truth for mode configuration across the app.
 */
import type { DebateMode, DebateRole } from "../types";
export type DiscussionModeId = "panel" | "autonomous" | "supervised" | "participatory" | "business-validation" | "decision";
export type ModeCategory = "QUICK" | "STRUCTURED" | "RESEARCH";
export type StanceMode = "free" | "adversarial" | "assigned";
export interface PresetPanelist {
    name: string;
    persona: string;
    /** Optional debate role - if omitted, panelist uses natural persona without stance enforcement */
    role?: DebateRole;
}
export interface DiscussionModeConfig {
    id: DiscussionModeId;
    name: string;
    shortName: string;
    description: string;
    category: ModeCategory;
    icon: string;
    /** Maps to backend debate_mode field (undefined = no debate, just panel responses) */
    debateMode: DebateMode | undefined;
    defaultRounds: number;
    showRoundsConfig: boolean;
    /** If true, mode provides preset panelists that override user's panelists */
    overrideUserPanelists: boolean;
    presetPanelists?: PresetPanelist[];
    /** Stance assignment mode for debates */
    stanceMode?: StanceMode;
    /** Custom moderator prompt for report consolidation */
    moderatorPrompt?: string;
    /** If true, this mode uses the decision assistant endpoint instead of the panel/debate flow */
    isDecisionMode?: boolean;
}
/**
 * All available discussion modes.
 * Order matters - this is the display order in the UI.
 */
export declare const DISCUSSION_MODES: DiscussionModeConfig[];
/**
 * Group modes by category for UI display
 */
export declare const MODES_BY_CATEGORY: Record<ModeCategory, DiscussionModeConfig[]>;
/**
 * Category display labels
 */
export declare const CATEGORY_LABELS: Record<ModeCategory, string>;
/**
 * Get mode config by ID
 */
export declare function getModeConfig(modeId: DiscussionModeId | undefined): DiscussionModeConfig | undefined;
/**
 * Get default mode config
 */
export declare function getDefaultMode(): DiscussionModeConfig;
/**
 * Check if a mode has preset panelists
 */
export declare function hasPresetPanelists(modeId: DiscussionModeId): boolean;
/**
 * Get icon path for mode
 * Returns SVG path data for common icons
 */
export declare function getModeIconPath(icon: string): string;
