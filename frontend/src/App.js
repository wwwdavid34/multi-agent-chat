import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { askPanel } from "./api";
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
const MessageBubble = memo(function MessageBubble({ entry, onToggle }) {
    return (_jsxs(motion.article, { className: "flex flex-col gap-4 min-w-0", initial: { opacity: 0, y: 20 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.3 }, children: [_jsxs("div", { className: "flex flex-col items-end self-end text-right gap-1 w-full max-w-[90%] sm:max-w-[70%]", children: [_jsx("span", { className: "text-xs uppercase tracking-widest text-slate-500", children: "You" }), _jsxs(motion.div, { className: "w-full bg-gradient-to-r from-sky-500 to-blue-600 text-white rounded-3xl rounded-br-md p-4 sm:p-5 shadow-lg break-words", whileHover: { scale: 1.01 }, transition: { type: "spring", stiffness: 300 }, children: [_jsx(Markdown, { content: entry.question }), entry.attachments.length > 0 && (_jsx("div", { className: "mt-3 flex flex-wrap gap-2", children: entry.attachments.map((src, index) => (_jsx("img", { src: src, alt: `attachment-${index + 1}`, className: "w-16 h-16 object-cover rounded-xl border border-white/60 shadow-sm" }, index))) }))] })] }), _jsxs("div", { className: "flex flex-col items-start self-start text-left gap-2 w-full max-w-[90%] sm:max-w-[70%]", children: [_jsx("span", { className: "text-xs uppercase tracking-widest text-slate-500 dark:text-slate-400", children: "LLM panel" }), _jsxs(motion.div, { className: "w-full bg-white dark:bg-slate-800 border border-slate-200/80 dark:border-slate-700 rounded-3xl rounded-bl-md shadow-lg p-4 sm:p-5 break-words", whileHover: { scale: 1.01 }, transition: { type: "spring", stiffness: 280 }, children: [_jsx(Markdown, { content: entry.summary }), _jsxs(motion.button, { type: "button", className: "mt-3 inline-flex items-center gap-1 text-sm font-semibold bg-transparent text-blue-600 dark:text-blue-400 border-none p-0 cursor-pointer hover:opacity-80 transition-opacity", onClick: onToggle, whileHover: { scale: 1.02 }, whileTap: { scale: 0.98 }, children: [entry.expanded ? "Hide panel responses" : "Show panel responses", _jsx("svg", { viewBox: "0 0 24 24", "aria-hidden": "true", className: `w-4 h-4 transition-transform ${entry.expanded ? "rotate-180" : ""}`, children: _jsx("path", { fill: "currentColor", d: "M7 10l5 5 5-5z" }) })] }), entry.expanded && (_jsx(motion.div, { className: "mt-4 border-t border-slate-200 dark:border-slate-700 pt-4 grid gap-3", initial: { opacity: 0, height: 0 }, animate: { opacity: 1, height: "auto" }, exit: { opacity: 0, height: 0 }, transition: { duration: 0.3 }, children: Object.entries(entry.panel_responses).map(([name, text]) => (_jsxs("article", { className: "border border-slate-200/70 dark:border-slate-700 rounded-2xl p-3.5 sm:p-4 bg-slate-50 dark:bg-slate-900/70 shadow-sm", children: [_jsx("h4", { className: "m-0 mb-2 text-slate-900 dark:text-slate-100 text-base", children: name }), _jsx(Markdown, { content: text })] }, name))) }))] })] })] }));
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
    const [error, setError] = useState(null);
    const [showScrollToBottom, setShowScrollToBottom] = useState(false);
    const newThreadInputRef = useRef(null);
    const messageListRef = useRef(null);
    const messages = conversations[threadId] ?? [];
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
        try {
            const sanitizedQuestion = question.trim() || "See attached images.";
            const result = await askPanel({
                thread_id: threadId.trim(),
                question: sanitizedQuestion,
                attachments,
                panelists: preparedPanelists,
                provider_keys: sanitizedProviderKeys,
            });
            const newEntry = {
                id: `${threadId}-${Date.now()}`,
                question: sanitizedQuestion,
                attachments,
                summary: result.summary,
                panel_responses: result.panel_responses,
                expanded: false,
            };
            setConversations((prev) => ({
                ...prev,
                [threadId]: [...(prev[threadId] ?? []), newEntry],
            }));
        }
        catch (err) {
            setError(err instanceof Error ? err.message : "Something went wrong");
            throw err;
        }
        finally {
            setLoading(false);
        }
    }, [loading, preparedPanelists, sanitizedProviderKeys, threadId]);
    const handleScrollToBottom = useCallback(() => {
        const el = messageListRef.current;
        if (!el)
            return;
        el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
        setShowScrollToBottom(false);
    }, []);
    useEffect(() => {
        function handleScroll() {
            const el = messageListRef.current;
            if (!el)
                return;
            const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
            setShowScrollToBottom(distanceFromBottom > 180);
        }
        handleScroll();
        const el = messageListRef.current;
        if (!el)
            return;
        el.addEventListener("scroll", handleScroll);
        return () => el.removeEventListener("scroll", handleScroll);
    }, []);
    useEffect(() => {
        const el = messageListRef.current;
        if (!el)
            return;
        const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
        if (distanceFromBottom <= 200) {
            el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
            setShowScrollToBottom(false);
        }
    }, [messages.length]);
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
    return (_jsxs("div", { className: "flex h-screen w-full overflow-hidden bg-gradient-to-br from-slate-100 via-white to-slate-100 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950", children: [_jsxs("aside", { className: "hidden lg:flex w-72 flex-shrink-0 bg-white/90 dark:bg-slate-950/85 px-6 py-8 shadow-xl dark:shadow-slate-950 flex-col gap-6 overflow-y-auto border-r border-slate-200/70 dark:border-slate-800/70", children: [_jsxs("div", { className: "flex items-center justify-between gap-3", children: [_jsx("h2", { className: "text-xl font-semibold m-0 text-slate-900 dark:text-slate-100", children: "Threads" }), _jsx("button", { type: "button", className: "w-9 h-9 rounded-full border border-slate-200/80 dark:border-slate-700/80 bg-slate-50/80 dark:bg-slate-900/70 text-slate-900 dark:text-slate-100 text-xl font-semibold leading-none flex items-center justify-center cursor-pointer hover:border-blue-500 hover:text-blue-500 transition-colors", onClick: () => {
                                    setIsCreatingThread(true);
                                    setNewThreadName("");
                                }, "aria-label": "Create new thread", children: "+" })] }), _jsx("ul", { className: "list-none p-0 m-0 flex flex-col gap-3 overflow-y-auto flex-1", children: threads.map((id) => (_jsx("li", { children: _jsxs("div", { className: `flex items-center gap-1.5 rounded-2xl p-2 transition-colors ${threadId === id ? "bg-sky-100/70 dark:bg-sky-950/40" : "bg-transparent"}`, children: [_jsx("button", { type: "button", className: `flex-1 flex items-center justify-between px-4 py-3 rounded-xl border text-sm ${threadId === id
                                            ? "border-blue-600/70 dark:border-blue-500/60 bg-white dark:bg-slate-900 text-blue-700 dark:text-blue-300 font-semibold"
                                            : "border-slate-200/80 dark:border-slate-700/80 bg-slate-50/80 dark:bg-slate-900/70 font-semibold text-slate-900 dark:text-slate-100"} cursor-pointer transition-all hover:border-blue-500 dark:hover:border-blue-500/70 shadow-sm`, onClick: () => handleThreadSelect(id), children: _jsx("span", { children: id }) }), _jsxs("div", { className: "flex gap-1", children: [_jsx("button", { type: "button", onClick: () => handleRenameThread(id), "aria-label": "Rename thread", className: "border-none bg-transparent cursor-pointer text-sm hover:opacity-70 transition-opacity p-1.5 rounded-full", children: "\u270F\uFE0F" }), _jsx("button", { type: "button", onClick: () => handleDeleteThread(id), "aria-label": "Delete thread", className: "border-none bg-transparent cursor-pointer text-sm hover:opacity-70 transition-opacity p-1.5 rounded-full", children: "\uD83D\uDDD1\uFE0F" })] })] }) }, id))) }), isCreatingThread && (_jsx("form", { className: "flex gap-2", onSubmit: handleCreateThread, children: _jsx("input", { ref: newThreadInputRef, value: newThreadName, onChange: (e) => setNewThreadName(e.target.value), onBlur: () => {
                                if (!newThreadName.trim()) {
                                    cancelThreadCreation();
                                }
                            }, onKeyDown: handleThreadInputKeyDown, placeholder: "Name your thread", className: "flex-1 rounded-xl border border-slate-300/80 dark:border-slate-700/80 px-3.5 py-2.5 font-inherit bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-600/70 dark:focus:ring-blue-500/70 shadow-sm" }) }))] }), _jsx("main", { className: "flex-1 overflow-hidden bg-transparent", children: _jsxs("div", { className: "mx-auto flex h-full max-w-5xl flex-col gap-4 min-w-0 px-4 md:px-8 lg:px-10 py-6", children: [_jsxs("header", { className: "flex flex-col md:flex-row md:items-center justify-between gap-3", children: [_jsxs("div", { className: "min-w-0", children: [_jsx("p", { className: "m-0 uppercase text-xs text-slate-500 dark:text-slate-400 tracking-widest", children: "Thread" }), _jsx("h1", { className: "mt-1 mb-0 text-2xl font-semibold text-slate-900 dark:text-slate-100 truncate", children: threadId })] }), _jsxs("div", { className: "flex items-center gap-3 text-sm text-slate-600 dark:text-slate-400", children: [_jsx("button", { type: "button", onClick: () => setConfigOpen(true), className: "rounded-full border border-slate-300 dark:border-slate-700 px-4 py-2 font-semibold text-slate-700 dark:text-slate-200 hover:border-blue-500", children: "Panel settings" }), _jsx(ThemeToggle, {})] })] }), _jsx("div", { className: "flex flex-wrap items-center gap-2 text-xs text-slate-600 dark:text-slate-400", children: panelistSummaries.map((summary) => (_jsxs("span", { className: "inline-flex items-center gap-1 rounded-full border border-slate-200 dark:border-slate-700 bg-white/70 dark:bg-slate-900/60 px-3 py-1", children: [_jsx("span", { className: "font-semibold text-slate-900 dark:text-slate-100", children: summary.name }), _jsxs("span", { children: ["\u00B7 ", summary.provider, summary.model ? ` · ${summary.model}` : ""] })] }, summary.id))) }), _jsxs("section", { className: "flex flex-1 min-h-0 flex-col rounded-[28px] bg-white/80 dark:bg-slate-950/40 border border-white/40 dark:border-slate-800/60 shadow-[0_20px_80px_-32px_rgba(15,23,42,0.6)] backdrop-blur relative", children: [_jsxs("div", { className: "flex-1 min-h-0 overflow-y-auto flex flex-col gap-6 px-3 sm:px-8 lg:px-12 py-8", ref: messageListRef, children: [messages.length === 0 && _jsx("p", { className: "text-slate-500 dark:text-slate-400 text-center", children: "Ask a question to start the discussion." }), messages.map((entry, index) => (_jsx(MessageBubble, { entry: entry, onToggle: () => toggleEntry(index) }, entry.id)))] }), showScrollToBottom && (_jsx(motion.button, { type: "button", className: "absolute right-6 bottom-36 md:bottom-40 rounded-full bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 px-4 py-2 shadow-lg text-sm font-semibold", onClick: handleScrollToBottom, initial: { opacity: 0, y: 20 }, animate: { opacity: 1, y: 0 }, exit: { opacity: 0, y: 20 }, children: "Go to latest" })), _jsx("div", { className: "border-t border-slate-200/60 dark:border-slate-800/70 bg-gradient-to-t from-slate-50/80 via-white/60 to-transparent dark:from-slate-900/70 dark:via-slate-950/50 px-3 sm:px-8 lg:px-12 py-6", children: _jsx(ChatComposer, { loading: loading, error: error, onSend: handleSend, onClearError: () => setError(null), onError: (message) => setError(message) }) })] })] }) }), _jsx(PanelConfigurator, { open: configOpen, onClose: () => setConfigOpen(false), panelists: panelists, onPanelistChange: handlePanelistChange, onAddPanelist: handleAddPanelist, onRemovePanelist: handleRemovePanelist, providerKeys: providerKeys, onProviderKeyChange: handleProviderKeyChange, providerModels: providerModels, modelStatus: modelStatus, onFetchModels: handleFetchProviderModels, maxPanelists: MAX_PANELISTS })] }));
}
function ChatComposer({ loading, error, onSend, onClearError, onError }) {
    const [question, setQuestion] = useState("");
    const [attachments, setAttachments] = useState([]);
    const fileInputRef = useRef(null);
    const hasContent = Boolean(question.trim()) || attachments.length > 0;
    const canSubmit = hasContent && !loading;
    async function handleSubmit(event) {
        event.preventDefault();
        if (!canSubmit)
            return;
        try {
            await onSend({ question, attachments });
            setQuestion("");
            setAttachments([]);
        }
        catch {
            // Parent handles error state
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
    return (_jsx("form", { className: "min-w-0", onSubmit: handleSubmit, children: _jsxs("div", { className: "flex flex-col gap-4 min-w-0", children: [_jsxs("div", { className: "relative rounded-2xl border border-slate-300/45 dark:border-slate-700/45 bg-white/95 dark:bg-slate-900/90 shadow-xl max-w-full", children: [_jsx("textarea", { value: question, onChange: (event) => {
                                setQuestion(event.target.value);
                                if (error)
                                    onClearError();
                            }, placeholder: "Send a message...", rows: 3, className: "w-full border-none rounded-2xl p-4 md:p-5 pr-16 md:pr-20 pb-14 md:pb-16 text-sm md:text-base font-inherit resize-vertical min-h-[120px] md:min-h-[140px] bg-transparent text-slate-900 dark:text-slate-100 focus:outline-none" }), _jsxs("div", { className: "absolute left-4 md:left-5 right-4 md:right-5 bottom-3 md:bottom-4 flex items-center gap-2 md:gap-3", children: [_jsxs("button", { type: "button", className: "inline-flex items-center gap-1 md:gap-1.5 px-2.5 md:px-3.5 py-1.5 md:py-2 rounded-full border border-slate-200 dark:border-slate-700 bg-slate-100/80 dark:bg-slate-800/60 text-slate-900 dark:text-slate-100 text-xs md:text-sm font-semibold cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors", onClick: () => fileInputRef.current?.click(), children: [_jsx("svg", { viewBox: "0 0 24 24", "aria-hidden": "true", className: "w-3 h-3 md:w-4 md:h-4", children: _jsx("path", { fill: "currentColor", d: "M16.5 6.5v9.25a4.25 4.25 0 0 1-8.5 0V5a2.75 2.75 0 0 1 5.5 0v9a1.25 1.25 0 0 1-2.5 0V6.5h-1.5V14a2.75 2.75 0 1 0 5.5 0V5a4.25 4.25 0 0 0-8.5 0v10.75a5.75 5.75 0 1 0 11.5 0V6.5z" }) }), _jsx("span", { className: "hidden sm:inline", children: "Add image" }), _jsx("span", { className: "sm:hidden", children: "Image" })] }), _jsx("input", { ref: fileInputRef, type: "file", accept: "image/*", multiple: true, hidden: true, onChange: (event) => {
                                        handleFilesSelected(event.target.files);
                                        event.target.value = "";
                                    } }), _jsx("button", { type: "submit", className: `ml-auto w-9 h-9 md:w-11 md:h-11 rounded-full inline-flex items-center justify-center bg-gradient-to-r from-blue-600 to-purple-600 dark:from-blue-600 dark:to-purple-600 text-white border-none cursor-pointer transition-all ${hasContent ? "opacity-100 scale-100" : "opacity-0 scale-80 translate-y-2"}`, disabled: !canSubmit, "aria-label": "Send message", children: loading ? "..." : (_jsx("svg", { viewBox: "0 0 24 24", "aria-hidden": "true", className: "w-4 h-4 md:w-5 md:h-5", children: _jsx("path", { fill: "currentColor", d: "M2.01 21 23 12 2.01 3 2 10l15 2-15 2z" }) })) })] })] }), attachments.length > 0 && (_jsx("div", { className: "flex flex-wrap gap-3", children: attachments.map((src, index) => (_jsxs("div", { className: "relative w-20 h-20 rounded-xl overflow-hidden border border-sky-200 dark:border-sky-900", children: [_jsx("img", { src: src, alt: `preview-${index + 1}`, className: "w-full h-full object-cover" }), _jsx("button", { type: "button", onClick: () => {
                                    removeAttachment(index);
                                    if (error)
                                        onClearError();
                                }, className: "absolute top-1 right-1 border-none rounded-full w-5 h-5 text-xs bg-slate-900/75 text-white cursor-pointer hover:bg-slate-900 transition-colors", children: "\u00D7" })] }, index))) })), error && _jsx("p", { className: "text-red-700 dark:text-red-400", children: error })] }) }));
}
