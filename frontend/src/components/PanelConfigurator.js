import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { AnimatePresence, motion } from "framer-motion";
import { PROVIDERS, PROVIDER_LABELS } from "../lib/modelProviders";
import { useMemo, useState } from "react";
import { loadPresets, savePreset, deletePreset } from "../lib/presetManager";
import { getModelCapabilities } from "../lib/modelCapabilities";
import { validatePanelistName } from "../lib/panelistNaming";
export function PanelConfigurator({ open, onClose, panelists, onPanelistChange, onAddPanelist, onRemovePanelist, providerKeys, onProviderKeyChange, providerModels, modelStatus, onFetchModels, maxPanelists, onLoadPreset, }) {
    const canAddMore = panelists.length < maxPanelists;
    const [activeTab, setActiveTab] = useState("panelists");
    const [showKeys, setShowKeys] = useState({});
    const [copiedKey, setCopiedKey] = useState(null);
    const [presets, setPresets] = useState(() => loadPresets());
    const [selectedPresetId, setSelectedPresetId] = useState("");
    const [showSavePreset, setShowSavePreset] = useState(false);
    const [newPresetName, setNewPresetName] = useState("");
    const [newPresetDescription, setNewPresetDescription] = useState("");
    const [showManagePresets, setShowManagePresets] = useState(false);
    const [nameErrors, setNameErrors] = useState({});
    const toggleKeyVisibility = (providerId) => {
        setShowKeys((prev) => ({ ...prev, [providerId]: !prev[providerId] }));
    };
    const copyToClipboard = async (providerId, key) => {
        try {
            await navigator.clipboard.writeText(key);
            setCopiedKey(providerId);
            setTimeout(() => setCopiedKey(null), 2000);
        }
        catch (err) {
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
        if (!newPresetName.trim())
            return;
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
        }
        catch (err) {
            console.error("Failed to save preset:", err);
        }
    };
    const handleDeletePreset = (presetId) => {
        try {
            deletePreset(presetId);
            setPresets(loadPresets());
        }
        catch (err) {
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
    return (_jsx(AnimatePresence, { children: open && (_jsx(motion.div, { className: "fixed inset-0 z-50 flex items-center justify-center p-4 bg-foreground/20 backdrop-blur-sm", initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 }, onClick: onClose, children: _jsxs(motion.div, { initial: { scale: 0.95, opacity: 0 }, animate: { scale: 1, opacity: 1 }, exit: { scale: 0.95, opacity: 0 }, transition: { type: "spring", stiffness: 300, damping: 30 }, className: "w-full max-w-4xl max-h-[90vh] bg-background text-foreground shadow-2xl rounded-2xl border border-border flex flex-col", onClick: (e) => e.stopPropagation(), children: [_jsxs("div", { className: "flex items-center justify-between gap-4 px-6 py-5 border-b border-border", children: [_jsxs("div", { children: [_jsx("h2", { className: "text-xl font-semibold m-0", children: "Panel Settings" }), _jsx("p", { className: "text-xs text-muted-foreground mt-1", children: "Configure API keys, panelists, and presets" })] }), _jsx("button", { type: "button", onClick: onClose, className: "rounded-lg w-9 h-9 border border-border flex items-center justify-center hover:bg-muted transition-colors text-xl", "aria-label": "Close", children: "\u00D7" })] }), _jsxs("div", { className: "flex gap-1 px-6 pt-4 border-b border-border", children: [_jsx("button", { type: "button", onClick: () => setActiveTab("panelists"), className: `px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${activeTab === "panelists"
                                    ? "bg-accent/10 text-accent border-b-2 border-accent"
                                    : "text-muted-foreground hover:text-foreground hover:bg-muted/40"}`, children: "Panelists" }), _jsx("button", { type: "button", onClick: () => setActiveTab("presets"), className: `px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${activeTab === "presets"
                                    ? "bg-accent/10 text-accent border-b-2 border-accent"
                                    : "text-muted-foreground hover:text-foreground hover:bg-muted/40"}`, children: "Presets" }), _jsx("button", { type: "button", onClick: () => setActiveTab("api-keys"), className: `px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${activeTab === "api-keys"
                                    ? "bg-accent/10 text-accent border-b-2 border-accent"
                                    : "text-muted-foreground hover:text-foreground hover:bg-muted/40"}`, children: "API Keys" })] }), _jsxs("div", { className: "flex-1 overflow-y-auto px-6 py-6", children: [activeTab === "api-keys" && (_jsx("div", { children: _jsxs("section", { className: "space-y-4", children: [_jsxs("header", { children: [_jsx("h3", { className: "text-base font-semibold m-0", children: "Provider API Keys" }), _jsx("p", { className: "text-sm text-muted-foreground mt-1", children: "Keys are stored locally in your browser and only used to fetch model lists." })] }), _jsx("div", { className: "space-y-3", children: PROVIDERS.map((provider) => {
                                                const status = modelStatus[provider.id];
                                                const keyValue = providerKeys[provider.id] ?? "";
                                                return (_jsxs("div", { className: "rounded-lg border border-border p-4 bg-card", children: [_jsxs("div", { className: "flex items-center justify-between gap-3", children: [_jsxs("div", { children: [_jsx("p", { className: "font-semibold m-0 text-foreground", children: provider.label }), _jsx("p", { className: "text-xs text-muted-foreground m-0 mt-0.5", children: provider.description })] }), _jsx("a", { href: provider.docs, target: "_blank", rel: "noreferrer", className: "text-xs text-accent hover:opacity-70 transition-opacity", children: "Docs \u2197" })] }), _jsx("label", { className: "mt-3 block text-xs tracking-wide text-muted-foreground font-medium", children: "API Key" }), _jsxs("div", { className: "mt-1.5 flex gap-2", children: [_jsxs("div", { className: "flex-1 relative", children: [_jsx("input", { type: showKeys[provider.id] ? "text" : "password", value: keyValue, onChange: (event) => onProviderKeyChange(provider.id, event.target.value), placeholder: provider.keyHint, className: "w-full rounded-lg border border-border bg-background px-3 py-2 pr-20 text-sm focus:outline-none focus:ring-2 focus:ring-accent/50" }), _jsxs("div", { className: "absolute right-2 top-1/2 -translate-y-1/2 flex gap-1", children: [_jsx("button", { type: "button", onClick: () => toggleKeyVisibility(provider.id), className: "p-1.5 rounded hover:bg-muted transition-colors text-muted-foreground hover:text-foreground", "aria-label": showKeys[provider.id] ? "Hide API key" : "Show API key", title: showKeys[provider.id] ? "Hide API key" : "Show API key", children: showKeys[provider.id] ? (_jsxs("svg", { viewBox: "0 0 24 24", className: "w-4 h-4", fill: "none", stroke: "currentColor", strokeWidth: "2", children: [_jsx("path", { d: "M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" }), _jsx("circle", { cx: "12", cy: "12", r: "3" })] })) : (_jsxs("svg", { viewBox: "0 0 24 24", className: "w-4 h-4", fill: "none", stroke: "currentColor", strokeWidth: "2", children: [_jsx("path", { d: "M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" }), _jsx("line", { x1: "1", y1: "1", x2: "23", y2: "23" })] })) }), _jsx("button", { type: "button", onClick: () => copyToClipboard(provider.id, keyValue), disabled: !keyValue, className: "p-1.5 rounded hover:bg-muted transition-colors text-muted-foreground hover:text-foreground disabled:opacity-30 disabled:cursor-not-allowed", "aria-label": "Copy API key", title: copiedKey === provider.id ? "Copied!" : "Copy API key", children: copiedKey === provider.id ? (_jsx("svg", { viewBox: "0 0 24 24", className: "w-4 h-4", fill: "none", stroke: "currentColor", strokeWidth: "2", children: _jsx("polyline", { points: "20 6 9 17 4 12" }) })) : (_jsxs("svg", { viewBox: "0 0 24 24", className: "w-4 h-4", fill: "none", stroke: "currentColor", strokeWidth: "2", children: [_jsx("rect", { x: "9", y: "9", width: "13", height: "13", rx: "2", ry: "2" }), _jsx("path", { d: "M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" })] })) })] })] }), _jsx("button", { type: "button", onClick: () => onFetchModels(provider.id), disabled: !keyValue || status?.loading, className: "rounded-lg border-none bg-foreground text-background px-4 py-2 text-sm font-medium disabled:opacity-50 hover:opacity-90 transition-opacity", children: status?.loading ? "Fetching..." : "Fetch" })] }), status?.error && (_jsx("p", { className: "text-sm text-destructive mt-2", children: status.error }))] }, provider.id));
                                            }) })] }) })), activeTab === "presets" && (_jsx("div", { children: _jsxs("section", { className: "space-y-4", children: [_jsxs("header", { children: [_jsx("h3", { className: "text-base font-semibold m-0", children: "Panelist Presets" }), _jsx("p", { className: "text-sm text-muted-foreground mt-1", children: "Save and load panelist configurations for quick setup" })] }), _jsxs("div", { className: "flex gap-2", children: [_jsxs("select", { value: selectedPresetId, onChange: (e) => setSelectedPresetId(e.target.value), className: "flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/50", children: [_jsx("option", { value: "", children: "Select a preset..." }), presets.map((preset) => (_jsxs("option", { value: preset.id, children: [preset.name, " ", preset.isDefault ? "(Default)" : ""] }, preset.id)))] }), _jsx("button", { type: "button", onClick: handleLoadPreset, disabled: !selectedPresetId, className: "rounded-lg border-none bg-foreground text-background px-4 py-2 text-sm font-medium disabled:opacity-50 hover:opacity-90 transition-opacity", children: "Load" })] }), _jsxs("div", { className: "flex gap-2", children: [_jsx("button", { type: "button", onClick: () => setShowSavePreset(!showSavePreset), className: "rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-muted transition-colors", children: showSavePreset ? "Cancel" : "Save Current" }), _jsx("button", { type: "button", onClick: () => setShowManagePresets(!showManagePresets), className: "rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-muted transition-colors", children: showManagePresets ? "Hide" : "Manage" })] }), showSavePreset && (_jsxs(motion.div, { initial: { opacity: 0, height: 0 }, animate: { opacity: 1, height: "auto" }, exit: { opacity: 0, height: 0 }, className: "rounded-lg border border-border p-4 bg-card space-y-3", children: [_jsxs("div", { children: [_jsx("label", { className: "text-xs tracking-wide text-muted-foreground font-medium", children: "Preset Name" }), _jsx("input", { type: "text", value: newPresetName, onChange: (e) => setNewPresetName(e.target.value), placeholder: "e.g., My Custom Panel", className: "mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/50" })] }), _jsxs("div", { children: [_jsx("label", { className: "text-xs tracking-wide text-muted-foreground font-medium", children: "Description (optional)" }), _jsx("input", { type: "text", value: newPresetDescription, onChange: (e) => setNewPresetDescription(e.target.value), placeholder: "Brief description of this preset", className: "mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/50" })] }), _jsx("button", { type: "button", onClick: handleSavePreset, disabled: !newPresetName.trim(), className: "w-full rounded-lg border-none bg-foreground text-background px-4 py-2 text-sm font-medium disabled:opacity-50 hover:opacity-90 transition-opacity", children: "Save Preset" })] })), showManagePresets && (_jsxs(motion.div, { initial: { opacity: 0, height: 0 }, animate: { opacity: 1, height: "auto" }, exit: { opacity: 0, height: 0 }, className: "rounded-lg border border-border p-4 bg-card space-y-2", children: [presets.length === 0 && (_jsx("p", { className: "text-sm text-muted-foreground", children: "No saved presets" })), presets.map((preset) => (_jsxs("div", { className: "flex items-center justify-between gap-3 p-3 rounded border border-border/40 hover:bg-muted/20 transition-colors", children: [_jsxs("div", { className: "flex-1 min-w-0", children: [_jsxs("p", { className: "font-medium text-sm m-0", children: [preset.name, preset.isDefault && (_jsx("span", { className: "ml-2 text-xs text-muted-foreground", children: "(Default)" }))] }), preset.description && (_jsx("p", { className: "text-xs text-muted-foreground m-0 mt-0.5 truncate", children: preset.description })), _jsxs("p", { className: "text-xs text-muted-foreground m-0 mt-1", children: [preset.panelists.length, " panelist", preset.panelists.length !== 1 ? "s" : ""] })] }), !preset.isDefault && (_jsx("button", { type: "button", onClick: () => handleDeletePreset(preset.id), className: "text-sm text-destructive hover:opacity-70 transition-opacity", children: "Delete" }))] }, preset.id)))] }))] }) })), activeTab === "panelists" && (_jsxs("div", { children: [_jsxs("section", { children: [_jsxs("header", { className: "flex flex-wrap items-center justify-between gap-3", children: [_jsxs("div", { children: [_jsx("h3", { className: "text-base font-semibold m-0", children: "Panelists" }), _jsxs("p", { className: "text-sm text-muted-foreground mt-1", children: ["Configure up to ", maxPanelists, " agents. Currently ", panelists.length, " active."] })] }), _jsx("button", { type: "button", onClick: onAddPanelist, disabled: !canAddMore, className: "rounded-lg border border-border px-4 py-2 text-sm font-medium disabled:opacity-50 hover:bg-muted transition-colors", children: "+ Add panelist" })] }), _jsx("div", { className: "mt-4 space-y-3", children: panelists.map((panelist) => {
                                                    const models = providerModels[panelist.provider] ?? [];
                                                    const status = modelStatus[panelist.provider];
                                                    return (_jsxs("div", { className: "rounded-lg border border-border p-4 bg-card", children: [_jsxs("div", { className: "flex items-center justify-between gap-3", children: [_jsxs("div", { className: "flex-1", children: [_jsx("input", { value: panelist.name, onChange: (event) => {
                                                                                    const newName = event.target.value;
                                                                                    onPanelistChange(panelist.id, { name: newName });
                                                                                    const error = validatePanelistName(newName);
                                                                                    setNameErrors(prev => ({ ...prev, [panelist.id]: error }));
                                                                                }, placeholder: "Panelist name (no spaces)", className: `w-full rounded-lg border ${nameErrors[panelist.id] ? 'border-destructive focus:ring-destructive/50' : 'border-border focus:ring-accent/50'} bg-background px-3 py-2 text-base font-semibold text-foreground focus:outline-none focus:ring-2` }), nameErrors[panelist.id] && (_jsxs("p", { className: "text-xs text-destructive mt-1 flex items-center gap-1", children: [_jsxs("svg", { viewBox: "0 0 24 24", className: "w-3 h-3", fill: "none", stroke: "currentColor", strokeWidth: "2", children: [_jsx("circle", { cx: "12", cy: "12", r: "10" }), _jsx("line", { x1: "12", y1: "8", x2: "12", y2: "12" }), _jsx("line", { x1: "12", y1: "16", x2: "12.01", y2: "16" })] }), nameErrors[panelist.id]] }))] }), _jsx("button", { type: "button", onClick: () => onRemovePanelist(panelist.id), disabled: panelists.length <= 1, className: "text-sm text-destructive disabled:opacity-40 hover:opacity-70 transition-opacity", children: "Remove" })] }), _jsxs("div", { className: "mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3", children: [_jsxs("div", { children: [_jsx("label", { className: "text-xs tracking-wide text-muted-foreground font-medium", children: "Provider" }), _jsx("select", { value: panelist.provider, onChange: (event) => onPanelistChange(panelist.id, {
                                                                                    provider: event.target.value,
                                                                                }), className: "mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/50", children: PROVIDERS.map((provider) => (_jsx("option", { value: provider.id, children: provider.label }, provider.id))) })] }), _jsxs("div", { children: [_jsx("label", { className: "text-xs tracking-wide text-muted-foreground font-medium", children: "Model" }), _jsx("div", { className: "mt-1.5", children: _jsxs("select", { value: panelist.model, onChange: (event) => onPanelistChange(panelist.id, {
                                                                                        model: event.target.value,
                                                                                    }), disabled: models.length === 0, className: "w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/50 disabled:opacity-60", children: [_jsx("option", { value: "", children: models.length === 0 ? "Select provider first" : "Select model" }), models.map((model) => {
                                                                                            const capabilities = getModelCapabilities(panelist.provider, model.id);
                                                                                            const badges = [];
                                                                                            if (capabilities.supportsVision)
                                                                                                badges.push("📷");
                                                                                            if (capabilities.deprecated)
                                                                                                badges.push("⚠️");
                                                                                            const badgeText = badges.length > 0 ? ` ${badges.join(" ")}` : "";
                                                                                            return (_jsxs("option", { value: model.id, children: [model.label, badgeText] }, model.id));
                                                                                        })] }) }), status?.error && (_jsxs("p", { className: "text-xs text-destructive mt-1.5", children: ["Unable to load models: ", status.error] })), panelist.model && (_jsx("div", { className: "mt-2 flex flex-wrap gap-1.5", children: (() => {
                                                                                    const capabilities = getModelCapabilities(panelist.provider, panelist.model);
                                                                                    return (_jsxs(_Fragment, { children: [capabilities.supportsVision && (_jsx("span", { className: "inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-accent/10 text-accent border border-accent/20", children: "\uD83D\uDCF7 Vision" })), capabilities.deprecated && (_jsx("span", { className: "inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-destructive/10 text-destructive border border-destructive/20", children: "\u26A0\uFE0F Deprecated" })), _jsxs("span", { className: "inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-muted/40 text-muted-foreground border border-border/40", children: [capabilities.tier === "flagship" && "🏆 Flagship", capabilities.tier === "standard" && "⭐ Standard", capabilities.tier === "fast" && "⚡ Fast", capabilities.tier === "legacy" && "📦 Legacy"] })] }));
                                                                                })() }))] })] })] }, panelist.id));
                                                }) })] }), _jsxs("section", { className: "mt-10 pb-4", children: [_jsx("h4", { className: "text-sm font-semibold tracking-wide text-muted-foreground", children: "Active Configuration" }), _jsx("ul", { className: "list-disc pl-5 text-sm text-foreground mt-2 space-y-1", children: providerSummary.map((summary) => (_jsx("li", { children: summary.text }, summary.id))) })] })] }))] })] }) })) }));
}
