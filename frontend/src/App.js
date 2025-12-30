import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { askPanelStream } from "./api";
import { Markdown } from "./components/Markdown";
import { PanelConfigurator } from "./components/PanelConfigurator";
import { ThemeToggle } from "./components/theme-toggle";
import { fetchModelsForProvider, PROVIDER_LABELS } from "./lib/modelProviders";
const DEFAULT_THREAD_ID = "demo-thread";
const parseJSON = (value, fallback) => {
    try {
        return value ? JSON.parse(value) : fallback;
    }
    catch {
        return fallback;
    }
};
const MAX_PANELISTS = 6;
const DEFAULT_PANELISTS = [
    { id: "panelist-1", name: "Panelist 1", provider: "openai", model: "" },
    { id: "panelist-2", name: "Panelist 2", provider: "openai", model: "" },
];
const createPanelist = (index) => ({
    id: `panelist-${Date.now()}-${Math.random().toString(16).slice(2, 7)}`,
    name: `Panelist ${index}`,
    provider: "openai",
    model: "",
});
const MessageBubble = memo(function MessageBubble({ entry, onToggle, isLatest = false, messageRef, loadingStatus = "Panel is thinking..." }) {
    return (_jsxs(motion.article, { ref: messageRef, className: "flex flex-col gap-7 min-w-0", initial: { opacity: 0, y: 8 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] }, children: [_jsxs("div", { className: "flex flex-col items-end self-end text-right gap-2 w-full max-w-[88%] sm:max-w-[68%]", children: [_jsx("span", { className: "text-[11px] font-medium tracking-wider uppercase text-muted-foreground/70 px-1", children: "You" }), _jsxs(motion.div, { className: "w-full bg-foreground text-background rounded-[20px] rounded-br-sm p-6 shadow-sm break-words", initial: { opacity: 0, x: 20 }, animate: { opacity: 1, x: 0 }, transition: { duration: 0.4, delay: 0.1, ease: [0.16, 1, 0.3, 1] }, children: [_jsx(Markdown, { content: entry.question }), entry.attachments.length > 0 && (_jsx("div", { className: "mt-4 flex flex-wrap gap-2.5", children: entry.attachments.map((src, index) => (_jsx(motion.img, { src: src, alt: `attachment-${index + 1}`, className: "w-20 h-20 object-cover rounded-xl border-2 border-background/30 shadow-sm", initial: { opacity: 0, scale: 0.8 }, animate: { opacity: 1, scale: 1 }, transition: { duration: 0.3, delay: 0.2 + index * 0.05 } }, index))) }))] })] }), _jsxs("div", { className: "flex flex-col items-start self-start text-left gap-2 w-full max-w-[88%] sm:max-w-[78%]", children: [_jsx("span", { className: "text-[11px] font-medium tracking-wider uppercase text-muted-foreground/70 px-1", children: "Panel" }), _jsx(motion.div, { className: "w-full bg-card border border-border/60 rounded-[20px] rounded-bl-sm shadow-sm p-6 break-words", initial: { opacity: 0, x: -20 }, animate: { opacity: 1, x: 0 }, transition: { duration: 0.4, delay: 0.2, ease: [0.16, 1, 0.3, 1] }, children: entry.summary ? (_jsxs(_Fragment, { children: [_jsx("div", { className: "prose prose-sm dark:prose-invert max-w-none", children: _jsx(Markdown, { content: entry.summary }) }), _jsxs("button", { type: "button", className: "mt-5 inline-flex items-center gap-2 text-[13px] font-medium bg-transparent text-accent/90 border-none p-0 cursor-pointer hover:text-accent transition-colors", onClick: onToggle, children: [entry.expanded ? "Hide individual responses" : "Show individual responses", _jsx("svg", { viewBox: "0 0 24 24", "aria-hidden": "true", className: `w-3.5 h-3.5 transition-transform duration-200 ${entry.expanded ? "rotate-180" : ""}`, children: _jsx("path", { fill: "currentColor", d: "M7 10l5 5 5-5z" }) })] }), _jsx(AnimatePresence, { children: entry.expanded && (_jsx(motion.div, { className: "mt-6 border-t border-border/50 pt-6 grid gap-4", initial: { opacity: 0, height: 0 }, animate: { opacity: 1, height: "auto" }, exit: { opacity: 0, height: 0 }, transition: { duration: 0.3, ease: [0.16, 1, 0.3, 1] }, children: Object.entries(entry.panel_responses).map(([name, text], idx) => (_jsxs(motion.article, { className: "border border-border/40 rounded-2xl p-5 bg-muted/20", initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.3, delay: idx * 0.05 }, children: [_jsx("h4", { className: "m-0 mb-3 text-foreground text-[13px] font-semibold tracking-wide", children: name }), _jsx("div", { className: "text-[13px] leading-relaxed text-muted-foreground", children: _jsx(Markdown, { content: text }) })] }, name))) })) })] })) : (_jsxs("div", { className: "flex items-center gap-3", children: [_jsxs(motion.div, { className: "flex gap-1.5", initial: { opacity: 0 }, animate: { opacity: 1 }, transition: { duration: 0.3 }, children: [_jsx(motion.div, { className: "w-2 h-2 rounded-full bg-muted-foreground/40", animate: { scale: [1, 1.2, 1], opacity: [0.4, 0.8, 0.4] }, transition: { duration: 1.2, repeat: Infinity, delay: 0 } }), _jsx(motion.div, { className: "w-2 h-2 rounded-full bg-muted-foreground/40", animate: { scale: [1, 1.2, 1], opacity: [0.4, 0.8, 0.4] }, transition: { duration: 1.2, repeat: Infinity, delay: 0.2 } }), _jsx(motion.div, { className: "w-2 h-2 rounded-full bg-muted-foreground/40", animate: { scale: [1, 1.2, 1], opacity: [0.4, 0.8, 0.4] }, transition: { duration: 1.2, repeat: Infinity, delay: 0.4 } })] }), _jsx("span", { className: "text-[13px] text-muted-foreground/60", children: loadingStatus })] })) })] })] }));
});
MessageBubble.displayName = "MessageBubble";
export default function App() {
    const [threadId, setThreadId] = useState(() => localStorage.getItem("threadId") ?? DEFAULT_THREAD_ID);
    const [threads, setThreads] = useState(() => {
        const stored = parseJSON(localStorage.getItem("threads"), []);
        if (!stored.includes(DEFAULT_THREAD_ID)) {
            stored.unshift(DEFAULT_THREAD_ID);
        }
        return Array.from(new Set(stored));
    });
    const [conversations, setConversations] = useState(() => {
        const raw = parseJSON(localStorage.getItem("conversations"), {});
        const normalized = {};
        Object.entries(raw).forEach(([id, entries]) => {
            normalized[id] = (entries ?? []).map((entry) => ({
                ...entry,
                attachments: entry.attachments ?? [],
                panel_responses: entry.panel_responses ?? {},
                expanded: Boolean(entry.expanded),
            }));
        });
        if (!normalized[DEFAULT_THREAD_ID]) {
            normalized[DEFAULT_THREAD_ID] = [];
        }
        return normalized;
    });
    const [newThreadName, setNewThreadName] = useState("");
    const [isCreatingThread, setIsCreatingThread] = useState(false);
    const [panelists, setPanelists] = useState(() => {
        const stored = parseJSON(localStorage.getItem("panelists"), DEFAULT_PANELISTS);
        return stored.length > 0 ? stored : DEFAULT_PANELISTS;
    });
    const [providerKeys, setProviderKeys] = useState(() => parseJSON(localStorage.getItem("providerKeys"), {}));
    const [providerModels, setProviderModels] = useState(() => parseJSON(localStorage.getItem("providerModels"), {}));
    const [modelStatus, setModelStatus] = useState({});
    const [configOpen, setConfigOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const [loadingStatus, setLoadingStatus] = useState("Panel is thinking...");
    const [error, setError] = useState(null);
    const [showScrollToBottom, setShowScrollToBottom] = useState(false);
    const newThreadInputRef = useRef(null);
    const messageListRef = useRef(null);
    const latestMessageRef = useRef(null);
    const messages = conversations[threadId] ?? [];
    // Auto-scroll to latest message when messages change
    useEffect(() => {
        if (latestMessageRef.current && messages.length > 0) {
            // Small delay to allow DOM to update
            setTimeout(() => {
                latestMessageRef.current?.scrollIntoView({
                    behavior: "smooth",
                    block: "end"
                });
            }, 100);
        }
    }, [messages.length]);
    useEffect(() => {
        localStorage.setItem("threadId", threadId);
    }, [threadId]);
    useEffect(() => {
        localStorage.setItem("threads", JSON.stringify(threads));
    }, [threads]);
    useEffect(() => {
        localStorage.setItem("conversations", JSON.stringify(conversations));
    }, [conversations]);
    useEffect(() => {
        localStorage.setItem("panelists", JSON.stringify(panelists));
    }, [panelists]);
    useEffect(() => {
        localStorage.setItem("providerKeys", JSON.stringify(providerKeys));
    }, [providerKeys]);
    useEffect(() => {
        localStorage.setItem("providerModels", JSON.stringify(providerModels));
    }, [providerModels]);
    useEffect(() => {
        if (!threads.includes(threadId)) {
            setThreads((prev) => Array.from(new Set([...prev, threadId])));
        }
        if (!conversations[threadId]) {
            setConversations((prev) => ({ ...prev, [threadId]: [] }));
        }
    }, [threadId, threads, conversations]);
    useEffect(() => {
        if (isCreatingThread) {
            const frame = requestAnimationFrame(() => newThreadInputRef.current?.focus());
            return () => cancelAnimationFrame(frame);
        }
    }, [isCreatingThread]);
    const preparedPanelists = useMemo(() => panelists.map((panelist, index) => ({
        ...panelist,
        name: panelist.name.trim() || `Panelist ${index + 1}`,
    })), [panelists]);
    const panelistSummaries = useMemo(() => preparedPanelists.map((panelist) => ({
        id: panelist.id,
        name: panelist.name,
        provider: PROVIDER_LABELS[panelist.provider],
        model: panelist.model,
    })), [preparedPanelists]);
    const sanitizedProviderKeys = useMemo(() => {
        const entries = Object.entries(providerKeys).filter(([, value]) => Boolean(value?.trim()));
        return Object.fromEntries(entries.map(([key, value]) => [key, value.trim()]));
    }, [providerKeys]);
    const handleSend = useCallback(async ({ question, attachments }) => {
        const hasContent = Boolean(question.trim()) || attachments.length > 0;
        if (!hasContent || loading) {
            return;
        }
        setLoading(true);
        setError(null);
        const sanitizedQuestion = question.trim() || "See attached images.";
        const entryId = `${threadId}-${Date.now()}`;
        // Immediately add user message with loading state for assistant response
        const optimisticEntry = {
            id: entryId,
            question: sanitizedQuestion,
            attachments,
            summary: "", // Will be filled when response arrives
            panel_responses: {},
            expanded: false,
        };
        setConversations((prev) => ({
            ...prev,
            [threadId]: [...(prev[threadId] ?? []), optimisticEntry],
        }));
        try {
            await askPanelStream({
                thread_id: threadId.trim(),
                question: sanitizedQuestion,
                attachments,
                panelists: preparedPanelists,
                provider_keys: sanitizedProviderKeys,
            }, {
                onStatus: (message) => {
                    setLoadingStatus(message);
                },
                onResult: (result) => {
                    // Update the entry with the actual response
                    setConversations((prev) => ({
                        ...prev,
                        [threadId]: prev[threadId]?.map((entry) => entry.id === entryId
                            ? {
                                ...entry,
                                summary: result.summary,
                                panel_responses: result.panel_responses,
                            }
                            : entry) ?? [],
                    }));
                },
                onError: (err) => {
                    // Remove the optimistic entry on error
                    setConversations((prev) => ({
                        ...prev,
                        [threadId]: prev[threadId]?.filter((entry) => entry.id !== entryId) ?? [],
                    }));
                    setError(err.message);
                    setLoading(false);
                    setLoadingStatus("Panel is thinking..."); // Reset status
                },
            });
        }
        catch (err) {
            // Remove the optimistic entry on error
            setConversations((prev) => ({
                ...prev,
                [threadId]: prev[threadId]?.filter((entry) => entry.id !== entryId) ?? [],
            }));
            setError(err instanceof Error ? err.message : "Something went wrong");
            throw err;
        }
        finally {
            setLoading(false);
            setLoadingStatus("Panel is thinking..."); // Reset status
        }
    }, [loading, preparedPanelists, sanitizedProviderKeys, threadId]);
    const handleScrollToBottom = useCallback(() => {
        const el = messageListRef.current;
        if (!el)
            return;
        el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
        setShowScrollToBottom(false);
    }, []);
    // Track scroll position for showing/hiding scroll button
    useEffect(() => {
        function handleScroll() {
            const el = messageListRef.current;
            if (!el)
                return;
            const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
            setShowScrollToBottom(distanceFromBottom > 300);
        }
        handleScroll();
        const el = messageListRef.current;
        if (!el)
            return;
        el.addEventListener("scroll", handleScroll);
        return () => el.removeEventListener("scroll", handleScroll);
    }, []);
    function toggleEntry(index) {
        setConversations((prev) => ({
            ...prev,
            [threadId]: prev[threadId]?.map((item, i) => i === index ? { ...item, expanded: !item.expanded } : item) ?? [],
        }));
    }
    function handleThreadSelect(id) {
        setThreadId(id);
    }
    function handleRenameThread(id) {
        const proposed = prompt("Rename thread", id)?.trim();
        if (!proposed || proposed === id || threads.includes(proposed)) {
            return;
        }
        setThreads((prev) => prev.map((thread) => (thread === id ? proposed : thread)));
        setConversations((prev) => {
            const { [id]: entries, ...rest } = prev;
            return { ...rest, [proposed]: entries ?? [] };
        });
        if (threadId === id) {
            setThreadId(proposed);
        }
    }
    function handleDeleteThread(id) {
        if (threads.length === 1) {
            return;
        }
        setThreads((prev) => prev.filter((thread) => thread !== id));
        setConversations((prev) => {
            const { [id]: _removed, ...rest } = prev;
            return rest;
        });
        if (threadId === id) {
            const fallback = threads.find((thread) => thread !== id) ?? DEFAULT_THREAD_ID;
            setThreadId(fallback);
        }
    }
    function handleCreateThread(event) {
        event.preventDefault();
        const trimmed = newThreadName.trim();
        if (!trimmed)
            return;
        setThreads((prev) => (prev.includes(trimmed) ? prev : [...prev, trimmed]));
        setConversations((prev) => (prev[trimmed] ? prev : { ...prev, [trimmed]: [] }));
        setThreadId(trimmed);
        setNewThreadName("");
        setIsCreatingThread(false);
    }
    function cancelThreadCreation() {
        setIsCreatingThread(false);
        setNewThreadName("");
    }
    function handleThreadInputKeyDown(event) {
        if (event.key === "Escape") {
            event.preventDefault();
            cancelThreadCreation();
        }
    }
    const handlePanelistChange = useCallback((id, updates) => {
        setPanelists((prev) => prev.map((panelist) => {
            if (panelist.id !== id)
                return panelist;
            const nextProvider = updates.provider ?? panelist.provider;
            const providerModelsList = providerModels[nextProvider] ?? [];
            let nextModel = updates.model ?? panelist.model;
            if (updates.provider && updates.provider !== panelist.provider) {
                nextModel = providerModelsList[0]?.id ?? "";
            }
            return {
                ...panelist,
                ...updates,
                provider: nextProvider,
                model: nextModel,
                name: updates.name ?? panelist.name,
            };
        }));
    }, [providerModels]);
    const handleAddPanelist = useCallback(() => {
        setPanelists((prev) => {
            if (prev.length >= MAX_PANELISTS)
                return prev;
            const index = prev.length + 1;
            const base = createPanelist(index);
            const defaultModel = providerModels[base.provider]?.[0]?.id ?? "";
            return [...prev, { ...base, model: defaultModel }];
        });
    }, [providerModels]);
    const handleRemovePanelist = useCallback((id) => {
        setPanelists((prev) => {
            if (prev.length <= 1) {
                return prev;
            }
            const filtered = prev.filter((panelist) => panelist.id !== id);
            return filtered.length > 0 ? filtered : prev;
        });
    }, []);
    const handleProviderKeyChange = useCallback((provider, key) => {
        setProviderKeys((prev) => ({ ...prev, [provider]: key }));
    }, []);
    const handleFetchProviderModels = useCallback(async (provider) => {
        const apiKey = providerKeys[provider]?.trim();
        if (!apiKey) {
            setModelStatus((prev) => ({
                ...prev,
                [provider]: { loading: false, error: "API key required" },
            }));
            return;
        }
        setModelStatus((prev) => ({
            ...prev,
            [provider]: { loading: true, error: null },
        }));
        try {
            const models = await fetchModelsForProvider(provider, apiKey);
            setProviderModels((prev) => ({ ...prev, [provider]: models }));
            setModelStatus((prev) => ({
                ...prev,
                [provider]: { loading: false, error: null },
            }));
            setPanelists((prev) => prev.map((panelist) => {
                if (panelist.provider !== provider)
                    return panelist;
                if (!models.length) {
                    return { ...panelist, model: "" };
                }
                const hasModel = models.some((model) => model.id === panelist.model);
                return hasModel ? panelist : { ...panelist, model: models[0].id };
            }));
        }
        catch (err) {
            setModelStatus((prev) => ({
                ...prev,
                [provider]: {
                    loading: false,
                    error: err instanceof Error ? err.message : "Failed to fetch models",
                },
            }));
        }
    }, [providerKeys]);
    return (_jsxs("div", { className: "flex h-screen w-full overflow-hidden bg-background", children: [_jsxs("aside", { className: "hidden lg:flex w-72 flex-shrink-0 bg-card px-6 py-8 flex-col gap-6 overflow-y-auto border-r border-border/60", children: [_jsxs("div", { className: "flex items-center justify-between gap-3", children: [_jsx("h2", { className: "text-lg font-semibold m-0 text-foreground tracking-tight", children: "Conversations" }), _jsx("button", { type: "button", className: "w-8 h-8 rounded-lg border border-border/60 bg-muted/30 text-foreground text-lg font-semibold leading-none flex items-center justify-center cursor-pointer hover:bg-muted hover:border-accent/50 transition-all", onClick: () => {
                                    setIsCreatingThread(true);
                                    setNewThreadName("");
                                }, "aria-label": "Create new thread", children: "+" })] }), _jsx("ul", { className: "list-none p-0 m-0 flex flex-col gap-1.5 overflow-y-auto flex-1", children: threads.map((id) => (_jsx("li", { className: "group", children: _jsxs("div", { className: "flex items-center gap-1.5 relative", children: [_jsx("button", { type: "button", className: `flex-1 flex items-center justify-between px-3.5 py-2 rounded-lg border text-[13px] transition-all ${threadId === id
                                            ? "border-accent/60 bg-accent/8 text-accent font-medium"
                                            : "border-border/40 bg-transparent font-normal text-foreground hover:bg-muted/30 hover:border-border"}`, onClick: () => handleThreadSelect(id), children: _jsx("span", { className: "truncate", children: id }) }), _jsxs("div", { className: "flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200", children: [_jsx("button", { type: "button", onClick: () => handleRenameThread(id), "aria-label": "Rename thread", className: "border-none bg-muted/40 hover:bg-muted cursor-pointer p-1.5 rounded-md transition-colors", children: _jsxs("svg", { viewBox: "0 0 24 24", className: "w-3.5 h-3.5 text-foreground/70", fill: "none", stroke: "currentColor", strokeWidth: "2", children: [_jsx("path", { d: "M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" }), _jsx("path", { d: "M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" })] }) }), _jsx("button", { type: "button", onClick: () => handleDeleteThread(id), "aria-label": "Delete thread", className: "border-none bg-muted/40 hover:bg-destructive/10 cursor-pointer p-1.5 rounded-md transition-colors group/delete", children: _jsxs("svg", { viewBox: "0 0 24 24", className: "w-3.5 h-3.5 text-foreground/70 group-hover/delete:text-destructive transition-colors", fill: "none", stroke: "currentColor", strokeWidth: "2", children: [_jsx("path", { d: "M3 6h18" }), _jsx("path", { d: "M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" }), _jsx("path", { d: "M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" }), _jsx("line", { x1: "10", y1: "11", x2: "10", y2: "17" }), _jsx("line", { x1: "14", y1: "11", x2: "14", y2: "17" })] }) })] })] }) }, id))) }), isCreatingThread && (_jsx("form", { className: "flex gap-2", onSubmit: handleCreateThread, children: _jsx("input", { ref: newThreadInputRef, value: newThreadName, onChange: (e) => setNewThreadName(e.target.value), onBlur: () => {
                                if (!newThreadName.trim()) {
                                    cancelThreadCreation();
                                }
                            }, onKeyDown: handleThreadInputKeyDown, placeholder: "Name your thread", className: "flex-1 rounded-lg border border-border/60 px-3 py-2 text-sm font-inherit bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent/60 transition-all" }) }))] }), _jsx("main", { className: "flex-1 overflow-hidden bg-transparent", children: _jsxs("div", { className: "mx-auto flex h-full max-w-4xl flex-col gap-5 min-w-0 px-4 md:px-6 lg:px-8 py-6", children: [_jsxs("header", { className: "flex flex-col md:flex-row md:items-center justify-between gap-4", children: [_jsxs("div", { className: "min-w-0", children: [_jsx("p", { className: "m-0 text-[11px] text-muted-foreground/70 tracking-wider uppercase font-medium", children: "Thread" }), _jsx("h1", { className: "mt-0.5 mb-0 text-2xl font-semibold text-foreground truncate tracking-tight", children: threadId })] }), _jsxs("div", { className: "flex items-center gap-2.5 text-sm", children: [_jsx("button", { type: "button", onClick: () => setConfigOpen(true), className: "rounded-lg border border-border/60 px-4 py-2 text-[13px] font-medium text-foreground hover:bg-muted/40 hover:border-accent/50 transition-all", children: "Settings" }), _jsx(ThemeToggle, {})] })] }), _jsx("div", { className: "flex flex-wrap items-center gap-2 text-xs text-muted-foreground", children: panelistSummaries.map((summary) => (_jsxs("span", { className: "inline-flex items-center gap-1.5 rounded-lg border border-border/40 bg-card/50 px-3 py-1.5", children: [_jsx("span", { className: "font-semibold text-foreground text-[12px]", children: summary.name }), _jsxs("span", { className: "text-muted-foreground text-[11px]", children: ["\u00B7 ", summary.provider, summary.model ? ` · ${summary.model}` : ""] })] }, summary.id))) }), _jsxs("section", { className: "flex flex-1 min-h-0 flex-col rounded-2xl bg-card/50 border border-border/60 shadow-sm relative backdrop-blur-sm overflow-hidden", children: [_jsxs("div", { className: "flex-1 min-h-0 overflow-y-auto flex flex-col gap-10 px-4 sm:px-8 lg:px-10 py-10 pb-8 scroll-smooth", ref: messageListRef, children: [messages.length === 0 && (_jsx("div", { className: "flex-1 flex items-center justify-center", children: _jsx("p", { className: "text-muted-foreground/60 text-center text-sm", children: "Start a conversation by asking a question below." }) })), messages.map((entry, index) => (_jsx(MessageBubble, { entry: entry, onToggle: () => toggleEntry(index), isLatest: index === messages.length - 1, messageRef: index === messages.length - 1 ? latestMessageRef : undefined, loadingStatus: loadingStatus }, entry.id)))] }), _jsx("div", { className: "absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-background via-background/80 to-transparent pointer-events-none" }), _jsx(AnimatePresence, { children: showScrollToBottom && (_jsxs(motion.button, { type: "button", className: "absolute right-6 bottom-[210px] md:bottom-[220px] rounded-full bg-foreground/90 text-background pl-4 pr-5 py-2.5 shadow-lg text-[13px] font-medium hover:bg-foreground transition-all backdrop-blur-sm flex items-center gap-2 z-10", onClick: handleScrollToBottom, initial: { opacity: 0, y: 10, scale: 0.9 }, animate: { opacity: 1, y: 0, scale: 1 }, exit: { opacity: 0, y: 10, scale: 0.9 }, transition: { duration: 0.2 }, children: [_jsx("svg", { viewBox: "0 0 24 24", className: "w-4 h-4", fill: "currentColor", children: _jsx("path", { d: "M12 16l-6-6h12z" }) }), "Jump to latest"] })) }), _jsx("div", { className: "px-4 sm:px-8 lg:px-10 pt-8 pb-5 relative z-10", children: _jsx(ChatComposer, { loading: loading, error: error, onSend: handleSend, onClearError: () => setError(null), onError: (message) => setError(message) }) })] })] }) }), _jsx(PanelConfigurator, { open: configOpen, onClose: () => setConfigOpen(false), panelists: panelists, onPanelistChange: handlePanelistChange, onAddPanelist: handleAddPanelist, onRemovePanelist: handleRemovePanelist, providerKeys: providerKeys, onProviderKeyChange: handleProviderKeyChange, providerModels: providerModels, modelStatus: modelStatus, onFetchModels: handleFetchProviderModels, maxPanelists: MAX_PANELISTS })] }));
}
function ChatComposer({ loading, error, onSend, onClearError, onError }) {
    const [question, setQuestion] = useState("");
    const [attachments, setAttachments] = useState([]);
    const fileInputRef = useRef(null);
    const textareaRef = useRef(null);
    const hasContent = Boolean(question.trim()) || attachments.length > 0;
    const canSubmit = hasContent && !loading;
    async function handleSubmit(event) {
        event.preventDefault();
        if (!canSubmit)
            return;
        // Clear immediately for better UX
        const currentQuestion = question;
        const currentAttachments = [...attachments];
        setQuestion("");
        setAttachments([]);
        // Refocus textarea
        textareaRef.current?.focus();
        try {
            await onSend({ question: currentQuestion, attachments: currentAttachments });
        }
        catch {
            // On error, restore the content
            setQuestion(currentQuestion);
            setAttachments(currentAttachments);
        }
    }
    function handleFilesSelected(files) {
        if (!files)
            return;
        const toRead = Array.from(files).slice(0, 4);
        Promise.all(toRead.map((file) => new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(String(reader.result));
            reader.onerror = reject;
            reader.readAsDataURL(file);
        })))
            .then((data) => {
            setAttachments((prev) => [...prev, ...data]);
            if (error)
                onClearError();
        })
            .catch(() => onError("Failed to load image"));
    }
    function removeAttachment(index) {
        setAttachments((prev) => prev.filter((_, i) => i !== index));
    }
    return (_jsx("form", { className: "min-w-0", onSubmit: handleSubmit, children: _jsxs("div", { className: "flex flex-col gap-3 min-w-0", children: [_jsxs("div", { className: "relative rounded-2xl border border-border/50 bg-background/95 backdrop-blur-sm max-w-full shadow-sm", children: [_jsx("textarea", { ref: textareaRef, value: question, onChange: (event) => {
                                setQuestion(event.target.value);
                                if (error)
                                    onClearError();
                            }, placeholder: "Send a message...", rows: 3, className: "w-full border-none rounded-2xl p-4 md:p-5 pr-4 md:pr-5 pb-[72px] md:pb-20 text-sm md:text-[15px] font-inherit resize-vertical min-h-[140px] md:min-h-[150px] bg-transparent text-foreground placeholder:text-muted-foreground/50 focus:outline-none leading-relaxed" }), _jsx("div", { className: "absolute left-0 right-0 bottom-0 pt-3 px-4 md:px-5 pb-3.5 md:pb-4 bg-gradient-to-t from-background/95 via-background/80 to-transparent border-t border-border/20 rounded-b-2xl", children: _jsxs("div", { className: "flex items-center gap-2 md:gap-2.5", children: [_jsxs("button", { type: "button", className: "inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-border/50 bg-background/90 text-foreground text-xs font-medium cursor-pointer hover:bg-muted/60 hover:border-border transition-all shadow-sm", onClick: () => fileInputRef.current?.click(), children: [_jsx("svg", { viewBox: "0 0 24 24", "aria-hidden": "true", className: "w-3.5 h-3.5", children: _jsx("path", { fill: "currentColor", d: "M16.5 6.5v9.25a4.25 4.25 0 0 1-8.5 0V5a2.75 2.75 0 0 1 5.5 0v9a1.25 1.25 0 0 1-2.5 0V6.5h-1.5V14a2.75 2.75 0 1 0 5.5 0V5a4.25 4.25 0 0 0-8.5 0v10.75a5.75 5.75 0 1 0 11.5 0V6.5z" }) }), _jsx("span", { className: "hidden sm:inline", children: "Attach" })] }), _jsx("input", { ref: fileInputRef, type: "file", accept: "image/*", multiple: true, hidden: true, onChange: (event) => {
                                            handleFilesSelected(event.target.files);
                                            event.target.value = "";
                                        } }), _jsx(motion.button, { type: "submit", className: "ml-auto w-10 h-10 md:w-11 md:h-11 rounded-xl inline-flex items-center justify-center bg-accent text-accent-foreground border-none cursor-pointer hover:opacity-90 transition-all shadow-sm disabled:opacity-40 disabled:cursor-not-allowed", disabled: !canSubmit, "aria-label": "Send message", whileHover: { scale: canSubmit ? 1.05 : 1 }, whileTap: { scale: canSubmit ? 0.95 : 1 }, animate: {
                                            opacity: hasContent ? 1 : 0.3,
                                            scale: hasContent ? 1 : 0.9
                                        }, transition: { duration: 0.2 }, children: loading ? (_jsxs("svg", { className: "w-5 h-5 animate-spin", viewBox: "0 0 24 24", fill: "none", children: [_jsx("circle", { className: "opacity-25", cx: "12", cy: "12", r: "10", stroke: "currentColor", strokeWidth: "3" }), _jsx("path", { className: "opacity-75", fill: "currentColor", d: "M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" })] })) : (_jsx("svg", { viewBox: "0 0 24 24", "aria-hidden": "true", className: "w-5 h-5", children: _jsx("path", { fill: "currentColor", d: "M2.01 21 23 12 2.01 3 2 10l15 2-15 2z" }) })) })] }) })] }), _jsx(AnimatePresence, { children: attachments.length > 0 && (_jsx(motion.div, { className: "flex flex-wrap gap-2.5", initial: { opacity: 0, height: 0 }, animate: { opacity: 1, height: "auto" }, exit: { opacity: 0, height: 0 }, children: attachments.map((src, index) => (_jsxs(motion.div, { className: "relative w-20 h-20 rounded-xl overflow-hidden border-2 border-border/40 shadow-sm group", initial: { opacity: 0, scale: 0.8 }, animate: { opacity: 1, scale: 1 }, exit: { opacity: 0, scale: 0.8 }, transition: { duration: 0.2, delay: index * 0.03 }, children: [_jsx("img", { src: src, alt: `preview-${index + 1}`, className: "w-full h-full object-cover" }), _jsx("button", { type: "button", onClick: () => {
                                        removeAttachment(index);
                                        if (error)
                                            onClearError();
                                    }, className: "absolute top-1 right-1 border-none rounded-full w-6 h-6 text-xs bg-foreground/90 text-background cursor-pointer hover:bg-foreground transition-all opacity-0 group-hover:opacity-100 flex items-center justify-center font-semibold shadow-sm", children: "\u00D7" })] }, index))) })) }), _jsx(AnimatePresence, { children: error && (_jsx(motion.p, { className: "text-destructive text-[13px] m-0 px-1", initial: { opacity: 0, y: -5 }, animate: { opacity: 1, y: 0 }, exit: { opacity: 0, y: -5 }, children: error })) })] }) }));
}
