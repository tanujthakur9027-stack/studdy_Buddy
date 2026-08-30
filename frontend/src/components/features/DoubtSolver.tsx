"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageCircle, Send, Bot, User, Lightbulb, ArrowRight,
  Copy, CheckCheck, FileText, Volume2, VolumeX, RotateCcw,
  Bookmark, BookmarkCheck, Mic, MicOff, BookMarked, X,
  Plus, Trash2, History, PencilLine, ChevronLeft,
} from "lucide-react";
import { Spinner } from "@/components/ui";
import { streamPost } from "@/lib/streamApi";
import { useSpeech, useVoiceInput } from "@/hooks/useSpeech";
import { useSavedAnswers } from "@/hooks/useSavedAnswers";
import {
  fetchChatSessions, createChatSession, deleteChatSession,
  fetchChatMessages, appendChatMessage, renameChatSession,
} from "@/lib/api";
import type { SourceChunk } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage, ChatSessionSummary } from "@/types";
import toast from "react-hot-toast";
import { clsx } from "clsx";

interface Props { docId?: string }

const STARTER_QUESTIONS = [
  "What is the central idea of this document?",
  "Explain the main concepts in simple terms",
  "What are the most important formulas?",
  "Compare and contrast the key theories",
  "What should I focus on for exams?",
];

let _msgCounter = 0;
function nextId() { return `msg_${++_msgCounter}_${Date.now()}`; }

// ── Copy button ───────────────────────────────────────────────────────────────
function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Copy failed");
    }
  };
  return (
    <button
      onClick={handleCopy}
      aria-label="Copy answer"
      className="p-1 rounded-lg text-gray-600 hover:text-gray-400 hover:bg-gray-800 transition-colors"
    >
      {copied
        ? <CheckCheck className="h-3.5 w-3.5 text-green-400" />
        : <Copy className="h-3.5 w-3.5" />}
    </button>
  );
}

// ── Source chips ──────────────────────────────────────────────────────────────
function SourceChips({ sources }: { sources: SourceChunk[] }) {
  if (!sources.length) return null;
  const unique = sources.filter(
    (s, i, arr) => arr.findIndex((x) => x.filename === s.filename && x.page === s.page) === i
  );
  return (
    <div className="flex flex-wrap gap-1.5 mt-1">
      {unique.map((src, i) => (
        <span
          key={i}
          title={src.snippet}
          className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-gray-800 border border-gray-700 text-gray-400 cursor-default"
        >
          <FileText className="h-3 w-3 shrink-0 text-brand-400" />
          {src.filename}
          {src.page > 0 && <span className="text-gray-600">· p{src.page}</span>}
        </span>
      ))}
    </div>
  );
}

// ── Session sidebar ───────────────────────────────────────────────────────────
function SessionSidebar({
  sessions,
  activeId,
  onSelect,
  onNew,
  onDelete,
  onRename,
  loading,
}: {
  sessions: ChatSessionSummary[];
  activeId: string | null;
  onSelect: (_id: string) => void;
  onNew: () => void;
  onDelete: (_id: string) => void;
  onRename: (_id: string, _title: string) => void;
  loading: boolean;
}) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue]   = useState("");

  const startEdit = (s: ChatSessionSummary) => {
    setEditingId(s.id);
    setEditValue(s.title);
  };
  const commitEdit = async (id: string) => {
    if (editValue.trim()) onRename(id, editValue.trim());
    setEditingId(null);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold text-gray-400 uppercase tracking-widest flex items-center gap-1.5">
          <History className="h-3.5 w-3.5" /> Chat History
        </span>
        <button
          onClick={onNew}
          disabled={loading}
          title="New chat"
          className="p-1.5 rounded-lg bg-brand-600 hover:bg-brand-700 text-white transition-colors"
        >
          <Plus className="h-3.5 w-3.5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto space-y-1 pr-0.5">
        {sessions.length === 0 && (
          <p className="text-xs text-gray-600 text-center py-6">No chats yet</p>
        )}
        {sessions.map((s) => (
          <div
            key={s.id}
            className={clsx(
              "group flex items-center gap-2 px-3 py-2 rounded-xl cursor-pointer transition-all",
              s.id === activeId
                ? "bg-brand-600/20 border border-brand-500/40 text-white"
                : "hover:bg-gray-800 border border-transparent text-gray-400 hover:text-gray-200",
            )}
            onClick={() => onSelect(s.id)}
          >
            {editingId === s.id ? (
              <input
                autoFocus
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onBlur={() => commitEdit(s.id)}
                onKeyDown={(e) => { if (e.key === "Enter") commitEdit(s.id); if (e.key === "Escape") setEditingId(null); }}
                onClick={(e) => e.stopPropagation()}
                className="flex-1 text-xs bg-gray-900 border border-gray-600 rounded px-1.5 py-0.5 outline-none text-white"
              />
            ) : (
              <span className="flex-1 text-xs truncate">{s.title}</span>
            )}
            <span className="text-[10px] text-gray-600 shrink-0">{s.message_count}</span>
            <button
              onClick={(e) => { e.stopPropagation(); startEdit(s); }}
              className="p-0.5 opacity-0 group-hover:opacity-100 transition-opacity text-gray-500 hover:text-brand-400"
              title="Rename"
            >
              <PencilLine className="h-3 w-3" />
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(s.id); }}
              className="p-0.5 opacity-0 group-hover:opacity-100 transition-opacity text-gray-500 hover:text-red-400"
              title="Delete chat"
            >
              <Trash2 className="h-3 w-3" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────
export function DoubtSolver({ docId }: Props) {
  const [messages,     setMessages]     = useState<ChatMessage[]>([]);
  const [input,        setInput]        = useState("");
  const [loading,      setLoading]      = useState(false);
  const [mode,         setMode]         = useState<"standard" | "eli5">("standard");
  const [showSaved,    setShowSaved]    = useState(false);
  const [showSidebar,  setShowSidebar]  = useState(false);
  const [sessions,     setSessions]     = useState<ChatSessionSummary[]>([]);
  const [activeSession, setActiveSession] = useState<string | null>(null);
  const [sessionsLoading, setSessionsLoading] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef  = useRef<AbortController | null>(null);

  const { speak, stop, speaking, isSupported: ttsSupported } = useSpeech();
  const { saved, saveAnswer, removeAnswer, isSaved } = useSavedAnswers();

  const handleVoiceResult = useCallback((transcript: string) => {
    setInput((prev) => prev ? `${prev} ${transcript}` : transcript);
  }, []);
  const { startListening, stopListening, listening, isSupported: voiceSupported } = useVoiceInput(handleVoiceResult);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => () => { abortRef.current?.abort(); }, []);

  // Load session list on mount
  useEffect(() => {
    loadSessions();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadSessions = async () => {
    try {
      const data = await fetchChatSessions();
      setSessions(data.map((s) => ({
        id: s.id,
        title: s.title,
        doc_id: s.doc_id,
        updated_at: s.updated_at,
        message_count: s.message_count,
      })));
    } catch {
      // non-critical — don't toast
    }
  };

  // Load messages when active session changes
  useEffect(() => {
    if (!activeSession) { setMessages([]); return; }
    (async () => {
      try {
        const msgs = await fetchChatMessages(activeSession);
        setMessages(msgs.map((m) => ({
          id: nextId(),
          dbId: m.id,
          role: m.role as "user" | "assistant",
          content: m.content,
          mode: m.mode as "standard" | "eli5",
          sources: (() => {
            try { return JSON.parse(m.sources_json) as SourceChunk[]; } catch { return []; }
          })(),
          timestamp: new Date(m.created_at),
        })));
      } catch {
        toast.error("Failed to load chat messages");
      }
    })();
  }, [activeSession]);

  const handleNewSession = async () => {
    setSessionsLoading(true);
    try {
      const title = docId ? `Doc chat · ${new Date().toLocaleDateString()}` : `Chat · ${new Date().toLocaleDateString()}`;
      const session = await createChatSession(title, docId);
      setSessions((prev) => [{ ...session }, ...prev]);
      setActiveSession(session.id);
      setMessages([]);
    } catch {
      toast.error("Could not create chat session");
    }
    setSessionsLoading(false);
  };

  const handleSelectSession = (id: string) => {
    if (id === activeSession) return;
    abortRef.current?.abort();
    setLoading(false);
    setActiveSession(id);
  };

  const handleDeleteSession = async (id: string) => {
    try {
      await deleteChatSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (activeSession === id) {
        setActiveSession(null);
        setMessages([]);
      }
    } catch {
      toast.error("Failed to delete chat");
    }
  };

  const handleRenameSession = async (id: string, title: string) => {
    try {
      await renameChatSession(id, title);
      setSessions((prev) => prev.map((s) => s.id === id ? { ...s, title } : s));
    } catch {
      toast.error("Failed to rename chat");
    }
  };

  const sendMessage = useCallback(async (question: string) => {
    if (!question.trim() || loading) return;

    abortRef.current?.abort();

    // Ensure we have an active session — create one on first message
    let sessionId = activeSession;
    if (!sessionId) {
      try {
        const title = question.slice(0, 60) + (question.length > 60 ? "…" : "");
        const session = await createChatSession(title, docId);
        sessionId = session.id;
        setActiveSession(session.id);
        setSessions((prev) => [{ ...session }, ...prev]);
      } catch {
        toast.error("Could not start chat session");
        return;
      }
    }

    const userMsgId = nextId();
    const assistId  = nextId();

    const userMsg: ChatMessage   = { id: userMsgId, role: "user",      content: question.trim(), timestamp: new Date() };
    const assistMsg: ChatMessage = { id: assistId,  role: "assistant", content: "",              timestamp: new Date(), mode };

    setMessages((prev) => [...prev, userMsg, assistMsg]);
    setInput("");
    setLoading(true);

    // Persist user message to DB (fire-and-forget)
    appendChatMessage(sessionId, "user", question.trim(), "[]", mode).catch(() => {});

    const history = messages.map(({ role, content }) => ({ role, content }));

    let finalSources: SourceChunk[] = [];

    abortRef.current = streamPost(
      "/api/doubt/stream",
      { question: question.trim(), doc_id: docId ?? null, mode, k: 5, conversation_history: history },
      {
        onToken: (token) => {
          setMessages((prev) =>
            prev.map((m) => m.id === assistId ? { ...m, content: m.content + token } : m)
          );
        },
        onDone: (meta) => {
          const sources = (meta.sources ?? []) as SourceChunk[];
          finalSources = sources;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistId
                ? { ...m, sources, sourceNames: (meta.sourceNames ?? []) }
                : m
            )
          );
          setLoading(false);

          // Persist assistant message to DB
          setMessages((prev) => {
            const assistantMsg = prev.find((m) => m.id === assistId);
            if (assistantMsg && sessionId) {
              appendChatMessage(
                sessionId,
                "assistant",
                assistantMsg.content,
                JSON.stringify(finalSources),
                mode,
              ).catch(() => {});
              // Bump session message count in sidebar
              setSessions((ss) =>
                ss.map((s) =>
                  s.id === sessionId
                    ? { ...s, message_count: s.message_count + 2, updated_at: new Date().toISOString() }
                    : s
                )
              );
            }
            return prev;
          });
        },
        onError: (err) => {
          if (err.includes("AbortError") || err === "") { setLoading(false); return; }
          toast.error(err || "Failed to get answer");
          setMessages((prev) => prev.filter((m) => m.id !== assistId && m.id !== userMsgId));
          setLoading(false);
        },
      }
    );
  }, [loading, messages, docId, mode, activeSession]);

  const handleRegenerate = useCallback((question: string) => {
    abortRef.current?.abort();
    setMessages((prev) => {
      const lastAssist = [...prev].reverse().findIndex((m) => m.role === "assistant");
      if (lastAssist === -1) return prev;
      return prev.slice(0, prev.length - 1 - lastAssist);
    });
    sendMessage(question);
  }, [sendMessage]);

  return (
    <div className="flex gap-0 h-[700px] relative">
      {/* ── Sidebar ──────────────────────────────────────────────────────────── */}
      <AnimatePresence>
        {showSidebar && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 220, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="shrink-0 overflow-hidden border-r border-gray-800 pr-3 mr-4"
          >
            <SessionSidebar
              sessions={sessions}
              activeId={activeSession}
              onSelect={handleSelectSession}
              onNew={handleNewSession}
              onDelete={handleDeleteSession}
              onRename={handleRenameSession}
              loading={sessionsLoading}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Main chat area ────────────────────────────────────────────────────── */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Header */}
        <div className="flex items-start gap-4 pb-4 border-b border-gray-800 mb-4 shrink-0">
          {/* Sidebar toggle */}
          <button
            onClick={() => setShowSidebar((v) => !v)}
            title={showSidebar ? "Hide history" : "Show history"}
            className={clsx(
              "p-2 rounded-xl border transition-all shrink-0 self-center",
              showSidebar
                ? "bg-brand-600/20 border-brand-500/40 text-brand-400"
                : "bg-gray-900 border-gray-800 text-gray-500 hover:text-gray-300"
            )}
          >
            {showSidebar ? <ChevronLeft className="h-4 w-4" /> : <History className="h-4 w-4" />}
          </button>

          <div className="p-3 rounded-2xl bg-cyan-500/10 text-cyan-400 shrink-0">
            <MessageCircle className="h-7 w-7" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="section-heading">RAG Doubt Solver</h2>
            <p className="text-sm text-gray-400 mt-1 truncate">
              {activeSession
                ? sessions.find((s) => s.id === activeSession)?.title ?? "Active chat"
                : "Ask anything about your uploaded documents."}
            </p>
          </div>

          {/* Saved answers button */}
          {saved.length > 0 && (
            <button
              onClick={() => setShowSaved((s) => !s)}
              title="Saved answers"
              className={clsx(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all shrink-0",
                showSaved
                  ? "bg-brand-600 border-brand-500 text-white"
                  : "bg-gray-900 border-gray-700 text-gray-400 hover:border-gray-600"
              )}
            >
              <BookMarked className="h-3.5 w-3.5" />
              {saved.length}
            </button>
          )}

          {/* New chat */}
          <button
            onClick={handleNewSession}
            disabled={sessionsLoading}
            title="New chat"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border bg-gray-900 border-gray-700 text-gray-400 hover:border-brand-500 hover:text-brand-400 transition-all shrink-0"
          >
            <Plus className="h-3.5 w-3.5" />
            New
          </button>

          {/* Mode toggle */}
          <div className="flex gap-1 shrink-0">
            {(["standard", "eli5"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={clsx(
                  "px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all",
                  mode === m
                    ? "bg-brand-600 border-brand-500 text-white"
                    : "bg-gray-900 border-gray-700 text-gray-400 hover:border-gray-600",
                )}
              >
                {m === "eli5" ? "🧒 ELI5" : "📚 Standard"}
              </button>
            ))}
          </div>
        </div>

        {/* Saved Answers Panel */}
        <AnimatePresence>
          {showSaved && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden shrink-0 mb-3"
            >
              <div className="glass-card p-4 space-y-2 max-h-52 overflow-y-auto">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-1">Bookmarked Answers</p>
                {saved.map((s) => (
                  <div key={s.id} className="flex items-start gap-2 p-2.5 rounded-xl bg-gray-800/60 border border-gray-700/50">
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-brand-400 truncate">{s.question}</p>
                      <p className="text-xs text-gray-400 mt-0.5 line-clamp-2">{s.answer.slice(0, 120)}…</p>
                    </div>
                    <button
                      onClick={() => removeAnswer(s.id)}
                      className="p-1 rounded-lg text-gray-600 hover:text-red-400 transition-colors shrink-0"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto space-y-4 pr-1 pb-2">
          {messages.length === 0 && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-4"
            >
              <div className="text-center py-8">
                <div className="h-14 w-14 rounded-2xl bg-cyan-500/10 text-cyan-400 flex items-center justify-center mx-auto mb-3">
                  <Bot className="h-8 w-8" />
                </div>
                <p className="text-gray-400 text-sm">
                  {docId
                    ? "I've indexed your documents. Ask me anything!"
                    : "Upload a document first, or ask any general study question."}
                </p>
                <p className="text-xs text-gray-600 mt-1">
                  Mode: <span className="text-brand-400 font-medium">{mode === "eli5" ? "ELI5 (simplified)" : "Standard (detailed)"}</span>
                </p>
              </div>

              <div className="space-y-2">
                <p className="text-xs text-gray-500 font-medium uppercase tracking-widest">Suggested Questions</p>
                {STARTER_QUESTIONS.map((q) => (
                  <motion.button
                    key={q}
                    whileHover={{ x: 4 }}
                    onClick={() => sendMessage(q)}
                    className="w-full text-left flex items-center gap-3 px-4 py-3 rounded-xl bg-gray-900 border border-gray-800 hover:border-brand-600 hover:bg-gray-800/50 text-sm text-gray-300 transition-all group"
                  >
                    <Lightbulb className="h-4 w-4 text-brand-400 shrink-0 group-hover:text-brand-300" />
                    {q}
                    <ArrowRight className="h-3.5 w-3.5 text-gray-600 group-hover:text-brand-400 ml-auto transition-colors" />
                  </motion.button>
                ))}
              </div>
            </motion.div>
          )}

          <AnimatePresence initial={false}>
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25 }}
                className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
              >
                <div className={`h-8 w-8 rounded-xl flex items-center justify-center shrink-0 mt-1 ${
                  msg.role === "user"
                    ? "bg-brand-600 text-white"
                    : "bg-gray-800 text-cyan-400 border border-gray-700"
                }`}>
                  {msg.role === "user" ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                </div>

                <div className={`max-w-[85%] space-y-1.5 ${msg.role === "user" ? "items-end" : "items-start"} flex flex-col`}>
                  {msg.role === "assistant" && msg.mode && (
                    <span className="text-[10px] text-gray-600 font-medium">
                      {msg.mode === "eli5" ? "🧒 ELI5" : "📚 Standard"}
                    </span>
                  )}

                  <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "bg-brand-600 text-white rounded-tr-md"
                      : "bg-gray-900 border border-gray-800 text-gray-200 rounded-tl-md"
                  }`}>
                    {msg.role === "assistant" ? (
                      <div className="prose prose-invert prose-sm max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {msg.content + (loading && messages[messages.length - 1]?.id === msg.id && msg.content.length > 0 ? " ▍" : "")}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <p>{msg.content}</p>
                    )}
                  </div>

                  {msg.sources && msg.sources.length > 0 && (
                    <SourceChips sources={msg.sources} />
                  )}

                  <div className={`flex items-center gap-1.5 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
                    {msg.role === "assistant" && (
                      <>
                        <CopyButton text={msg.content} />
                        {ttsSupported && (
                          <button
                            onClick={() => speaking ? stop() : speak(msg.content)}
                            title={speaking ? "Stop" : "Read aloud"}
                            className={`p-1 rounded-lg transition-colors ${speaking ? "text-brand-400" : "text-gray-600 hover:text-gray-400 hover:bg-gray-800"}`}
                          >
                            {speaking ? <VolumeX className="h-3.5 w-3.5" /> : <Volume2 className="h-3.5 w-3.5" />}
                          </button>
                        )}
                        {messages[messages.length - 1]?.id === msg.id && (
                          <button
                            onClick={() => {
                              const lastUser = [...messages].reverse().find((m) => m.role === "user");
                              if (lastUser) handleRegenerate(lastUser.content);
                            }}
                            disabled={loading}
                            title="Regenerate answer"
                            className="p-1 rounded-lg text-gray-600 hover:text-brand-400 hover:bg-gray-800 transition-colors"
                          >
                            <RotateCcw className="h-3.5 w-3.5" />
                          </button>
                        )}
                        <button
                          onClick={() => {
                            const lastUser = [...messages].reverse().find((m) => m.role === "user");
                            if (!lastUser) return;
                            if (isSaved(lastUser.content)) {
                              toast("Already bookmarked");
                            } else {
                              saveAnswer(lastUser.content, msg.content);
                              toast.success("Answer bookmarked!");
                            }
                          }}
                          title="Bookmark answer"
                          className={`p-1 rounded-lg transition-colors ${isSaved([...messages].reverse().find((m) => m.role === "user")?.content ?? "") ? "text-yellow-400" : "text-gray-600 hover:text-yellow-400 hover:bg-gray-800"}`}
                        >
                          {isSaved([...messages].reverse().find((m) => m.role === "user")?.content ?? "")
                            ? <BookmarkCheck className="h-3.5 w-3.5" />
                            : <Bookmark className="h-3.5 w-3.5" />}
                        </button>
                      </>
                    )}
                    <p className="text-[10px] text-gray-600">
                      {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </p>
                  </div>

                  {msg.followUpQuestions && msg.followUpQuestions.length > 0 && (
                    <div className="space-y-1 w-full">
                      <p className="text-[10px] text-gray-500 font-medium">Follow-up:</p>
                      {msg.followUpQuestions.map((fq, fi) => (
                        <button
                          key={fi}
                          onClick={() => sendMessage(fq)}
                          className="block w-full text-left text-xs text-brand-400 hover:text-brand-300 px-3 py-1.5 rounded-lg bg-brand-500/8 border border-brand-500/20 hover:bg-brand-500/15 transition-colors"
                        >
                          → {fq}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Spinner — only while waiting for first token */}
          {loading && messages[messages.length - 1]?.role === "assistant" && messages[messages.length - 1]?.content.length === 0 && (
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="flex gap-3 items-center"
            >
              <div className="h-8 w-8 rounded-xl bg-gray-800 border border-gray-700 text-cyan-400 flex items-center justify-center shrink-0">
                <Bot className="h-4 w-4" />
              </div>
              <div className="flex items-center gap-2 px-4 py-3 rounded-2xl bg-gray-900 border border-gray-800">
                <Spinner size="sm" />
                <span className="text-sm text-gray-400">Thinking…</span>
              </div>
            </motion.div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="shrink-0 pt-4 border-t border-gray-800">
          <div className="flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), sendMessage(input))}
              placeholder={listening ? "Listening…" : "Ask a question about your notes…"}
              disabled={loading}
              aria-label="Type your question"
              className={clsx("input-field flex-1", listening && "border-red-500/50 ring-1 ring-red-500/30")}
            />
            {voiceSupported && (
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => listening ? stopListening() : startListening()}
                title={listening ? "Stop listening" : "Voice input"}
                aria-label="Voice input"
                className={clsx(
                  "px-3 rounded-xl border transition-all",
                  listening
                    ? "bg-red-500/20 border-red-500/50 text-red-400 animate-pulse"
                    : "bg-gray-800 border-gray-700 text-gray-400 hover:text-gray-200"
                )}
              >
                {listening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
              </motion.button>
            )}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => sendMessage(input)}
              disabled={loading || !input.trim()}
              aria-label="Send message"
              className="btn-primary px-4"
            >
              {loading ? <Spinner size="sm" /> : <Send className="h-4 w-4" />}
            </motion.button>
          </div>
          <p className="text-xs text-gray-600 mt-2">Enter to send · Shift+Enter for new line{voiceSupported ? " · Mic for voice" : ""}</p>
        </div>
      </div>
    </div>
  );
}
