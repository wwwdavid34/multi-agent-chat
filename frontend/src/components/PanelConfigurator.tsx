import { AnimatePresence, motion } from "framer-motion";
import { PROVIDERS, PROVIDER_LABELS } from "../lib/modelProviders";
import type {
  LLMProvider,
  PanelistConfigPayload,
  ProviderKeyMap,
  ProviderModelsMap,
  ProviderModelStatusMap,
} from "../types";
import { useMemo, useState } from "react";
import { loadPresets, savePreset, deletePreset, type PanelistPreset } from "../lib/presetManager";
import { getModelCapabilities } from "../lib/modelCapabilities";

interface PanelConfiguratorProps {
  open: boolean;
  onClose: () => void;
  panelists: PanelistConfigPayload[];
  onPanelistChange: (id: string, updates: Partial<PanelistConfigPayload>) => void;
  onAddPanelist: () => void;
  onRemovePanelist: (id: string) => void;
  providerKeys: ProviderKeyMap;
  onProviderKeyChange: (provider: LLMProvider, key: string) => void;
  providerModels: ProviderModelsMap;
  modelStatus: ProviderModelStatusMap;
  onFetchModels: (provider: LLMProvider) => Promise<void>;
  maxPanelists: number;
  onLoadPreset: (preset: PanelistPreset) => void;
}

export function PanelConfigurator({
  open,
  onClose,
  panelists,
  onPanelistChange,
  onAddPanelist,
  onRemovePanelist,
  providerKeys,
  onProviderKeyChange,
  providerModels,
  modelStatus,
  onFetchModels,
  maxPanelists,
  onLoadPreset,
}: PanelConfiguratorProps) {
  const canAddMore = panelists.length < maxPanelists;
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [presets, setPresets] = useState<PanelistPreset[]>(() => loadPresets());
  const [selectedPresetId, setSelectedPresetId] = useState<string>("");
  const [showSavePreset, setShowSavePreset] = useState(false);
  const [newPresetName, setNewPresetName] = useState("");
  const [newPresetDescription, setNewPresetDescription] = useState("");
  const [showManagePresets, setShowManagePresets] = useState(false);

  const toggleKeyVisibility = (providerId: string) => {
    setShowKeys((prev) => ({ ...prev, [providerId]: !prev[providerId] }));
  };

  const copyToClipboard = async (providerId: string, key: string) => {
    try {
      await navigator.clipboard.writeText(key);
      setCopiedKey(providerId);
      setTimeout(() => setCopiedKey(null), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  const handleLoadPreset = () => {
    const preset = presets.find((p) => p.id === selectedPresetId);
    if (preset) {
      onLoadPreset(preset);
      setSelectedPresetId("");
    }
  };

  const handleSavePreset = () => {
    if (!newPresetName.trim()) return;

    try {
      const newPreset = savePreset({
        name: newPresetName.trim(),
        description: newPresetDescription.trim(),
        panelists: panelists,
      });
      setPresets(loadPresets());
      setNewPresetName("");
      setNewPresetDescription("");
      setShowSavePreset(false);
    } catch (err) {
      console.error("Failed to save preset:", err);
    }
  };

  const handleDeletePreset = (presetId: string) => {
    try {
      deletePreset(presetId);
      setPresets(loadPresets());
    } catch (err) {
      console.error("Failed to delete preset:", err);
    }
  };

  const providerSummary = useMemo(() => {
    return panelists.map((panelist) => {
      const providerLabel = PROVIDER_LABELS[panelist.provider];
      const modelLabel = panelist.model || "Select a model";
      return {
        id: panelist.id,
        text: `${panelist.name.trim() || "Panelist"} → ${providerLabel}${panelist.model ? ` (${modelLabel})` : ""}`,
      };
    });
  }, [panelists]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <div className="flex-1 bg-foreground/20 backdrop-blur-sm" onClick={onClose} />
          <motion.div
            initial={{ x: 420 }}
            animate={{ x: 0 }}
            exit={{ x: 420 }}
            transition={{ type: "spring", stiffness: 280, damping: 28 }}
            className="w-full max-w-xl h-full bg-background text-foreground shadow-2xl px-6 py-7 overflow-y-auto border-l border-border"
          >
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-xs tracking-wide text-muted-foreground mb-1 font-medium">
                  Configuration
                </p>
                <h2 className="text-2xl font-semibold m-0">Panel Settings</h2>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg w-10 h-10 border border-border flex items-center justify-center hover:bg-muted transition-colors text-xl"
                aria-label="Close configuration"
              >
                ×
              </button>
            </div>

            <section className="mt-8 space-y-4">
              <header>
                <h3 className="text-base font-semibold m-0">Provider API Keys</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Keys are stored locally in your browser and only used to fetch model lists.
                </p>
              </header>
              <div className="space-y-3">
                {PROVIDERS.map((provider) => {
                  const status = modelStatus[provider.id];
                  const keyValue = providerKeys[provider.id] ?? "";
                  return (
                    <div key={provider.id} className="rounded-lg border border-border p-4 bg-card">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="font-semibold m-0 text-foreground">{provider.label}</p>
                          <p className="text-xs text-muted-foreground m-0 mt-0.5">
                            {provider.description}
                          </p>
                        </div>
                        <a
                          href={provider.docs}
                          target="_blank"
                          rel="noreferrer"
                          className="text-xs text-accent hover:opacity-70 transition-opacity"
                        >
                          Docs ↗
                        </a>
                      </div>
                      <label className="mt-3 block text-xs tracking-wide text-muted-foreground font-medium">
                        API Key
                      </label>
                      <div className="mt-1.5 flex gap-2">
                        <div className="flex-1 relative">
                          <input
                            type={showKeys[provider.id] ? "text" : "password"}
                            value={keyValue}
                            onChange={(event) => onProviderKeyChange(provider.id, event.target.value)}
                            placeholder={provider.keyHint}
                            className="w-full rounded-lg border border-border bg-background px-3 py-2 pr-20 text-sm focus:outline-none focus:ring-2 focus:ring-accent/50"
                          />
                          <div className="absolute right-2 top-1/2 -translate-y-1/2 flex gap-1">
                            <button
                              type="button"
                              onClick={() => toggleKeyVisibility(provider.id)}
                              className="p-1.5 rounded hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
                              aria-label={showKeys[provider.id] ? "Hide API key" : "Show API key"}
                              title={showKeys[provider.id] ? "Hide API key" : "Show API key"}
                            >
                              {showKeys[provider.id] ? (
                                <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
                                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                                  <circle cx="12" cy="12" r="3" />
                                </svg>
                              ) : (
                                <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
                                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                                  <line x1="1" y1="1" x2="23" y2="23" />
                                </svg>
                              )}
                            </button>
                            <button
                              type="button"
                              onClick={() => copyToClipboard(provider.id, keyValue)}
                              disabled={!keyValue}
                              className="p-1.5 rounded hover:bg-muted transition-colors text-muted-foreground hover:text-foreground disabled:opacity-30 disabled:cursor-not-allowed"
                              aria-label="Copy API key"
                              title={copiedKey === provider.id ? "Copied!" : "Copy API key"}
                            >
                              {copiedKey === provider.id ? (
                                <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
                                  <polyline points="20 6 9 17 4 12" />
                                </svg>
                              ) : (
                                <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
                                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                                </svg>
                              )}
                            </button>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => onFetchModels(provider.id)}
                          disabled={!keyValue || status?.loading}
                          className="rounded-lg border-none bg-foreground text-background px-4 py-2 text-sm font-medium disabled:opacity-50 hover:opacity-90 transition-opacity"
                        >
                          {status?.loading ? "Fetching..." : "Fetch"}
                        </button>
                      </div>
                      {status?.error && (
                        <p className="text-sm text-destructive mt-2">{status.error}</p>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>

            {/* Presets Section */}
            <section className="mt-10 space-y-4">
              <header>
                <h3 className="text-base font-semibold m-0">Panelist Presets</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Save and load panelist configurations for quick setup
                </p>
              </header>

              {/* Load Preset */}
              <div className="flex gap-2">
                <select
                  value={selectedPresetId}
                  onChange={(e) => setSelectedPresetId(e.target.value)}
                  className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/50"
                >
                  <option value="">Select a preset...</option>
                  {presets.map((preset) => (
                    <option key={preset.id} value={preset.id}>
                      {preset.name} {preset.isDefault ? "(Default)" : ""}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={handleLoadPreset}
                  disabled={!selectedPresetId}
                  className="rounded-lg border-none bg-foreground text-background px-4 py-2 text-sm font-medium disabled:opacity-50 hover:opacity-90 transition-opacity"
                >
                  Load
                </button>
              </div>

              {/* Save Current as Preset */}
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setShowSavePreset(!showSavePreset)}
                  className="rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-muted transition-colors"
                >
                  {showSavePreset ? "Cancel" : "Save Current"}
                </button>
                <button
                  type="button"
                  onClick={() => setShowManagePresets(!showManagePresets)}
                  className="rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-muted transition-colors"
                >
                  {showManagePresets ? "Hide" : "Manage"}
                </button>
              </div>

              {/* Save Preset Form */}
              {showSavePreset && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="rounded-lg border border-border p-4 bg-card space-y-3"
                >
                  <div>
                    <label className="text-xs tracking-wide text-muted-foreground font-medium">
                      Preset Name
                    </label>
                    <input
                      type="text"
                      value={newPresetName}
                      onChange={(e) => setNewPresetName(e.target.value)}
                      placeholder="e.g., My Custom Panel"
                      className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/50"
                    />
                  </div>
                  <div>
                    <label className="text-xs tracking-wide text-muted-foreground font-medium">
                      Description (optional)
                    </label>
                    <input
                      type="text"
                      value={newPresetDescription}
                      onChange={(e) => setNewPresetDescription(e.target.value)}
                      placeholder="Brief description of this preset"
                      className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/50"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={handleSavePreset}
                    disabled={!newPresetName.trim()}
                    className="w-full rounded-lg border-none bg-foreground text-background px-4 py-2 text-sm font-medium disabled:opacity-50 hover:opacity-90 transition-opacity"
                  >
                    Save Preset
                  </button>
                </motion.div>
              )}

              {/* Manage Presets */}
              {showManagePresets && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="rounded-lg border border-border p-4 bg-card space-y-2"
                >
                  {presets.length === 0 && (
                    <p className="text-sm text-muted-foreground">No saved presets</p>
                  )}
                  {presets.map((preset) => (
                    <div
                      key={preset.id}
                      className="flex items-center justify-between gap-3 p-3 rounded border border-border/40 hover:bg-muted/20 transition-colors"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm m-0">
                          {preset.name}
                          {preset.isDefault && (
                            <span className="ml-2 text-xs text-muted-foreground">(Default)</span>
                          )}
                        </p>
                        {preset.description && (
                          <p className="text-xs text-muted-foreground m-0 mt-0.5 truncate">
                            {preset.description}
                          </p>
                        )}
                        <p className="text-xs text-muted-foreground m-0 mt-1">
                          {preset.panelists.length} panelist{preset.panelists.length !== 1 ? "s" : ""}
                        </p>
                      </div>
                      {!preset.isDefault && (
                        <button
                          type="button"
                          onClick={() => handleDeletePreset(preset.id)}
                          className="text-sm text-destructive hover:opacity-70 transition-opacity"
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  ))}
                </motion.div>
              )}
            </section>

            <section className="mt-10">
              <header className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="text-base font-semibold m-0">Panelists</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    Configure up to {maxPanelists} agents. Currently {panelists.length} active.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={onAddPanelist}
                  disabled={!canAddMore}
                  className="rounded-lg border border-border px-4 py-2 text-sm font-medium disabled:opacity-50 hover:bg-muted transition-colors"
                >
                  + Add panelist
                </button>
              </header>
              <div className="mt-4 space-y-3">
                {panelists.map((panelist) => {
                  const models = providerModels[panelist.provider] ?? [];
                  const status = modelStatus[panelist.provider];
                  return (
                    <div key={panelist.id} className="rounded-lg border border-border p-4 bg-card">
                      <div className="flex items-center justify-between gap-3">
                        <input
                          value={panelist.name}
                          onChange={(event) => onPanelistChange(panelist.id, { name: event.target.value })}
                          placeholder="Panelist name"
                          className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-base font-semibold text-foreground focus:outline-none focus:ring-2 focus:ring-accent/50"
                        />
                        <button
                          type="button"
                          onClick={() => onRemovePanelist(panelist.id)}
                          disabled={panelists.length <= 1}
                          className="text-sm text-destructive disabled:opacity-40 hover:opacity-70 transition-opacity"
                        >
                          Remove
                        </button>
                      </div>
                      <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                          <label className="text-xs tracking-wide text-muted-foreground font-medium">
                            Provider
                          </label>
                          <select
                            value={panelist.provider}
                            onChange={(event) =>
                              onPanelistChange(panelist.id, {
                                provider: event.target.value as LLMProvider,
                              })
                            }
                            className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/50"
                          >
                            {PROVIDERS.map((provider) => (
                              <option key={provider.id} value={provider.id}>
                                {provider.label}
                              </option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <label className="text-xs tracking-wide text-muted-foreground font-medium">
                            Model
                          </label>
                          <div className="mt-1.5 flex gap-2">
                            <select
                              value={panelist.model}
                              onChange={(event) =>
                                onPanelistChange(panelist.id, {
                                  model: event.target.value,
                                })
                              }
                              disabled={models.length === 0}
                              className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/50 disabled:opacity-60"
                            >
                              <option value="">
                                {models.length === 0 ? "Fetch models" : "Select model"}
                              </option>
                              {models.map((model) => {
                                const capabilities = getModelCapabilities(panelist.provider, model.id);
                                const badges = [];
                                if (capabilities.supportsVision) badges.push("📷");
                                if (capabilities.deprecated) badges.push("⚠️");
                                const badgeText = badges.length > 0 ? ` ${badges.join(" ")}` : "";

                                return (
                                  <option key={model.id} value={model.id}>
                                    {model.label}{badgeText}
                                  </option>
                                );
                              })}
                            </select>
                            <button
                              type="button"
                              onClick={() => onFetchModels(panelist.provider)}
                              disabled={status?.loading}
                              className="rounded-lg border border-border px-3 py-2 text-xs disabled:opacity-50 hover:bg-muted transition-colors"
                            >
                              ↻
                            </button>
                          </div>
                          {status?.error && (
                            <p className="text-xs text-destructive mt-1.5">
                              Unable to load models: {status.error}
                            </p>
                          )}
                          {panelist.model && (
                            <div className="mt-2 flex flex-wrap gap-1.5">
                              {(() => {
                                const capabilities = getModelCapabilities(panelist.provider, panelist.model);
                                return (
                                  <>
                                    {capabilities.supportsVision && (
                                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-accent/10 text-accent border border-accent/20">
                                        📷 Vision
                                      </span>
                                    )}
                                    {capabilities.deprecated && (
                                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-destructive/10 text-destructive border border-destructive/20">
                                        ⚠️ Deprecated
                                      </span>
                                    )}
                                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-muted/40 text-muted-foreground border border-border/40">
                                      {capabilities.tier === "flagship" && "🏆 Flagship"}
                                      {capabilities.tier === "standard" && "⭐ Standard"}
                                      {capabilities.tier === "fast" && "⚡ Fast"}
                                      {capabilities.tier === "legacy" && "📦 Legacy"}
                                    </span>
                                  </>
                                );
                              })()}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>

            <section className="mt-10 pb-4">
              <h4 className="text-sm font-semibold tracking-wide text-muted-foreground">
                Active Configuration
              </h4>
              <ul className="list-disc pl-5 text-sm text-foreground mt-2 space-y-1">
                {providerSummary.map((summary) => (
                  <li key={summary.id}>{summary.text}</li>
                ))}
              </ul>
            </section>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
