"use client";
import { useState, useRef, useEffect } from "react";
import { motion } from "framer-motion";
import {
  FileText, Sparkles, Printer, X, Loader2, RotateCcw,
} from "lucide-react";
import { streamPost } from "@/lib/streamApi";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import toast from "react-hot-toast";

interface Props {
  docId: string;
  filename: string;
  onClose: () => void;
}

export function CheatSheet({ docId, filename, onClose }: Props) {
  const [topic,      setTopic]      = useState("");
  const [content,    setContent]    = useState("");
  const [loading,    setLoading]    = useState(false);
  const [generated,  setGenerated]  = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  // Auto-generate on open
  useEffect(() => {
    generate("");
    return () => { abortRef.current?.abort(); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const generate = (focusTopic: string) => {
    abortRef.current?.abort();
    setContent("");
    setLoading(true);
    setGenerated(false);

    abortRef.current = streamPost(
      "/api/cheatsheet",
      { doc_id: docId, topic: focusTopic },
      {
        onToken: (token) => setContent((prev) => prev + token),
        onDone: () => { setLoading(false); setGenerated(true); },
        onError: (err) => {
          if (!err.includes("AbortError")) toast.error(err || "Cheat sheet generation failed");
          setLoading(false);
        },
      },
    );
  };

  const handlePrint = () => window.print();

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/70 backdrop-blur-sm overflow-y-auto py-8 px-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.96, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.96 }}
        className="w-full max-w-2xl bg-gray-950 border border-gray-800 rounded-2xl shadow-2xl"
      >
        {/* Header */}
        <div className="flex items-start gap-3 p-5 border-b border-gray-800">
          <div className="p-2 rounded-xl bg-brand-500/10 text-brand-400 shrink-0">
            <FileText className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-base font-bold text-white">AI Cheat Sheet</h2>
            <p className="text-xs text-gray-500 truncate mt-0.5">{filename}</p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {generated && (
              <button
                onClick={handlePrint}
                title="Print / Save as PDF"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gray-800 border border-gray-700 text-gray-300 hover:text-white text-xs font-medium transition-colors"
              >
                <Printer className="h-3.5 w-3.5" /> Print
              </button>
            )}
            <button
              onClick={() => generate(topic)}
              disabled={loading}
              title="Regenerate"
              className="p-1.5 rounded-xl bg-gray-800 border border-gray-700 text-gray-400 hover:text-gray-200 transition-colors"
            >
              <RotateCcw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-xl bg-gray-800 border border-gray-700 text-gray-400 hover:text-red-400 transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Topic filter */}
        <div className="flex gap-2 p-4 border-b border-gray-800/60">
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && generate(topic)}
            placeholder="Focus on a specific topic (optional)…"
            className="input-field flex-1 text-sm py-2"
          />
          <button
            onClick={() => generate(topic)}
            disabled={loading}
            className="btn-primary px-4 py-2 text-sm"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            {loading ? "Generating…" : "Generate"}
          </button>
        </div>

        {/* Content area — printable */}
        <div
          id="cheatsheet-content"
          className="p-6 min-h-[320px]"
        >
          {!content && loading && (
            <div className="flex items-center justify-center gap-3 py-16 text-gray-500">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span className="text-sm">Analysing document and generating cheat sheet…</span>
            </div>
          )}

          {content && (
            <div className="prose prose-invert prose-sm max-w-none
              prose-headings:text-brand-400 prose-headings:font-bold prose-headings:text-base
              prose-headings:border-b prose-headings:border-gray-800 prose-headings:pb-1 prose-headings:mb-3
              prose-li:text-gray-300 prose-p:text-gray-300
              prose-code:bg-gray-800 prose-code:text-green-400 prose-code:px-1 prose-code:rounded
              prose-strong:text-white"
            >
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {content + (loading ? " ▍" : "")}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-gray-800 flex items-center justify-between">
          <p className="text-[10px] text-gray-600">
            {generated ? "✓ Generated from your document" : "Powered by StudyBuddy AI"}
          </p>
          {generated && (
            <p className="text-[10px] text-gray-600">Press Print to save as PDF</p>
          )}
        </div>
      </motion.div>

      {/* Print-only styles injected inline */}
      <style>{`
        @media print {
          body > * { display: none !important; }
          #cheatsheet-content { display: block !important; }
          #cheatsheet-content { font-family: system-ui, sans-serif; font-size: 11pt; color: #000; }
          #cheatsheet-content h2 { font-size: 13pt; font-weight: 700; border-bottom: 1px solid #ccc; padding-bottom: 4px; margin: 12px 0 6px; color: #1a1a1a; }
          #cheatsheet-content li, #cheatsheet-content p { font-size: 10pt; margin: 2px 0; color: #222; }
          #cheatsheet-content code { background: #f3f4f6; padding: 0 3px; border-radius: 3px; font-size: 9pt; }
        }
      `}</style>
    </div>
  );
}
