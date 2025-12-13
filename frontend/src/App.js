import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { askPanel } from "./api";
import { Markdown } from "./components/Markdown";
import { ThemeToggle } from "./components/theme-toggle";
const DEFAULT_THREAD_ID = "demo-thread";
const parseJSON = (value, fallback) => {
    try {
        return value ? JSON.parse(value) : fallback;
    }
    catch {
        return fallback;
    }
};
function MessageBubble({ entry, onToggle }) {
    return (_jsxs(motion.div, { className: "flex flex-col gap-2", initial: { opacity: 0, y: 20 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.3 }, children: [_jsxs(motion.div, { className: "ml-auto bg-blue-600 dark:bg-blue-700 text-white rounded-2xl rounded-br-sm max-w-[70%] p-3.5 px-4", whileHover: { scale: 1.01 }, transition: { type: "spring", stiffness: 300 }, children: [_jsx(Markdown, { content: entry.question }), entry.attachments.length > 0 && (_jsx("div", { className: "mt-2 flex flex-wrap gap-1.5", children: entry.attachments.map((src, index) => (_jsx("img", { src: src, alt: `attachment-${index + 1}`, className: "w-18 h-18 object-cover rounded-lg border border-slate-200" }, index))) }))] }), _jsxs(motion.div, { className: "bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl rounded-bl-sm shadow-md max-w-[70%] p-3.5 px-4", whileHover: { scale: 1.01 }, transition: { type: "spring", stiffness: 300 }, children: [_jsx(Markdown, { content: entry.summary }), _jsx(motion.button, { type: "button", className: "bg-transparent text-blue-600 dark:text-blue-400 border-none p-2 px-0 cursor-pointer font-semibold hover:opacity-70 transition-opacity", onClick: onToggle, whileHover: { scale: 1.02 }, whileTap: { scale: 0.98 }, children: entry.expanded ? "Hide panel responses" : "Show panel responses" }), entry.expanded && (_jsx(motion.div, { className: "mt-4 border-t border-slate-200 dark:border-slate-700 pt-4 grid gap-3", initial: { opacity: 0, height: 0 }, animate: { opacity: 1, height: "auto" }, exit: { opacity: 0, height: 0 }, transition: { duration: 0.3 }, children: Object.entries(entry.panel_responses).map(([name, text]) => (_jsxs("article", { className: "border border-slate-200 dark:border-slate-700 rounded-xl p-3 bg-slate-50 dark:bg-slate-900", children: [_jsx("h4", { className: "m-0 mb-2 text-slate-900 dark:text-slate-100", children: name }), _jsx(Markdown, { content: text })] }, name))) }))] })] }));
}
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
    const [question, setQuestion] = useState("");
    const [newThreadName, setNewThreadName] = useState("");
    const [attachments, setAttachments] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const fileInputRef = useRef(null);
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
        if (!threads.includes(threadId)) {
            setThreads((prev) => Array.from(new Set([...prev, threadId])));
        }
        if (!conversations[threadId]) {
            setConversations((prev) => ({ ...prev, [threadId]: [] }));
        }
    }, [threadId, threads, conversations]);
    const hasContent = Boolean(question.trim()) || attachments.length > 0;
    const canSubmit = hasContent && !loading;
    async function handleSubmit(event) {
        event.preventDefault();
        if (!hasContent)
            return;
        setLoading(true);
        setError(null);
        try {
            const sanitizedQuestion = question.trim() || "See attached images.";
            const result = await askPanel({
                thread_id: threadId.trim(),
                question: sanitizedQuestion,
                attachments,
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
            setQuestion("");
            setAttachments([]);
        }
        catch (err) {
            setError(err instanceof Error ? err.message : "Something went wrong");
        }
        finally {
            setLoading(false);
        }
    }
    function toggleEntry(index) {
        setConversations((prev) => ({
            ...prev,
            [threadId]: prev[threadId]?.map((item, i) => i === index ? { ...item, expanded: !item.expanded } : item) ?? [],
        }));
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
        })
            .catch(() => setError("Failed to load image"));
    }
    function removeAttachment(index) {
        setAttachments((prev) => prev.filter((_, i) => i !== index));
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
    }
    return (_jsxs("div", { className: "flex h-screen overflow-hidden", children: [_jsxs("aside", { className: "w-64 bg-white dark:bg-slate-950 p-8 px-5 shadow-lg dark:shadow-slate-900 flex flex-col gap-5 overflow-y-auto border-r border-slate-200 dark:border-slate-800", children: [_jsx("h2", { className: "text-xl font-semibold m-0 text-slate-900 dark:text-slate-100", children: "Threads" }), _jsx("ul", { className: "list-none p-0 m-0 flex flex-col gap-2 overflow-y-auto flex-1", children: threads.map((id) => (_jsx("li", { children: _jsxs("div", { className: `flex items-center gap-1.5 rounded-xl p-1 transition-colors ${threadId === id ? "bg-sky-100 dark:bg-sky-950" : ""}`, children: [_jsx("button", { type: "button", className: `flex-1 flex items-center justify-between px-3.5 py-2.5 rounded-lg border ${threadId === id
                                            ? "border-blue-600 dark:border-blue-500 bg-transparent text-blue-700 dark:text-blue-400 font-semibold"
                                            : "border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 font-semibold text-slate-900 dark:text-slate-100"} cursor-pointer transition-all hover:border-blue-500 dark:hover:border-blue-600`, onClick: () => handleThreadSelect(id), children: _jsx("span", { children: id }) }), _jsxs("div", { className: "flex gap-0.5", children: [_jsx("button", { type: "button", onClick: () => handleRenameThread(id), "aria-label": "Rename thread", className: "border-none bg-transparent cursor-pointer text-sm hover:opacity-70 transition-opacity", children: "\u270F\uFE0F" }), _jsx("button", { type: "button", onClick: () => handleDeleteThread(id), "aria-label": "Delete thread", className: "border-none bg-transparent cursor-pointer text-sm hover:opacity-70 transition-opacity", children: "\uD83D\uDDD1\uFE0F" })] })] }) }, id))) }), _jsxs("form", { className: "flex gap-2", onSubmit: handleCreateThread, children: [_jsx("input", { value: newThreadName, onChange: (e) => setNewThreadName(e.target.value), placeholder: "New thread ID", className: "flex-1 rounded-lg border border-slate-300 dark:border-slate-700 p-2.5 font-inherit bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-600 dark:focus:ring-blue-500" }), _jsx("button", { type: "submit", className: "rounded-lg border-none bg-sky-500 dark:bg-sky-600 text-white px-4 py-2.5 font-semibold cursor-pointer hover:bg-sky-600 dark:hover:bg-sky-700 transition-colors", children: "Add" })] })] }), _jsxs("main", { className: "flex-1 flex flex-col p-8 gap-6 h-screen min-h-0 overflow-hidden", children: [_jsxs("header", { className: "flex items-center justify-between gap-4", children: [_jsxs("div", { children: [_jsx("p", { className: "m-0 uppercase text-xs text-slate-500 dark:text-slate-400 tracking-wider", children: "Current thread" }), _jsx("h1", { className: "mt-1 mb-0 text-slate-900 dark:text-slate-100", children: threadId })] }), _jsxs("div", { className: "flex items-center gap-4", children: [_jsx("p", { className: "text-slate-600 dark:text-slate-400", children: "Keep chatting to build on the multi-agent discussion." }), _jsx(ThemeToggle, {})] })] }), _jsxs("section", { className: "bg-white dark:bg-slate-900 rounded-3xl p-6 shadow-2xl dark:shadow-slate-950 flex flex-col flex-1 min-h-0 relative", children: [_jsxs("div", { className: "flex-1 min-h-0 overflow-y-auto flex flex-col gap-4 pb-36", children: [messages.length === 0 && _jsx("p", { className: "text-slate-500 dark:text-slate-400 text-center", children: "Ask a question to start the discussion." }), messages.map((entry, index) => (_jsx(MessageBubble, { entry: entry, onToggle: () => toggleEntry(index) }, entry.id)))] }), _jsx("div", { className: "sticky bottom-4 px-2", children: _jsx("form", { className: "mt-2", onSubmit: handleSubmit, children: _jsxs("div", { className: "flex-1 flex flex-col gap-3", children: [_jsxs("div", { className: "relative rounded-3xl border border-slate-300/45 dark:border-slate-700/45 bg-white/90 dark:bg-slate-900/90 backdrop-blur shadow-2xl dark:shadow-slate-950 w-full", children: [_jsx("textarea", { value: question, onChange: (e) => setQuestion(e.target.value), placeholder: "Type your question...", rows: 3, className: "w-full border-none rounded-3xl p-5 pr-20 pb-16 text-base font-inherit resize-vertical min-h-[140px] bg-gradient-to-br from-slate-50/95 to-slate-200/85 dark:from-slate-900/95 dark:to-slate-800/85 text-slate-900 dark:text-slate-100 focus:outline-none" }), _jsxs("div", { className: "absolute left-5 right-5 bottom-4 flex items-center gap-3", children: [_jsxs("button", { type: "button", className: "inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full border-none bg-slate-200/85 dark:bg-slate-700/85 text-slate-900 dark:text-slate-100 font-semibold cursor-pointer shadow-inner hover:bg-slate-300 dark:hover:bg-slate-600 transition-colors", onClick: () => fileInputRef.current?.click(), children: [_jsx("svg", { viewBox: "0 0 24 24", "aria-hidden": "true", className: "w-4 h-4", children: _jsx("path", { fill: "currentColor", d: "M16.5 6.5v9.25a4.25 4.25 0 0 1-8.5 0V5a2.75 2.75 0 0 1 5.5 0v9a1.25 1.25 0 0 1-2.5 0V6.5h-1.5V14a2.75 2.75 0 1 0 5.5 0V5a4.25 4.25 0 0 0-8.5 0v10.75a5.75 5.75 0 1 0 11.5 0V6.5z" }) }), _jsx("span", { children: "Add image" })] }), _jsx("input", { ref: fileInputRef, type: "file", accept: "image/*", multiple: true, hidden: true, onChange: (e) => {
                                                                    handleFilesSelected(e.target.files);
                                                                    e.target.value = "";
                                                                } }), _jsx("button", { type: "submit", className: `ml-auto w-11 h-11 rounded-full inline-flex items-center justify-center bg-gradient-to-r from-blue-600 to-purple-600 dark:from-blue-700 dark:to-purple-700 text-white border-none cursor-pointer transition-all ${hasContent ? "opacity-100 scale-100" : "opacity-0 scale-80 translate-y-2"}`, disabled: !canSubmit, "aria-label": "Send message", children: loading ? "..." : (_jsx("svg", { viewBox: "0 0 24 24", "aria-hidden": "true", className: "w-5 h-5", children: _jsx("path", { fill: "currentColor", d: "M2.01 21 23 12 2.01 3 2 10l15 2-15 2z" }) })) })] })] }), attachments.length > 0 && (_jsx("div", { className: "flex flex-wrap gap-2", children: attachments.map((src, index) => (_jsxs("div", { className: "relative w-20 h-20 rounded-xl overflow-hidden border border-sky-200 dark:border-sky-900", children: [_jsx("img", { src: src, alt: `preview-${index + 1}`, className: "w-full h-full object-cover" }), _jsx("button", { type: "button", onClick: () => removeAttachment(index), className: "absolute top-1 right-1 border-none rounded-full w-5 h-5 text-xs bg-slate-900/75 text-white cursor-pointer hover:bg-slate-900 transition-colors", children: "\u00D7" })] }, index))) }))] }) }) }), error && _jsx("p", { className: "text-red-700 dark:text-red-400 mt-2", children: error })] })] })] }));
}
