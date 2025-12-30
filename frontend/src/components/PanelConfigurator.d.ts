import type { LLMProvider, PanelistConfigPayload, ProviderKeyMap, ProviderModelsMap, ProviderModelStatusMap } from "../types";
import { type PanelistPreset } from "../lib/presetManager";
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
export declare function PanelConfigurator({ open, onClose, panelists, onPanelistChange, onAddPanelist, onRemovePanelist, providerKeys, onProviderKeyChange, providerModels, modelStatus, onFetchModels, maxPanelists, onLoadPreset, }: PanelConfiguratorProps): import("react/jsx-runtime").JSX.Element;
export {};
