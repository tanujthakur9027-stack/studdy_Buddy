"use client";
import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain, CheckCircle2, XCircle, Lightbulb,
  ChevronDown, ChevronUp, RotateCcw, Sparkles, BookOpen,
} from "lucide-react";
import { evaluateFeynman } from "@/lib/api";
import type { FeynmanResponse } from "@/lib/api";
import { Spinner, Badge, ProgressBar } from "@/components/ui";
import toast from "react-hot-toast";
import { clsx } from "clsx";

interface Props { docId?: string }

const GRADE_META: Record<string, { label: string; bg: string; text: string; ring: string }> = {
  S: { label: "Mastered!",      bg: "bg-yellow-500/15 border-yellow-500/30", text: "text-yellow-400", ring: "#eab308" },
  A: { label: "Excellent!",     bg: "bg-green-500/15  border-green-500/30",  text: "text-green-400",  ring: "#22c55e" },
  B: { label: "Good progress!", bg: "bg-blue-500/15   border-blue-500/30",   text: "text-blue-400",   ring: "#3b82f6" },
  C: { label: "Keep studying!", bg: "bg-orange-500/15 border-orange-500/30", text: "text-orange-400", ring: "#f97316" },
  D: { label: "Needs work",     bg: "bg-red-500/15    border-red-500/30",    text: "text-red-400",    ring: "#ef4444" },
};

const SAMPLE_CONCEPTS = [
  "Photosynthesis", "Newton's Second Law", "Machine Learning",
  "Supply and Demand", "DNA Replication", "The Water Cycle",
];

// ── Score ring (SVG circle) ────────────────────────────────────────────────
function ScoreRing({ score, grade }: { score: number; grade: string }) {
  const gm = GRADE_META[grade] ?? GRADE_META["D"];
  const r = 44;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;

  return (
    <div className="relative h-28 w-28 shrink-0">
      <svg className="h-full w-full -rotate-90" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r={r} fill="none" stroke="#1f2937" strokeWidth="8" />
        <motion.circle
          cx="50" cy="50" r={r}
          fill="none"
          stroke={gm.ring}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circ}
          initial={{ strokeDashoffset: circ }}
          animate={{ strokeDashoffset: circ - dash }}
          transition={{ duration: 1, ease: "easeOut" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={clsx("text-3xl font-black", gm.text)}>{score}</span>
        <span className="text-[10px] text-gray-500 font-medium">/ 100</span>
      </div>
    </div>
  );
}

// ── Q&A Accordion Item ─────────────────────────────────────────────────────
function QAItem({ q, a, index }: { q: string; a: string; index: number }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border border-gray-800 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-start justify-between gap-3 px-4 py-3 text-left hover:bg-gray-800/40 transition-colors"
      >
        <span className="flex items-center gap-2 text-sm text-gray-200 flex-1">
          <span className="shrink-0 h-5 w-5 rounded-full bg-brand-500/20 text-brand-400 text-[10px] font-bold flex items-center justify-center">
            {index + 1}
          </span>
          {q}
        </span>
        {open
          ? <ChevronUp className="h-4 w-4 text-gray-500 shrink-0 mt-0.5" />
          : <ChevronDown className="h-4 w-4 text-gray-500 shrink-0 mt-0.5" />}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-3 pt-1 border-t border-gray-800 text-sm text-gray-400 leading-relaxed">
              {a}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────
export function FeynmanMode({ docId }: Props) {
  const [concept,     setConcept]     = useState("");
  const [explanation, setExplanation] = useState("");
  const [loading,     setLoading]     = useState(false);
  const [result,      setResult]      = useState<FeynmanResponse | null>(null);

  const handleEvaluate = useCallback(async () => {
    if (!explanation.trim() || explanation.trim().length < 20) {
      toast.error("Write at least a sentence or two!");
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      const res = await evaluateFeynman({
        concept: concept.trim() || "this topic",
        explanation: explanation.trim(),
        doc_id: docId ?? null,
      });
      setResult(res);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        || "Evaluation failed. Please try again.";
      toast.error(msg);
    }
    setLoading(false);
  }, [concept, explanation, docId]);

  const handleReset = () => {
    setResult(null);
    setExplanation("");
  };

  const gm = result ? (GRADE_META[result.grade] ?? GRADE_META["D"]) : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div className="p-3 rounded-2xl bg-pink-500/10 text-pink-400 shrink-0">
          <Brain className="h-7 w-7" />
        </div>
        <div className="flex-1">
          <h2 className="section-heading">Feynman Mode</h2>
          <p className="text-sm text-gray-400 mt-1">
            Explain a concept in your own words — as if teaching someone else.
            The AI will grade your understanding, find gaps, and quiz you.
          </p>
        </div>
      </div>

      {/* Input panel */}
      {!result && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
          {/* Concept input */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-gray-400 uppercase tracking-widest">
              Concept (optional)
            </label>
            <input
              value={concept}
              onChange={(e) => setConcept(e.target.value)}
              placeholder="e.g. Photosynthesis, Newton's Second Law…"
              className="input-field w-full"
            />
            {/* Quick concept chips */}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {SAMPLE_CONCEPTS.map((c) => (
                <button
                  key={c}
                  onClick={() => setConcept(c)}
                  className="text-[11px] px-2.5 py-1 rounded-full bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-gray-200 border border-gray-700/50 transition-colors"
                >
                  {c}
                </button>
              ))}
            </div>
          </div>

          {/* Explanation textarea */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-gray-400 uppercase tracking-widest">
              Your Explanation
            </label>
            <textarea
              value={explanation}
              onChange={(e) => setExplanation(e.target.value)}
              placeholder={`Explain "${concept || "the concept"}" in your own words, as simply as possible, as if you're teaching a friend who has never heard of it…`}
              rows={8}
              className="input-field w-full resize-none leading-relaxed"
            />
            <p className="text-[11px] text-gray-600 text-right">
              {explanation.length} chars — aim for at least 100
            </p>
          </div>

          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleEvaluate}
            disabled={loading || explanation.trim().length < 10}
            className="btn-primary w-full justify-center py-3"
          >
            {loading ? <><Spinner size="sm" /> Evaluating…</> : <><Sparkles className="h-4 w-4" /> Evaluate My Understanding</>}
          </motion.button>

          {/* How it works */}
          <div className="p-4 rounded-xl bg-pink-500/5 border border-pink-500/15 text-xs text-gray-500 space-y-1">
            <p className="font-semibold text-pink-400 mb-1">💡 The Feynman Technique</p>
            <p>1. Choose a concept · 2. Explain it simply · 3. Find gaps · 4. Go back and study the gaps · 5. Repeat until perfect</p>
          </div>
        </motion.div>
      )}

      {/* Result panel */}
      <AnimatePresence>
        {result && gm && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-5"
          >
            {/* Grade banner */}
            <div className={clsx("glass-card p-6 border flex items-center gap-6", gm.bg)}>
              <ScoreRing score={result.score} grade={result.grade} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <span className={clsx("text-2xl font-black", gm.text)}>{result.grade}</span>
                  <Badge variant={
                    result.grade === "S" ? "yellow" :
                    result.grade === "A" ? "green" :
                    result.grade === "B" ? "blue" :
                    result.grade === "C" ? "yellow" : "red"
                  }>{gm.label}</Badge>
                </div>
                <p className="text-sm text-gray-400">
                  Concept: <span className="text-white font-medium">{concept || "General topic"}</span>
                </p>
                <ProgressBar value={result.score} className="mt-3 h-2" />
              </div>
            </div>

            {/* Strengths + Gaps side by side */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Strengths */}
              {result.strengths.length > 0 && (
                <div className="glass-card p-5 space-y-3">
                  <p className="text-xs font-semibold text-green-400 uppercase tracking-widest flex items-center gap-1.5">
                    <CheckCircle2 className="h-3.5 w-3.5" /> What You Got Right
                  </p>
                  <ul className="space-y-2">
                    {result.strengths.map((s, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                        <CheckCircle2 className="h-4 w-4 text-green-400 shrink-0 mt-0.5" />
                        {s}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Gaps */}
              {result.gaps.length > 0 && (
                <div className="glass-card p-5 space-y-3">
                  <p className="text-xs font-semibold text-red-400 uppercase tracking-widest flex items-center gap-1.5">
                    <XCircle className="h-3.5 w-3.5" /> Knowledge Gaps
                  </p>
                  <ul className="space-y-2">
                    {result.gaps.map((g, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                        <XCircle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
                        {g}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Coaching tip */}
            <div className="flex items-start gap-3 p-4 rounded-2xl bg-amber-500/8 border border-amber-500/20">
              <Lightbulb className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-semibold text-amber-400 mb-0.5">Coach&apos;s Tip</p>
                <p className="text-sm text-gray-300 leading-relaxed">{result.coaching_tip}</p>
              </div>
            </div>

            {/* Q&A pairs */}
            {result.qa_pairs.length > 0 && (
              <div className="space-y-3">
                <p className="text-xs font-semibold text-brand-400 uppercase tracking-widest flex items-center gap-1.5">
                  <BookOpen className="h-3.5 w-3.5" /> Questions From Your Explanation
                  <span className="text-gray-600 normal-case tracking-normal font-normal">— click to reveal answers</span>
                </p>
                {result.qa_pairs.map((pair, i) => (
                  <QAItem key={i} q={pair.question} a={pair.answer} index={i} />
                ))}
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3">
              <button onClick={handleReset} className="btn-secondary flex-1 justify-center">
                <RotateCcw className="h-4 w-4" /> Try Again
              </button>
              <button
                onClick={() => { setResult(null); setExplanation(""); setConcept(""); }}
                className="btn-primary flex-1 justify-center"
              >
                <Brain className="h-4 w-4" /> New Concept
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
