"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Lightbulb, Sparkles, BookOpen, ChevronDown, ChevronUp, Send } from "lucide-react";
import { explainTopic } from "@/lib/api";
import { Spinner, Badge } from "@/components/ui";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import toast from "react-hot-toast";

interface Props {
  docId?: string;
}

const LEVEL_CONFIG = {
  eli5:         { label: "ELI5 (Age 5–8)",   color: "green"  as const, emoji: "🧒" },
  beginner:     { label: "Beginner",           color: "blue"   as const, emoji: "📚" },
  intermediate: { label: "Intermediate",       color: "purple" as const, emoji: "🎓" },
};

const SAMPLE_TOPICS = [
  "Photosynthesis", "Newton's Laws", "Machine Learning", "Mitosis vs Meiosis",
  "The French Revolution", "Recursion in programming", "Gravity",
];

export function ExplainModule({ docId }: Props) {
  const [topic, setTopic] = useState("");
  const [level, setLevel] = useState<"eli5" | "beginner" | "intermediate">("eli5");
  const [result, setResult] = useState<{ explanation: string; analogy: string; key_points: string[] } | null>(null);
  const [loading, setLoading] = useState(false);
  const [showPoints, setShowPoints] = useState(true);

  const handleExplain = async () => {
    if (!topic.trim()) { toast.error("Please enter a topic"); return; }
    setLoading(true);
    setResult(null);
    try {
      const data = await explainTopic({ topic: topic.trim(), doc_id: docId, level });
      setResult(data);
    } catch (e: unknown) {
      toast.error((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Explanation failed");
    }
    setLoading(false);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div className="p-3 rounded-2xl bg-yellow-500/10 text-yellow-400">
          <Lightbulb className="h-7 w-7" />
        </div>
        <div>
          <h2 className="section-heading">Explain Like I&apos;m 10</h2>
          <p className="text-sm text-gray-400 mt-1">
            Get crystal-clear, age-appropriate explanations for any topic with analogies and key points.
          </p>
        </div>
      </div>

      {/* Level Selector */}
      <div className="flex gap-2 flex-wrap">
        {(Object.entries(LEVEL_CONFIG) as [typeof level, typeof LEVEL_CONFIG[typeof level]][]).map(([key, cfg]) => (
          <button
            key={key}
            onClick={() => setLevel(key)}
            className={`px-4 py-2 rounded-xl text-sm font-medium border transition-all duration-200 ${
              level === key
                ? "bg-brand-600 border-brand-500 text-white shadow-lg shadow-brand-900/30"
                : "bg-gray-900 border-gray-700 text-gray-400 hover:border-gray-600 hover:text-gray-200"
            }`}
          >
            {cfg.emoji} {cfg.label}
          </button>
        ))}
      </div>

      {/* Topic Input */}
      <div className="flex gap-3">
        <input
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleExplain()}
          placeholder="Enter a topic, concept, or question…"
          className="input-field flex-1"
        />
        <motion.button
          whileHover={{ scale: 1.04 }}
          whileTap={{ scale: 0.96 }}
          onClick={handleExplain}
          disabled={loading || !topic.trim()}
          className="btn-primary px-4"
        >
          {loading ? <Spinner size="sm" /> : <Send className="h-4 w-4" />}
          {loading ? "Explaining…" : "Explain"}
        </motion.button>
      </div>

      {/* Quick Topics */}
      <div className="flex flex-wrap gap-2">
        {SAMPLE_TOPICS.map((t) => (
          <button
            key={t}
            onClick={() => setTopic(t)}
            className="text-xs px-3 py-1.5 rounded-full bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-gray-200 border border-gray-700/50 transition-colors"
          >
            {t}
          </button>
        ))}
      </div>

      {/* Result */}
      <AnimatePresence mode="wait">
        {loading && (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="flex items-center justify-center gap-3 p-12 glass-card"
          >
            <Spinner size="lg" />
            <span className="text-gray-400 text-sm">Crafting your explanation…</span>
          </motion.div>
        )}

        {result && !loading && (
          <motion.div
            key="result"
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            {/* Main Explanation */}
            <div className="glass-card p-6">
              <div className="flex items-center gap-2 mb-4">
                <Sparkles className="h-4 w-4 text-brand-400" />
                <span className="text-xs font-semibold text-brand-400 uppercase tracking-widest">
                  {LEVEL_CONFIG[level].label} Explanation
                </span>
                <Badge variant={LEVEL_CONFIG[level].color}>{LEVEL_CONFIG[level].emoji} {level.toUpperCase()}</Badge>
              </div>
              <div className="prose prose-invert prose-sm max-w-none text-gray-200 leading-relaxed">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.explanation}</ReactMarkdown>
              </div>
            </div>

            {/* Analogy */}
            {result.analogy && (
              <motion.div
                initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }}
                className="p-5 rounded-2xl bg-amber-500/8 border border-amber-500/20"
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xl">💡</span>
                  <span className="text-sm font-semibold text-amber-400">Think of it this way…</span>
                </div>
                <p className="text-gray-300 text-sm leading-relaxed italic">{result.analogy}</p>
              </motion.div>
            )}

            {/* Key Points */}
            {result.key_points?.length > 0 && (
              <motion.div
                initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 }}
                className="glass-card overflow-hidden"
              >
                <button
                  onClick={() => setShowPoints(!showPoints)}
                  className="w-full flex items-center justify-between p-5 hover:bg-gray-800/30 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <BookOpen className="h-4 w-4 text-green-400" />
                    <span className="text-sm font-semibold text-gray-200">
                      Key Points ({result.key_points.length})
                    </span>
                  </div>
                  {showPoints ? <ChevronUp className="h-4 w-4 text-gray-500" /> : <ChevronDown className="h-4 w-4 text-gray-500" />}
                </button>
                <AnimatePresence>
                  {showPoints && (
                    <motion.ul
                      initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="px-5 pb-5 space-y-2 border-t border-gray-800">
                        {result.key_points.map((pt, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm text-gray-300 pt-2">
                            <span className="mt-0.5 h-5 w-5 shrink-0 rounded-full bg-green-500/15 text-green-400 text-xs flex items-center justify-center font-bold">
                              {i + 1}
                            </span>
                            {pt}
                          </li>
                        ))}
                      </div>
                    </motion.ul>
                  )}
                </AnimatePresence>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
