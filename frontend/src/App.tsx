import { FormEvent, useEffect, useRef, useState } from "react";

import { askPanel } from "./api";
import { Markdown } from "./components/Markdown";
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
    <div className="message-group">
      <div className="message user">
        <Markdown content={entry.question} />
        {entry.attachments.length > 0 && (
          <div className="attachment-grid">
            {entry.attachments.map((src, index) => (
              <img src={src} alt={`attachment-${index + 1}`} key={index} />
            ))}
          </div>
        )}
      </div>
      <div className="message bot">
        <Markdown content={entry.summary} />
        <button type="button" className="toggle" onClick={onToggle}>
          {entry.expanded ? "Hide panel responses" : "Show panel responses"}
        </button>
        {entry.expanded && (
          <div className="panel-list">
            {Object.entries(entry.panel_responses).map(([name, text]) => (
              <article key={name}>
                <h4>{name}</h4>
                <Markdown content={text} />
              </article>
            ))}
          </div>
        )}
      </div>
    </div>
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
    <div className="app-shell">
      <aside className="sidebar">
        <h2>Threads</h2>
        <ul className="thread-list">
          {threads.map((id) => (
            <li key={id}>
              <div className={`thread-row ${threadId === id ? "active" : ""}`}>
                <button
                  type="button"
                  className="thread-button"
                  onClick={() => handleThreadSelect(id)}
                >
                  <span>{id}</span>
                </button>
                <div className="thread-actions">
                  <button type="button" onClick={() => handleRenameThread(id)} aria-label="Rename thread">
                    ✏️
                  </button>
                  <button type="button" onClick={() => handleDeleteThread(id)} aria-label="Delete thread">
                    🗑️
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
        <form className="new-thread" onSubmit={handleCreateThread}>
          <input
            value={newThreadName}
            onChange={(e) => setNewThreadName(e.target.value)}
            placeholder="New thread ID"
          />
          <button type="submit">Add</button>
        </form>
      </aside>

      <main className="chat-panel">
        <header>
          <div>
            <p className="thread-label">Current thread</p>
            <h1>{threadId}</h1>
          </div>
          <p>Keep chatting to build on the multi-agent discussion.</p>
        </header>

        <section className="chat-card">
          <div className="messages">
            {messages.length === 0 && <p className="empty">Ask a question to start the discussion.</p>}
            {messages.map((entry, index) => (
              <MessageBubble key={entry.id} entry={entry} onToggle={() => toggleEntry(index)} />
            ))}
          </div>
          <div className="floating-composer">
            <form className="composer" onSubmit={handleSubmit}>
              <div className="inputs">
                <div className="textarea-wrapper">
                  <textarea
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="Type your question..."
                    rows={3}
                  />
                  <div className="composer-actions">
                    <button
                      type="button"
                      className="attach-inline"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path
                          fill="currentColor"
                          d="M16.5 6.5v9.25a4.25 4.25 0 0 1-8.5 0V5a2.75 2.75 0 0 1 5.5 0v9a1.25 1.25 0 0 1-2.5 0V6.5h-1.5V14a2.75 2.75 0 1 0 5.5 0V5a4.25 4.25 0 0 0-8.5 0v10.75a5.75 5.75 0 1 0 11.5 0V6.5z"
                        />
                      </svg>
                      <span>Add image</span>
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
                      className={`send-button ${hasContent ? "visible" : ""}`}
                      disabled={!canSubmit}
                      aria-label="Send message"
                    >
                      {loading ? "Thinking..." : (
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path fill="currentColor" d="M2.01 21 23 12 2.01 3 2 10l15 2-15 2z" />
                        </svg>
                      )}
                    </button>
                  </div>
                </div>

                {attachments.length > 0 && (
                  <div className="attachment-preview">
                    {attachments.map((src, index) => (
                      <div className="attachment-thumb" key={index}>
                        <img src={src} alt={`preview-${index + 1}`} />
                        <button type="button" onClick={() => removeAttachment(index)}>
                          &times;
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </form>
          </div>
          {error && <p className="error">{error}</p>}
        </section>
      </main>
    </div>
  );
}
