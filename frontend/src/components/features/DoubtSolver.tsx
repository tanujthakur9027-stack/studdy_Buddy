"use client";
import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageCircle, Send, Bot, User, Lightbulb, ArrowRight } from "lucide-react";
import { solveDoubt } from "@/lib/api";
import { Spinner } from "@/components/ui";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "@/types";
import toast from "react-hot-toast";

interface Props { docId?: string }

const STARTER_QUESTIONS = [
  "What is the central idea of this document?",
  "Explain the main concepts in simple terms",
  "What are the most important formulas?",
  "Compare and contrast the key theories",
  "What should I focus on for exams?",
];

export function DoubtSolver({ docId }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput]       = useState("");
  const [loading, setLoading]   = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (question: string) => {
    if (!question.trim() || loading) return;
    const userMsg: ChatMessage = {
      role: "user",
      content: question.trim(),
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    const history = messages.map(({ role, content }) => ({ role, content }));
    try {
      const data = await solveDoubt({
        question: question.trim(),
        doc_id: docId,
        conversation_history: history,
      });
      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: data.answer,
        sources: data.sources,
        followUpQuestions: data.follow_up_questions,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (e: unknown) {
      toast.error((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed to get answer");
      setMessages((prev) => prev.filter((m) => m !== userMsg));
    }
    setLoading(false);
  };

  return (
    <div className="flex flex-col h-[700px]">
      {/* Header */}
      <div className="flex items-start gap-4 pb-5 border-b border-gray-800 mb-4 shrink-0">
        <div className="p-3 rounded-2xl bg-cyan-500/10 text-cyan-400">
          <MessageCircle className="h-7 w-7" />
        </div>
        <div>
          <h2 className="section-heading">RAG Doubt Solver</h2>
          <p className="text-sm text-gray-400 mt-1">
            Ask anything about your uploaded documents — powered by Retrieval-Augmented Generation.
          </p>
        </div>
      </div>

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
          {messages.map((msg, i) => (
            <motion.div
              key={i}
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

              <div className={`max-w-[85%] space-y-2 ${msg.role === "user" ? "items-end" : "items-start"} flex flex-col`}>
                <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "bg-brand-600 text-white rounded-tr-md"
                    : "bg-gray-900 border border-gray-800 text-gray-200 rounded-tl-md"
                }`}>
                  {msg.role === "assistant" ? (
                    <div className="prose prose-invert prose-sm max-w-none">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                    </div>
                  ) : (
                    <p>{msg.content}</p>
                  )}
                </div>

                {/* Sources */}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {msg.sources.map((src, si) => (
                      <span key={si} className="text-[10px] px-2 py-0.5 rounded-full bg-gray-800 border border-gray-700 text-gray-400">
                        📄 {src}
                      </span>
                    ))}
                  </div>
                )}

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

                <p className="text-[10px] text-gray-600">
                  {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </p>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {loading && (
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
        <div className="flex gap-3">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), sendMessage(input))}
            placeholder="Ask a question about your notes…"
            disabled={loading}
            className="input-field flex-1"
          />
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => sendMessage(input)}
            disabled={loading || !input.trim()}
            className="btn-primary px-4"
          >
            {loading ? <Spinner size="sm" /> : <Send className="h-4 w-4" />}
          </motion.button>
        </div>
        <p className="text-xs text-gray-600 mt-2">Press Enter to send · Shift+Enter for new line</p>
      </div>
    </div>
  );
}
