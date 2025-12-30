import { AnimatePresence, motion } from "framer-motion";
import { PROVIDERS, PROVIDER_LABELS } from "../lib/modelProviders";
import type {
  LLMProvider,
  PanelistConfigPayload,
  ProviderKeyMap,
  ProviderModelsMap,
  ProviderModelStatusMap,
} from "../types";
import { useMemo } from "react";

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
}: PanelConfiguratorProps) {
  const canAddMore = panelists.length < maxPanelists;

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
                        <input
                          type="password"
                          value={keyValue}
                          onChange={(event) => onProviderKeyChange(provider.id, event.target.value)}
                          placeholder={provider.keyHint}
                          className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/50"
                        />
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
                              {models.map((model) => (
                                <option key={model.id} value={model.id}>
                                  {model.label}
                                </option>
                              ))}
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
