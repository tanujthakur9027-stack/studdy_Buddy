"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageCircle, Send, Bot, User, Lightbulb, ArrowRight,
  Copy, CheckCheck, FileText, Volume2, VolumeX, RotateCcw,
  Bookmark, BookmarkCheck, Mic, MicOff, BookMarked, X,
} from "lucide-react";
import { Spinner } from "@/components/ui";
import { streamPost } from "@/lib/streamApi";
import { useSpeech, useVoiceInput } from "@/hooks/useSpeech";
import { useSavedAnswers } from "@/hooks/useSavedAnswers";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "@/types";
import type { SourceChunk } from "@/lib/api";
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
  // Deduplicate by filename+page
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

// ── Main component ─────────────────────────────────────────────────────────────
export function DoubtSolver({ docId }: Props) {
  const [messages,  setMessages]  = useState<ChatMessage[]>([]);
  const [input,     setInput]     = useState("");
  const [loading,   setLoading]   = useState(false);
  const [mode,      setMode]      = useState<"standard" | "eli5">("standard");
  const [showSaved, setShowSaved] = useState(false);
  const bottomRef  = useRef<HTMLDivElement>(null);
  const abortRef   = useRef<AbortController | null>(null);

  const { speak, stop, speaking, isSupported: ttsSupported } = useSpeech();
  const { saved, saveAnswer, removeAnswer, isSaved } = useSavedAnswers();

  const handleVoiceResult = useCallback((transcript: string) => {
    setInput((prev) => prev ? `${prev} ${transcript}` : transcript);
  }, []);
  const { startListening, stopListening, listening, isSupported: voiceSupported } = useVoiceInput(handleVoiceResult);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Cancel any in-flight stream when unmounting
  useEffect(() => () => { abortRef.current?.abort(); }, []);

  const sendMessage = useCallback((question: string) => {
    if (!question.trim() || loading) return;

    // Abort any previous in-flight stream
    abortRef.current?.abort();

    const userMsgId  = nextId();
    const assistId   = nextId();

    // Add user bubble immediately
    const userMsg: ChatMessage = { id: userMsgId, role: "user", content: question.trim(), timestamp: new Date() };
    // Add a streaming assistant bubble (starts empty)
    const assistMsg: ChatMessage = { id: assistId, role: "assistant", content: "", timestamp: new Date(), mode };

    setMessages((prev) => [...prev, userMsg, assistMsg]);
    setInput("");
    setLoading(true);

    const history = messages.map(({ role, content }) => ({ role, content }));

    abortRef.current = streamPost(
      "/api/doubt/stream",
      { question: question.trim(), doc_id: docId ?? null, mode, k: 5, conversation_history: history },
      {
        onToken: (token) => {
          // Append token to the streaming assistant bubble
          setMessages((prev) =>
            prev.map((m) => m.id === assistId ? { ...m, content: m.content + token } : m)
          );
        },
        onDone: (meta) => {
          // Attach source names when stream finishes
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistId
                ? { ...m, sourceNames: (meta.sourceNames ?? (meta.sources as string[] | undefined) ?? []) }
                : m
            )
          );
          setLoading(false);
        },
        onError: (err) => {
          if (err.includes("AbortError") || err === "") { setLoading(false); return; }
          toast.error(err || "Failed to get answer");
          // Remove the empty assistant bubble on error
          setMessages((prev) => prev.filter((m) => m.id !== assistId && m.id !== userMsgId));
          setLoading(false);
        },
      }
    );
  }, [loading, messages, docId, mode]);

  // Regenerate: cancel current stream and re-ask last question
  const handleRegenerate = useCallback((question: string) => {
    abortRef.current?.abort();
    // Remove last assistant message and re-send
    setMessages((prev) => {
      const lastAssist = [...prev].reverse().findIndex((m) => m.role === "assistant");
      if (lastAssist === -1) return prev;
      const idx = prev.length - 1 - lastAssist;
      return prev.slice(0, idx);
    });
    sendMessage(question);
  }, [sendMessage]);

  return (
    <div className="flex flex-col h-[700px]">
      {/* Header */}
      <div className="flex items-start gap-4 pb-4 border-b border-gray-800 mb-4 shrink-0">
        <div className="p-3 rounded-2xl bg-cyan-500/10 text-cyan-400">
          <MessageCircle className="h-7 w-7" />
        </div>
        <div className="flex-1">
          <h2 className="section-heading">RAG Doubt Solver</h2>
          <p className="text-sm text-gray-400 mt-1">
            Ask anything about your uploaded documents — powered by Retrieval-Augmented Generation.
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
                {/* Mode badge for assistant */}
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

                {/* Rich sources */}
                {msg.sources && msg.sources.length > 0 && (
                  <SourceChips sources={msg.sources} />
                )}

                {/* Action row: copy · read aloud · regenerate · bookmark */}
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
                      {/* Regenerate — only on last assistant message */}
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
                      {/* Bookmark */}
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

                {/* Follow-up questions */}
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

        {/* Show spinner only while waiting for the first token */}
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
          {/* Voice input button */}
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
  );
}
