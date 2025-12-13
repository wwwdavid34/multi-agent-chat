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
          <div className="flex-1 bg-slate-950/30 backdrop-blur-sm" onClick={onClose} />
          <motion.div
            initial={{ x: 420 }}
            animate={{ x: 0 }}
            exit={{ x: 420 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="w-full max-w-xl h-full bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 shadow-2xl px-6 py-7 overflow-y-auto"
          >
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-widest text-slate-500 dark:text-slate-400 mb-1">
                  Panel configuration
                </p>
                <h2 className="text-2xl font-semibold m-0">LLM panel controls</h2>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="rounded-full w-10 h-10 border border-slate-300 dark:border-slate-700 flex items-center justify-center hover:bg-slate-100 dark:hover:bg-slate-800"
                aria-label="Close configuration"
              >
                ×
              </button>
            </div>

            <section className="mt-8 space-y-4">
              <header>
                <h3 className="text-base font-semibold m-0">Provider API keys</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Keys are stored locally in your browser and only used to fetch model lists.
                </p>
              </header>
              <div className="space-y-4">
                {PROVIDERS.map((provider) => {
                  const status = modelStatus[provider.id];
                  const keyValue = providerKeys[provider.id] ?? "";
                  return (
                    <div key={provider.id} className="rounded-2xl border border-slate-200 dark:border-slate-800 p-4 bg-white/70 dark:bg-slate-900/40">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="font-semibold m-0">{provider.label}</p>
                          <p className="text-xs text-slate-500 dark:text-slate-400 m-0">
                            {provider.description}
                          </p>
                        </div>
                        <a
                          href={provider.docs}
                          target="_blank"
                          rel="noreferrer"
                          className="text-xs text-blue-600 dark:text-blue-400"
                        >
                          Docs ↗
                        </a>
                      </div>
                      <label className="mt-3 block text-xs uppercase tracking-wider text-slate-500 dark:text-slate-400">
                        API key
                      </label>
                      <div className="mt-1 flex gap-2">
                        <input
                          type="password"
                          value={keyValue}
                          onChange={(event) => onProviderKeyChange(provider.id, event.target.value)}
                          placeholder={provider.keyHint}
                          className="flex-1 rounded-xl border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2"
                        />
                        <button
                          type="button"
                          onClick={() => onFetchModels(provider.id)}
                          disabled={!keyValue || status?.loading}
                          className="rounded-xl border-none bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 px-4 py-2 text-sm font-semibold disabled:opacity-60"
                        >
                          {status?.loading ? "Fetching..." : "Fetch"}
                        </button>
                      </div>
                      {status?.error && (
                        <p className="text-sm text-red-600 mt-2">{status.error}</p>
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
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    Configure up to {maxPanelists} agents. Currently {panelists.length} active.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={onAddPanelist}
                  disabled={!canAddMore}
                  className="rounded-full border border-slate-300 dark:border-slate-700 px-4 py-2 text-sm font-semibold disabled:opacity-60"
                >
                  + Add panelist
                </button>
              </header>
              <div className="mt-4 space-y-4">
                {panelists.map((panelist) => {
                  const models = providerModels[panelist.provider] ?? [];
                  const status = modelStatus[panelist.provider];
                  return (
                    <div key={panelist.id} className="rounded-2xl border border-slate-200 dark:border-slate-800 p-4 bg-white/80 dark:bg-slate-900/40">
                      <div className="flex items-center justify-between gap-3">
                        <input
                          value={panelist.name}
                          onChange={(event) => onPanelistChange(panelist.id, { name: event.target.value })}
                          placeholder="Panelist name"
                          className="flex-1 rounded-xl border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2 text-base font-semibold"
                        />
                        <button
                          type="button"
                          onClick={() => onRemovePanelist(panelist.id)}
                          disabled={panelists.length <= 1}
                          className="text-sm text-red-600 disabled:opacity-40"
                        >
                          Remove
                        </button>
                      </div>
                      <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                          <label className="text-xs uppercase tracking-wider text-slate-500 dark:text-slate-400">
                            Provider
                          </label>
                          <select
                            value={panelist.provider}
                            onChange={(event) =>
                              onPanelistChange(panelist.id, {
                                provider: event.target.value as LLMProvider,
                              })
                            }
                            className="mt-1 w-full rounded-xl border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2"
                          >
                            {PROVIDERS.map((provider) => (
                              <option key={provider.id} value={provider.id}>
                                {provider.label}
                              </option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <label className="text-xs uppercase tracking-wider text-slate-500 dark:text-slate-400">
                            Model
                          </label>
                          <div className="mt-1 flex gap-2">
                            <select
                              value={panelist.model}
                              onChange={(event) =>
                                onPanelistChange(panelist.id, {
                                  model: event.target.value,
                                })
                              }
                              disabled={models.length === 0}
                              className="flex-1 rounded-xl border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2"
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
                              className="rounded-xl border border-slate-300 dark:border-slate-700 px-3 py-2 text-xs disabled:opacity-50"
                            >
                              Refresh
                            </button>
                          </div>
                          {status?.error && (
                            <p className="text-xs text-red-600 mt-1">
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

            <section className="mt-10">
              <h4 className="text-sm font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Current plan
              </h4>
              <ul className="list-disc pl-5 text-sm text-slate-600 dark:text-slate-400 mt-2 space-y-1">
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
