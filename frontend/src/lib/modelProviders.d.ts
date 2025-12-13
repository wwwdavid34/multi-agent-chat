import type { LLMProvider, ProviderModel } from "../types";
export interface ProviderMeta {
    id: LLMProvider;
    label: string;
    description: string;
    docs: string;
    keyHint: string;
}
export declare const PROVIDERS: ProviderMeta[];
export declare const PROVIDER_LABELS: Record<LLMProvider, string>;
export declare function fetchModelsForProvider(provider: LLMProvider, apiKey: string): Promise<ProviderModel[]>;
