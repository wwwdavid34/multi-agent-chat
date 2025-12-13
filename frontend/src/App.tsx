import { FormEvent, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";

import { askPanel } from "./api";
import { Markdown } from "./components/Markdown";
import { ThemeToggle } from "./components/theme-toggle";
import type { AskResponse } from "./types";

const DEFAULT_THREAD_ID = "demo-thread";

type PanelResponses = AskResponse["panel_responses"];
type ConversationMap = Record<string, MessageEntry[]>;
type StoredConversationMap = Record<string, (MessageEntry & { attachments?: string[] })[]>;

interface MessageEntry {
  id: string;
  question: string;
  attachments: string[];
  summary: string;
  panel_responses: PanelResponses;
  expanded: boolean;
}

const parseJSON = <T,>(value: string | null, fallback: T): T => {
  try {
    return value ? (JSON.parse(value) as T) : fallback;
  } catch {
    return fallback;
  }
};

function MessageBubble({ entry, onToggle }: { entry: MessageEntry; onToggle: () => void }) {
  return (
    <motion.div
      className="flex flex-col gap-2 min-w-0"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <motion.div
        className="ml-auto bg-blue-600 dark:bg-blue-700 text-white rounded-2xl rounded-br-sm max-w-[85%] sm:max-w-[75%] md:max-w-[70%] p-3.5 px-4 break-words"
        whileHover={{ scale: 1.01 }}
        transition={{ type: "spring", stiffness: 300 }}
      >
        <Markdown content={entry.question} />
        {entry.attachments.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {entry.attachments.map((src, index) => (
              <img src={src} alt={`attachment-${index + 1}`} key={index} className="w-16 h-16 object-cover rounded-lg border border-slate-200" />
            ))}
          </div>
        )}
      </motion.div>
      <motion.div
        className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl rounded-bl-sm shadow-md max-w-[85%] sm:max-w-[75%] md:max-w-[70%] p-3.5 px-4 break-words"
        whileHover={{ scale: 1.01 }}
        transition={{ type: "spring", stiffness: 300 }}
      >
        <Markdown content={entry.summary} />
        <motion.button
          type="button"
          className="bg-transparent text-blue-600 dark:text-blue-400 border-none p-2 px-0 cursor-pointer font-semibold hover:opacity-70 transition-opacity"
          onClick={onToggle}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          {entry.expanded ? "Hide panel responses" : "Show panel responses"}
        </motion.button>
        {entry.expanded && (
          <motion.div
            className="mt-4 border-t border-slate-200 dark:border-slate-700 pt-4 grid gap-3"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
          >
            {Object.entries(entry.panel_responses).map(([name, text]) => (
              <article key={name} className="border border-slate-200 dark:border-slate-700 rounded-xl p-3 bg-slate-50 dark:bg-slate-900">
                <h4 className="m-0 mb-2 text-slate-900 dark:text-slate-100">{name}</h4>
                <Markdown content={text} />
              </article>
            ))}
          </motion.div>
        )}
      </motion.div>
    </motion.div>
  );
}

export default function App() {
  const [threadId, setThreadId] = useState(() => localStorage.getItem("threadId") ?? DEFAULT_THREAD_ID);
  const [threads, setThreads] = useState<string[]>(() => {
    const stored = parseJSON<string[]>(localStorage.getItem("threads"), []);
    if (!stored.includes(DEFAULT_THREAD_ID)) {
      stored.unshift(DEFAULT_THREAD_ID);
    }
    return Array.from(new Set(stored));
  });
  const [conversations, setConversations] = useState<ConversationMap>(() => {
    const raw = parseJSON<StoredConversationMap>(localStorage.getItem("conversations"), {});
    const normalized: ConversationMap = {};
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
  const [attachments, setAttachments] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!hasContent) return;

    setLoading(true);
    setError(null);

    try {
      const sanitizedQuestion = question.trim() || "See attached images.";
      const result = await askPanel({
        thread_id: threadId.trim(),
        question: sanitizedQuestion,
        attachments,
      });
      const newEntry: MessageEntry = {
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
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  function toggleEntry(index: number) {
    setConversations((prev) => ({
      ...prev,
      [threadId]: prev[threadId]?.map((item, i) =>
        i === index ? { ...item, expanded: !item.expanded } : item
      ) ?? [],
    }));
  }

  function handleFilesSelected(files: FileList | null) {
    if (!files) return;
    const toRead = Array.from(files).slice(0, 4);
    Promise.all(
      toRead.map(
        (file) =>
          new Promise<string>((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(String(reader.result));
            reader.onerror = reject;
            reader.readAsDataURL(file);
          })
      )
    )
      .then((data) => {
        setAttachments((prev) => [...prev, ...data]);
      })
      .catch(() => setError("Failed to load image"));
  }

  function removeAttachment(index: number) {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
  }

  function handleThreadSelect(id: string) {
    setThreadId(id);
  }

  function handleRenameThread(id: string) {
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

  function handleDeleteThread(id: string) {
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

  function handleCreateThread(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = newThreadName.trim();
    if (!trimmed) return;

    setThreads((prev) => (prev.includes(trimmed) ? prev : [...prev, trimmed]));
    setConversations((prev) => (prev[trimmed] ? prev : { ...prev, [trimmed]: [] }));
    setThreadId(trimmed);
    setNewThreadName("");
  }

  return (
    <div className="flex h-screen w-full overflow-hidden">
      <aside className="hidden lg:flex w-64 flex-shrink-0 bg-white dark:bg-slate-950 p-8 px-5 shadow-lg dark:shadow-slate-900 flex-col gap-5 overflow-y-auto border-r border-slate-200 dark:border-slate-800">
        <h2 className="text-xl font-semibold m-0 text-slate-900 dark:text-slate-100">Threads</h2>
        <ul className="list-none p-0 m-0 flex flex-col gap-2 overflow-y-auto flex-1">
          {threads.map((id) => (
            <li key={id}>
              <div className={`flex items-center gap-1.5 rounded-xl p-1 transition-colors ${threadId === id ? "bg-sky-100 dark:bg-sky-950" : ""}`}>
                <button
                  type="button"
                  className={`flex-1 flex items-center justify-between px-3.5 py-2.5 rounded-lg border ${
                    threadId === id
                      ? "border-blue-600 dark:border-blue-500 bg-transparent text-blue-700 dark:text-blue-400 font-semibold"
                      : "border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 font-semibold text-slate-900 dark:text-slate-100"
                  } cursor-pointer transition-all hover:border-blue-500 dark:hover:border-blue-600`}
                  onClick={() => handleThreadSelect(id)}
                >
                  <span>{id}</span>
                </button>
                <div className="flex gap-0.5">
                  <button type="button" onClick={() => handleRenameThread(id)} aria-label="Rename thread" className="border-none bg-transparent cursor-pointer text-sm hover:opacity-70 transition-opacity">
                    ✏️
                  </button>
                  <button type="button" onClick={() => handleDeleteThread(id)} aria-label="Delete thread" className="border-none bg-transparent cursor-pointer text-sm hover:opacity-70 transition-opacity">
                    🗑️
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
        <form className="flex gap-2" onSubmit={handleCreateThread}>
          <input
            value={newThreadName}
            onChange={(e) => setNewThreadName(e.target.value)}
            placeholder="New thread ID"
            className="flex-1 rounded-lg border border-slate-300 dark:border-slate-700 p-2.5 font-inherit bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-600 dark:focus:ring-blue-500"
          />
          <button type="submit" className="rounded-lg border-none bg-sky-500 dark:bg-sky-600 text-white px-4 py-2.5 font-semibold cursor-pointer hover:bg-sky-600 dark:hover:bg-sky-700 transition-colors">Add</button>
        </form>
      </aside>

      <main className="flex-1 flex flex-col p-4 md:p-8 gap-6 min-w-0 overflow-hidden">
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="min-w-0 flex-shrink-0">
            <p className="m-0 uppercase text-xs text-slate-500 dark:text-slate-400 tracking-wider">Current thread</p>
            <h1 className="mt-1 mb-0 text-slate-900 dark:text-slate-100 truncate">{threadId}</h1>
          </div>
          <div className="flex items-center gap-4 flex-shrink-0">
            <p className="hidden md:block text-slate-600 dark:text-slate-400">Keep chatting to build on the multi-agent discussion.</p>
            <ThemeToggle />
          </div>
        </header>

        <section className="bg-white dark:bg-slate-900 rounded-3xl p-4 md:p-6 shadow-2xl dark:shadow-slate-950 flex flex-col flex-1 min-h-0 min-w-0 relative overflow-hidden">
          <div className="flex-1 min-h-0 min-w-0 overflow-y-auto flex flex-col gap-4 pb-36 px-2">
            {messages.length === 0 && <p className="text-slate-500 dark:text-slate-400 text-center">Ask a question to start the discussion.</p>}
            {messages.map((entry, index) => (
              <MessageBubble key={entry.id} entry={entry} onToggle={() => toggleEntry(index)} />
            ))}
          </div>
          <div className="sticky bottom-4 px-1 md:px-2">
            <form className="mt-2 min-w-0" onSubmit={handleSubmit}>
              <div className="flex flex-col gap-3 min-w-0">
                <div className="relative rounded-3xl border border-slate-300/45 dark:border-slate-700/45 bg-white/90 dark:bg-slate-900/90 backdrop-blur shadow-2xl dark:shadow-slate-950 max-w-full">
                  <textarea
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="Type your question..."
                    rows={3}
                    className="w-full border-none rounded-3xl p-4 md:p-5 pr-16 md:pr-20 pb-14 md:pb-16 text-sm md:text-base font-inherit resize-vertical min-h-[120px] md:min-h-[140px] bg-gradient-to-br from-slate-50/95 to-slate-200/85 dark:from-slate-900/95 dark:to-slate-800/85 text-slate-900 dark:text-slate-100 focus:outline-none"
                  />
                  <div className="absolute left-4 md:left-5 right-4 md:right-5 bottom-3 md:bottom-4 flex items-center gap-2 md:gap-3">
                    <button
                      type="button"
                      className="inline-flex items-center gap-1 md:gap-1.5 px-2.5 md:px-3.5 py-1.5 md:py-2 rounded-full border-none bg-slate-200/85 dark:bg-slate-700/85 text-slate-900 dark:text-slate-100 text-xs md:text-sm font-semibold cursor-pointer shadow-inner hover:bg-slate-300 dark:hover:bg-slate-600 transition-colors"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true" className="w-3 h-3 md:w-4 md:h-4">
                        <path
                          fill="currentColor"
                          d="M16.5 6.5v9.25a4.25 4.25 0 0 1-8.5 0V5a2.75 2.75 0 0 1 5.5 0v9a1.25 1.25 0 0 1-2.5 0V6.5h-1.5V14a2.75 2.75 0 1 0 5.5 0V5a4.25 4.25 0 0 0-8.5 0v10.75a5.75 5.75 0 1 0 11.5 0V6.5z"
                        />
                      </svg>
                      <span className="hidden sm:inline">Add image</span>
                      <span className="sm:hidden">Image</span>
                    </button>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="image/*"
                      multiple
                      hidden
                      onChange={(e) => {
                        handleFilesSelected(e.target.files);
                        e.target.value = "";
                      }}
                    />
                    <button
                      type="submit"
                      className={`ml-auto w-9 h-9 md:w-11 md:h-11 rounded-full inline-flex items-center justify-center bg-gradient-to-r from-blue-600 to-purple-600 dark:from-blue-700 dark:to-purple-700 text-white border-none cursor-pointer transition-all ${
                        hasContent ? "opacity-100 scale-100" : "opacity-0 scale-80 translate-y-2"
                      }`}
                      disabled={!canSubmit}
                      aria-label="Send message"
                    >
                      {loading ? "..." : (
                        <svg viewBox="0 0 24 24" aria-hidden="true" className="w-4 h-4 md:w-5 md:h-5">
                          <path fill="currentColor" d="M2.01 21 23 12 2.01 3 2 10l15 2-15 2z" />
                        </svg>
                      )}
                    </button>
                  </div>
                </div>

                {attachments.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {attachments.map((src, index) => (
                      <div className="relative w-20 h-20 rounded-xl overflow-hidden border border-sky-200 dark:border-sky-900" key={index}>
                        <img src={src} alt={`preview-${index + 1}`} className="w-full h-full object-cover" />
                        <button type="button" onClick={() => removeAttachment(index)} className="absolute top-1 right-1 border-none rounded-full w-5 h-5 text-xs bg-slate-900/75 text-white cursor-pointer hover:bg-slate-900 transition-colors">
                          &times;
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </form>
          </div>
          {error && <p className="text-red-700 dark:text-red-400 mt-2">{error}</p>}
        </section>
      </main>
    </div>
  );
}
