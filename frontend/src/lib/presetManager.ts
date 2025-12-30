import type { PanelistConfigPayload } from "../types";

export interface PanelistPreset {
  id: string;
  name: string;
  description: string;
  panelists: PanelistConfigPayload[];
  isDefault?: boolean;  // System presets cannot be deleted
}

const PRESETS_STORAGE_KEY = "multi-agent-chat:presets";

/**
 * Default presets showcasing different use cases
 */
export const DEFAULT_PRESETS: PanelistPreset[] = [
  {
    id: "quick-and-cheap",
    name: "Quick & Cheap",
    description: "Fast, cost-effective models for quick discussions",
    isDefault: true,
    panelists: [
      {
        id: "quick-1",
        name: "GPT-4o Mini",
        provider: "openai",
        model: "gpt-4o-mini",
      },
      {
        id: "quick-2",
        name: "Gemini Flash",
        provider: "gemini",
        model: "gemini-1.5-flash",
      },
      {
        id: "quick-3",
        name: "Claude Haiku",
        provider: "claude",
        model: "claude-3-5-haiku-20241022",
      },
    ],
  },
  {
    id: "deep-thinkers",
    name: "Deep Thinkers",
    description: "Flagship models for complex reasoning and analysis",
    isDefault: true,
    panelists: [
      {
        id: "deep-1",
        name: "GPT-4o",
        provider: "openai",
        model: "gpt-4o",
      },
      {
        id: "deep-2",
        name: "Claude 3.5 Sonnet",
        provider: "claude",
        model: "claude-3-5-sonnet-20241022",
      },
      {
        id: "deep-3",
        name: "Gemini 1.5 Pro",
        provider: "gemini",
        model: "gemini-1.5-pro",
      },
    ],
  },
  {
    id: "multimodal-experts",
    name: "Multimodal Experts",
    description: "Vision-capable models for image analysis and discussion",
    isDefault: true,
    panelists: [
      {
        id: "vision-1",
        name: "GPT-4o (Vision)",
        provider: "openai",
        model: "gpt-4o",
      },
      {
        id: "vision-2",
        name: "Claude 3.5 Sonnet (Vision)",
        provider: "claude",
        model: "claude-3-5-sonnet-20241022",
      },
      {
        id: "vision-3",
        name: "Gemini 2.0 Flash",
        provider: "gemini",
        model: "gemini-2.0-flash",
      },
      {
        id: "vision-4",
        name: "Grok Vision",
        provider: "grok",
        model: "grok-2-1212",
      },
    ],
  },
  {
    id: "reasoning-specialists",
    name: "Reasoning Specialists",
    description: "OpenAI o-series models for complex problem solving",
    isDefault: true,
    panelists: [
      {
        id: "reasoning-1",
        name: "o1",
        provider: "openai",
        model: "o1",
      },
      {
        id: "reasoning-2",
        name: "o1-mini",
        provider: "openai",
        model: "o1-mini",
      },
      {
        id: "reasoning-3",
        name: "o3-mini",
        provider: "openai",
        model: "o3-mini",
      },
    ],
  },
];

/**
 * Load all presets (default + user-saved)
 */
export function loadPresets(): PanelistPreset[] {
  try {
    const stored = localStorage.getItem(PRESETS_STORAGE_KEY);
    if (!stored) {
      return DEFAULT_PRESETS;
    }

    const userPresets = JSON.parse(stored) as PanelistPreset[];
    return [...DEFAULT_PRESETS, ...userPresets];
  } catch (error) {
    console.error("Failed to load presets:", error);
    return DEFAULT_PRESETS;
  }
}

/**
 * Save a new preset
 */
export function savePreset(preset: Omit<PanelistPreset, "id" | "isDefault">): PanelistPreset {
  const presets = loadPresets();
  const userPresets = presets.filter((p) => !p.isDefault);

  const newPreset: PanelistPreset = {
    ...preset,
    id: `user-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
    isDefault: false,
  };

  const updatedUserPresets = [...userPresets, newPreset];

  try {
    localStorage.setItem(PRESETS_STORAGE_KEY, JSON.stringify(updatedUserPresets));
  } catch (error) {
    console.error("Failed to save preset:", error);
    throw new Error("Failed to save preset");
  }

  return newPreset;
}

/**
 * Update an existing user preset
 */
export function updatePreset(
  presetId: string,
  updates: Partial<Omit<PanelistPreset, "id" | "isDefault">>
): void {
  const presets = loadPresets();
  const preset = presets.find((p) => p.id === presetId);

  if (!preset) {
    throw new Error("Preset not found");
  }

  if (preset.isDefault) {
    throw new Error("Cannot modify default presets");
  }

  const userPresets = presets.filter((p) => !p.isDefault);
  const updatedUserPresets = userPresets.map((p) =>
    p.id === presetId ? { ...p, ...updates } : p
  );

  try {
    localStorage.setItem(PRESETS_STORAGE_KEY, JSON.stringify(updatedUserPresets));
  } catch (error) {
    console.error("Failed to update preset:", error);
    throw new Error("Failed to update preset");
  }
}

/**
 * Delete a user preset
 */
export function deletePreset(presetId: string): void {
  const presets = loadPresets();
  const preset = presets.find((p) => p.id === presetId);

  if (!preset) {
    throw new Error("Preset not found");
  }

  if (preset.isDefault) {
    throw new Error("Cannot delete default presets");
  }

  const userPresets = presets.filter((p) => !p.isDefault);
  const updatedUserPresets = userPresets.filter((p) => p.id !== presetId);

  try {
    localStorage.setItem(PRESETS_STORAGE_KEY, JSON.stringify(updatedUserPresets));
  } catch (error) {
    console.error("Failed to delete preset:", error);
    throw new Error("Failed to delete preset");
  }
}

/**
 * Get a specific preset by ID
 */
export function getPreset(presetId: string): PanelistPreset | undefined {
  const presets = loadPresets();
  return presets.find((p) => p.id === presetId);
}

/**
 * Export a preset as JSON
 */
export function exportPreset(presetId: string): string {
  const preset = getPreset(presetId);
  if (!preset) {
    throw new Error("Preset not found");
  }

  // Exclude id and isDefault for portability
  const exportData = {
    name: preset.name,
    description: preset.description,
    panelists: preset.panelists,
  };

  return JSON.stringify(exportData, null, 2);
}

/**
 * Import a preset from JSON
 */
export function importPreset(jsonString: string): PanelistPreset {
  try {
    const data = JSON.parse(jsonString);

    if (!data.name || !Array.isArray(data.panelists)) {
      throw new Error("Invalid preset format");
    }

    return savePreset({
      name: data.name,
      description: data.description || "",
      panelists: data.panelists,
    });
  } catch (error) {
    console.error("Failed to import preset:", error);
    throw new Error("Failed to import preset. Invalid format.");
  }
}
