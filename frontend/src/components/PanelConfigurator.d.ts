import type { LLMProvider, PanelistConfigPayload, ProviderKeyMap, ProviderModelsMap, ProviderModelStatusMap } from "../types";
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
export declare function PanelConfigurator({ open, onClose, panelists, onPanelistChange, onAddPanelist, onRemovePanelist, providerKeys, onProviderKeyChange, providerModels, modelStatus, onFetchModels, maxPanelists, }: PanelConfiguratorProps): import("react/jsx-runtime").JSX.Element;
export {};
