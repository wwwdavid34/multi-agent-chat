import { FormEvent, KeyboardEvent, memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";

import { askPanel } from "./api";
import { Markdown } from "./components/Markdown";
import { PanelConfigurator } from "./components/PanelConfigurator";
import { ThemeToggle } from "./components/theme-toggle";
import { fetchModelsForProvider, PROVIDER_LABELS } from "./lib/modelProviders";
import type {
  AskResponse,
  LLMProvider,
  PanelistConfigPayload,
  ProviderKeyMap,
  ProviderModelsMap,
  ProviderModelStatusMap,
} from "./types";

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

const MAX_PANELISTS = 6;
const DEFAULT_PANELISTS: PanelistConfigPayload[] = [
  { id: "panelist-1", name: "Panelist 1", provider: "openai", model: "" },
  { id: "panelist-2", name: "Panelist 2", provider: "openai", model: "" },
];

const createPanelist = (index: number): PanelistConfigPayload => ({
  id: `panelist-${Date.now()}-${Math.random().toString(16).slice(2, 7)}`,
  name: `Panelist ${index}`,
  provider: "openai",
  model: "",
});

const MessageBubble = memo(function MessageBubble({ entry, onToggle }: { entry: MessageEntry; onToggle: () => void }) {
  return (
    <motion.article
      className="flex flex-col gap-6 min-w-0"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="flex flex-col items-end self-end text-right gap-2 w-full max-w-[85%] sm:max-w-[65%]">
        <span className="text-xs font-medium tracking-wide text-muted-foreground px-1">You</span>
        <div className="w-full bg-foreground text-background rounded-2xl rounded-br p-5 shadow-sm break-words">
          <Markdown content={entry.question} />
          {entry.attachments.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {entry.attachments.map((src, index) => (
                <img
                  src={src}
                  alt={`attachment-${index + 1}`}
                  key={index}
                  className="w-16 h-16 object-cover rounded-lg border border-background/20 shadow-sm"
                />
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-col items-start self-start text-left gap-2 w-full max-w-[85%] sm:max-w-[75%]">
        <span className="text-xs font-medium tracking-wide text-muted-foreground px-1">Assistant</span>
        <div className="w-full bg-card border border-border rounded-2xl rounded-bl shadow-sm p-5 break-words">
          <Markdown content={entry.summary} />
          <button
            type="button"
            className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium bg-transparent text-accent border-none p-0 cursor-pointer hover:opacity-70 transition-opacity"
            onClick={onToggle}
          >
            {entry.expanded ? "Hide individual responses" : "Show individual responses"}
            <svg viewBox="0 0 24 24" aria-hidden="true" className={`w-4 h-4 transition-transform duration-200 ${entry.expanded ? "rotate-180" : ""}`}>
              <path fill="currentColor" d="M7 10l5 5 5-5z" />
            </svg>
          </button>
          {entry.expanded && (
            <motion.div
              className="mt-5 border-t border-border pt-5 grid gap-4"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            >
              {Object.entries(entry.panel_responses).map(([name, text]) => (
                <article key={name} className="border border-border rounded-xl p-4 bg-muted/30">
                  <h4 className="m-0 mb-2.5 text-card-foreground text-sm font-semibold tracking-wide">{name}</h4>
                  <div className="text-sm leading-relaxed">
                    <Markdown content={text} />
                  </div>
                </article>
              ))}
            </motion.div>
          )}
        </div>
      </div>
    </motion.article>
  );
});
MessageBubble.displayName = "MessageBubble";

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
  const [newThreadName, setNewThreadName] = useState("");
  const [isCreatingThread, setIsCreatingThread] = useState(false);
  const [panelists, setPanelists] = useState<PanelistConfigPayload[]>(() => {
    const stored = parseJSON<PanelistConfigPayload[]>(localStorage.getItem("panelists"), DEFAULT_PANELISTS);
    return stored.length > 0 ? stored : DEFAULT_PANELISTS;
  });
  const [providerKeys, setProviderKeys] = useState<ProviderKeyMap>(() =>
    parseJSON<ProviderKeyMap>(localStorage.getItem("providerKeys"), {})
  );
  const [providerModels, setProviderModels] = useState<ProviderModelsMap>(() =>
    parseJSON<ProviderModelsMap>(localStorage.getItem("providerModels"), {})
  );
  const [modelStatus, setModelStatus] = useState<ProviderModelStatusMap>({});
  const [configOpen, setConfigOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showScrollToBottom, setShowScrollToBottom] = useState(false);
  const newThreadInputRef = useRef<HTMLInputElement>(null);
  const messageListRef = useRef<HTMLDivElement>(null);

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

  const preparedPanelists = useMemo(
    () =>
      panelists.map((panelist, index) => ({
        ...panelist,
        name: panelist.name.trim() || `Panelist ${index + 1}`,
      })),
    [panelists]
  );

  const panelistSummaries = useMemo(
    () =>
      preparedPanelists.map((panelist) => ({
        id: panelist.id,
        name: panelist.name,
        provider: PROVIDER_LABELS[panelist.provider],
        model: panelist.model,
      })),
    [preparedPanelists]
  );

  const sanitizedProviderKeys = useMemo(() => {
    const entries = Object.entries(providerKeys).filter(([, value]) => Boolean(value?.trim()));
    return Object.fromEntries(entries.map(([key, value]) => [key, value.trim()])) as ProviderKeyMap;
  }, [providerKeys]);

  const handleSend = useCallback(
    async ({ question, attachments }: { question: string; attachments: string[] }) => {
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
      } catch (err) {
        setError(err instanceof Error ? err.message : "Something went wrong");
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [loading, preparedPanelists, sanitizedProviderKeys, threadId]
  );

  const handleScrollToBottom = useCallback(() => {
    const el = messageListRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    setShowScrollToBottom(false);
  }, []);

  useEffect(() => {
    function handleScroll() {
      const el = messageListRef.current;
      if (!el) return;
      const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
      setShowScrollToBottom(distanceFromBottom > 180);
    }

    handleScroll();
    const el = messageListRef.current;
    if (!el) return;
    el.addEventListener("scroll", handleScroll);
    return () => el.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    const el = messageListRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    if (distanceFromBottom <= 200) {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
      setShowScrollToBottom(false);
    }
  }, [messages.length]);

  function toggleEntry(index: number) {
    setConversations((prev) => ({
      ...prev,
      [threadId]: prev[threadId]?.map((item, i) =>
        i === index ? { ...item, expanded: !item.expanded } : item
      ) ?? [],
    }));
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
    setIsCreatingThread(false);
  }

  function cancelThreadCreation() {
    setIsCreatingThread(false);
    setNewThreadName("");
  }

  function handleThreadInputKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      cancelThreadCreation();
    }
  }

  const handlePanelistChange = useCallback(
    (id: string, updates: Partial<PanelistConfigPayload>) => {
      setPanelists((prev) =>
        prev.map((panelist) => {
          if (panelist.id !== id) return panelist;
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
        })
      );
    },
    [providerModels]
  );

  const handleAddPanelist = useCallback(() => {
    setPanelists((prev) => {
      if (prev.length >= MAX_PANELISTS) return prev;
      const index = prev.length + 1;
      const base = createPanelist(index);
      const defaultModel = providerModels[base.provider]?.[0]?.id ?? "";
      return [...prev, { ...base, model: defaultModel }];
    });
  }, [providerModels]);

  const handleRemovePanelist = useCallback((id: string) => {
    setPanelists((prev) => {
      if (prev.length <= 1) {
        return prev;
      }
      const filtered = prev.filter((panelist) => panelist.id !== id);
      return filtered.length > 0 ? filtered : prev;
    });
  }, []);

  const handleProviderKeyChange = useCallback((provider: LLMProvider, key: string) => {
    setProviderKeys((prev) => ({ ...prev, [provider]: key }));
  }, []);

  const handleFetchProviderModels = useCallback(
    async (provider: LLMProvider) => {
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
        setPanelists((prev) =>
          prev.map((panelist) => {
            if (panelist.provider !== provider) return panelist;
            if (!models.length) {
              return { ...panelist, model: "" };
            }
            const hasModel = models.some((model) => model.id === panelist.model);
            return hasModel ? panelist : { ...panelist, model: models[0].id };
          })
        );
      } catch (err) {
        setModelStatus((prev) => ({
          ...prev,
          [provider]: {
            loading: false,
            error: err instanceof Error ? err.message : "Failed to fetch models",
          },
        }));
      }
    },
    [providerKeys]
  );

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      <aside className="hidden lg:flex w-72 flex-shrink-0 bg-card px-6 py-8 flex-col gap-6 overflow-y-auto border-r border-border">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-xl font-semibold m-0 text-foreground">Conversations</h2>
          <button
            type="button"
            className="w-9 h-9 rounded-lg border border-border bg-muted/40 text-foreground text-xl font-semibold leading-none flex items-center justify-center cursor-pointer hover:bg-muted hover:border-accent/40 transition-all"
            onClick={() => {
              setIsCreatingThread(true);
              setNewThreadName("");
            }}
            aria-label="Create new thread"
          >
            +
          </button>
        </div>
        <ul className="list-none p-0 m-0 flex flex-col gap-2 overflow-y-auto flex-1">
          {threads.map((id) => (
            <li key={id}>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  className={`flex-1 flex items-center justify-between px-4 py-2.5 rounded-lg border text-sm transition-all ${
                    threadId === id
                      ? "border-accent/50 bg-accent/5 text-accent font-medium"
                      : "border-border bg-transparent font-normal text-foreground hover:bg-muted/40 hover:border-muted-foreground/20"
                  }`}
                  onClick={() => handleThreadSelect(id)}
                >
                  <span className="truncate">{id}</span>
                </button>
                <div className="flex gap-0.5">
                  <button type="button" onClick={() => handleRenameThread(id)} aria-label="Rename thread" className="border-none bg-transparent cursor-pointer text-sm hover:opacity-60 transition-opacity p-1.5 rounded">
                    ✏️
                  </button>
                  <button type="button" onClick={() => handleDeleteThread(id)} aria-label="Delete thread" className="border-none bg-transparent cursor-pointer text-sm hover:opacity-60 transition-opacity p-1.5 rounded">
                    🗑️
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
        {isCreatingThread && (
          <form className="flex gap-2" onSubmit={handleCreateThread}>
            <input
              ref={newThreadInputRef}
              value={newThreadName}
              onChange={(e) => setNewThreadName(e.target.value)}
              onBlur={() => {
                if (!newThreadName.trim()) {
                  cancelThreadCreation();
                }
              }}
              onKeyDown={handleThreadInputKeyDown}
              placeholder="Name your thread"
              className="flex-1 rounded-lg border border-border px-3.5 py-2.5 font-inherit bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-accent/50"
            />
          </form>
        )}
      </aside>

      <main className="flex-1 overflow-hidden bg-transparent">
        <div className="mx-auto flex h-full max-w-4xl flex-col gap-5 min-w-0 px-4 md:px-8 lg:px-10 py-6">
          <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="min-w-0">
              <p className="m-0 text-xs text-muted-foreground tracking-wide font-medium">Thread</p>
              <h1 className="mt-0.5 mb-0 text-2xl font-semibold text-foreground truncate">{threadId}</h1>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <button
                type="button"
                onClick={() => setConfigOpen(true)}
                className="rounded-lg border border-border px-4 py-2 font-medium text-foreground hover:bg-muted/50 hover:border-accent/40 transition-all"
              >
                Settings
              </button>
              <ThemeToggle />
            </div>
          </header>

          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            {panelistSummaries.map((summary) => (
              <span
                key={summary.id}
                className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5"
              >
                <span className="font-semibold text-foreground">{summary.name}</span>
                <span className="text-muted-foreground">
                  · {summary.provider}
                  {summary.model ? ` · ${summary.model}` : ""}
                </span>
              </span>
            ))}
          </div>

          <section className="flex flex-1 min-h-0 flex-col rounded-xl bg-card border border-border shadow-sm relative">
            <div
              className="flex-1 min-h-0 overflow-y-auto flex flex-col gap-8 px-3 sm:px-8 lg:px-12 py-8"
              ref={messageListRef}
            >
              {messages.length === 0 && <p className="text-muted-foreground text-center text-sm">Start a conversation by asking a question below.</p>}
              {messages.map((entry, index) => (
                <MessageBubble key={entry.id} entry={entry} onToggle={() => toggleEntry(index)} />
              ))}
            </div>
            {showScrollToBottom && (
              <motion.button
                type="button"
                className="absolute right-6 bottom-36 md:bottom-40 rounded-lg bg-foreground text-background px-4 py-2 shadow-md text-sm font-medium hover:opacity-90 transition-opacity"
                onClick={handleScrollToBottom}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 20 }}
              >
                Jump to latest
              </motion.button>
            )}
            <div className="border-t border-border bg-card/80 backdrop-blur-sm px-3 sm:px-8 lg:px-12 py-6">
              <ChatComposer
                loading={loading}
                error={error}
                onSend={handleSend}
                onClearError={() => setError(null)}
                onError={(message) => setError(message)}
              />
            </div>
          </section>
        </div>
      </main>
      <PanelConfigurator
        open={configOpen}
        onClose={() => setConfigOpen(false)}
        panelists={panelists}
        onPanelistChange={handlePanelistChange}
        onAddPanelist={handleAddPanelist}
        onRemovePanelist={handleRemovePanelist}
        providerKeys={providerKeys}
        onProviderKeyChange={handleProviderKeyChange}
        providerModels={providerModels}
        modelStatus={modelStatus}
        onFetchModels={handleFetchProviderModels}
        maxPanelists={MAX_PANELISTS}
      />
    </div>
  );
}

interface ChatComposerProps {
  loading: boolean;
  error: string | null;
  onSend: (payload: { question: string; attachments: string[] }) => Promise<void>;
  onClearError: () => void;
  onError: (message: string) => void;
}

function ChatComposer({ loading, error, onSend, onClearError, onError }: ChatComposerProps) {
  const [question, setQuestion] = useState("");
  const [attachments, setAttachments] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const hasContent = Boolean(question.trim()) || attachments.length > 0;
  const canSubmit = hasContent && !loading;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;

    try {
      await onSend({ question, attachments });
      setQuestion("");
      setAttachments([]);
    } catch {
      // Parent handles error state
    }
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
        if (error) onClearError();
      })
      .catch(() => onError("Failed to load image"));
  }

  function removeAttachment(index: number) {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
  }

  return (
    <form className="min-w-0" onSubmit={handleSubmit}>
      <div className="flex flex-col gap-4 min-w-0">
        <div className="relative rounded-xl border border-border bg-background max-w-full">
          <textarea
            value={question}
            onChange={(event) => {
              setQuestion(event.target.value);
              if (error) onClearError();
            }}
            placeholder="Send a message..."
            rows={3}
            className="w-full border-none rounded-xl p-4 md:p-5 pr-16 md:pr-20 pb-14 md:pb-16 text-sm md:text-base font-inherit resize-vertical min-h-[120px] md:min-h-[140px] bg-transparent text-foreground placeholder:text-muted-foreground focus:outline-none"
          />
          <div className="absolute left-4 md:left-5 right-4 md:right-5 bottom-3 md:bottom-4 flex items-center gap-2 md:gap-3">
            <button
              type="button"
              className="inline-flex items-center gap-1 md:gap-1.5 px-2.5 md:px-3.5 py-1.5 md:py-2 rounded-lg border border-border bg-muted/40 text-foreground text-xs md:text-sm font-medium cursor-pointer hover:bg-muted transition-colors"
              onClick={() => fileInputRef.current?.click()}
            >
              <svg viewBox="0 0 24 24" aria-hidden="true" className="w-3 h-3 md:w-4 md:h-4">
                <path
                  fill="currentColor"
                  d="M16.5 6.5v9.25a4.25 4.25 0 0 1-8.5 0V5a2.75 2.75 0 0 1 5.5 0v9a1.25 1.25 0 0 1-2.5 0V6.5h-1.5V14a2.75 2.75 0 1 0 5.5 0V5a4.25 4.25 0 0 0-8.5 0v10.75a5.75 5.75 0 1 0 11.5 0V6.5z"
                />
              </svg>
              <span className="hidden sm:inline">Attach image</span>
              <span className="sm:hidden">Image</span>
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              multiple
              hidden
              onChange={(event) => {
                handleFilesSelected(event.target.files);
                event.target.value = "";
              }}
            />
            <button
              type="submit"
              className={`ml-auto w-9 h-9 md:w-11 md:h-11 rounded-lg inline-flex items-center justify-center bg-accent text-accent-foreground border-none cursor-pointer transition-all ${
                hasContent ? "opacity-100 scale-100" : "opacity-0 scale-80 translate-y-2"
              }`}
              disabled={!canSubmit}
              aria-label="Send message"
            >
              {loading ? (
                <svg className="w-4 h-4 md:w-5 md:h-5 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" aria-hidden="true" className="w-4 h-4 md:w-5 md:h-5">
                  <path fill="currentColor" d="M2.01 21 23 12 2.01 3 2 10l15 2-15 2z" />
                </svg>
              )}
            </button>
          </div>
        </div>

        {attachments.length > 0 && (
          <div className="flex flex-wrap gap-3">
            {attachments.map((src, index) => (
              <div className="relative w-20 h-20 rounded-lg overflow-hidden border border-border" key={index}>
                <img src={src} alt={`preview-${index + 1}`} className="w-full h-full object-cover" />
                <button
                  type="button"
                  onClick={() => {
                    removeAttachment(index);
                    if (error) onClearError();
                  }}
                  className="absolute top-1 right-1 border-none rounded-full w-5 h-5 text-xs bg-foreground/80 text-background cursor-pointer hover:bg-foreground transition-colors"
                >
                  &times;
                </button>
              </div>
            ))}
          </div>
        )}

        {error && <p className="text-destructive text-sm">{error}</p>}
      </div>
    </form>
  );
}
