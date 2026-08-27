"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CheckCircle2, XCircle, MinusCircle, RotateCcw, ArrowLeft,
  ChevronDown, ChevronUp, Tag, AlertTriangle,
} from "lucide-react";
import type { QuizQuestion, QuizAnswerDetail } from "@/lib/api";
import { Badge } from "@/components/ui";
import { clsx } from "clsx";

interface Props {
  questions: QuizQuestion[];
  answers: Record<string, number>;     // question_id → chosen idx
  details: QuizAnswerDetail[];
  onBack: () => void;
  onRestart: () => void;
}

const OPTION_LETTERS = ["A", "B", "C", "D"] as const;
const DIFF_BADGE: Record<string, "green" | "yellow" | "red"> = {
  easy: "green", medium: "yellow", hard: "red",
};

// Group by topic_tag to surface weak-topic clusters
function groupByTopic(details: QuizAnswerDetail[]) {
  const map = new Map<string, QuizAnswerDetail[]>();
  for (const d of details) {
    const key = d.topic_tag || "General";
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(d);
  }
  return map;
}

// Visual score bar for a topic
function TopicBar({ correct, total }: { correct: number; total: number }) {
  const pct = total ? (correct / total) * 100 : 0;
  const color = pct >= 70 ? "bg-green-500" : pct >= 40 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-gray-800 overflow-hidden">
        <div className={clsx("h-full rounded-full transition-all", color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-500 tabular-nums w-10 text-right">{correct}/{total}</span>
    </div>
  );
}

// Single expandable question card
function QuestionCard({
  detail, question, index,
}: {
  detail: QuizAnswerDetail;
  question: QuizQuestion;
  index: number;
}) {
  const [open, setOpen] = useState(false);
  const timedOut = detail.user_index === -1;
  const correct  = detail.is_correct;

  const StatusIcon = correct
    ? <CheckCircle2 className="h-5 w-5 text-green-400 shrink-0" />
    : timedOut
    ? <MinusCircle  className="h-5 w-5 text-gray-500 shrink-0" />
    : <XCircle      className="h-5 w-5 text-red-400  shrink-0" />;

  const borderColor = correct
    ? "border-l-green-500"
    : timedOut
    ? "border-l-gray-600"
    : "border-l-red-500";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04 }}
      className={clsx("glass-card overflow-hidden border-l-4", borderColor)}
    >
      {/* Collapsed header */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-start gap-3 p-4 text-left hover:bg-gray-800/30 transition-colors"
      >
        {StatusIcon}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-200 leading-snug">
            <span className="text-gray-500 mr-1">{index + 1}.</span>
            {question.question}
          </p>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            {question.topic_tag && (
              <span className="flex items-center gap-1 text-[10px] text-gray-500">
                <Tag className="h-3 w-3" />{question.topic_tag}
              </span>
            )}
            <Badge variant={DIFF_BADGE[detail.difficulty]}>{detail.difficulty}</Badge>
            {timedOut && <Badge variant="gray">Timed out</Badge>}
          </div>
        </div>
        {open
          ? <ChevronUp   className="h-4 w-4 text-gray-500 shrink-0 mt-0.5" />
          : <ChevronDown className="h-4 w-4 text-gray-500 shrink-0 mt-0.5" />}
      </button>

      {/* Expanded body */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: "auto" }}
            exit={{ height: 0 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 space-y-3 border-t border-gray-800 pt-3">
              {/* Options */}
              <div className="space-y-1.5">
                {question.options.map((opt, oi) => {
                  const isCorrect  = oi === question.correct_index;
                  const isSelected = oi === detail.user_index;
                  return (
                    <div
                      key={oi}
                      className={clsx(
                        "flex items-center gap-2 px-3 py-2 rounded-xl text-sm transition-colors",
                        isCorrect  && "bg-green-500/15 border border-green-500/25 text-green-300",
                        isSelected && !isCorrect && "bg-red-500/10 border border-red-500/20 text-red-300",
                        !isCorrect && !isSelected && "text-gray-600",
                      )}
                    >
                      <span className={clsx(
                        "h-6 w-6 rounded-lg shrink-0 flex items-center justify-center text-xs font-black border",
                        isCorrect  && "bg-green-500 border-green-400 text-white",
                        isSelected && !isCorrect && "bg-red-500 border-red-400 text-white",
                        !isCorrect && !isSelected && "bg-gray-800 border-gray-700 text-gray-500",
                      )}>
                        {OPTION_LETTERS[oi]}
                      </span>
                      <span className={clsx(
                        isSelected && !isCorrect && "line-through opacity-70",
                      )}>
                        {opt}
                      </span>
                      {isCorrect && (
                        <CheckCircle2 className="h-3.5 w-3.5 text-green-400 ml-auto shrink-0" />
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Explanation */}
              <div className="p-3 rounded-xl bg-brand-500/8 border border-brand-500/20 text-sm text-gray-300">
                <span className="text-brand-400 font-semibold">💡 Explanation: </span>
                {detail.explanation}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

export function ReviewScreen({ questions, answers, details, onBack, onRestart }: Props) {
  const [filter, setFilter] = useState<"all" | "wrong" | "correct">("all");
  const topicMap = groupByTopic(details);

  const filtered = details.filter((d) => {
    if (filter === "wrong")   return !d.is_correct;
    if (filter === "correct") return d.is_correct;
    return true;
  });

  const wrongCount   = details.filter((d) => !d.is_correct).length;
  const correctCount = details.filter((d) =>  d.is_correct).length;
  const timedOut     = details.filter((d) => d.user_index === -1).length;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={onBack} className="btn-secondary py-2 px-3">
          <ArrowLeft className="h-4 w-4" />
        </button>
        <h2 className="section-heading flex-1">Answer Review</h2>
        <button onClick={onRestart} className="btn-secondary py-2 px-3 text-xs">
          <RotateCcw className="h-4 w-4" /> New Quiz
        </button>
      </div>

      {/* Summary row */}
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="glass-card p-3">
          <p className="text-xl font-black text-green-400">{correctCount}</p>
          <p className="text-[10px] text-gray-500">Correct</p>
        </div>
        <div className="glass-card p-3">
          <p className="text-xl font-black text-red-400">{wrongCount}</p>
          <p className="text-[10px] text-gray-500">Wrong</p>
        </div>
        <div className="glass-card p-3">
          <p className="text-xl font-black text-gray-500">{timedOut}</p>
          <p className="text-[10px] text-gray-500">Timed out</p>
        </div>
      </div>

      {/* Topic breakdown */}
      {topicMap.size > 1 && (
        <div className="glass-card p-5 space-y-3">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest">
            Performance by Topic
          </p>
          {Array.from(topicMap.entries()).map(([tag, tagDetails]) => {
            const correct = tagDetails.filter((d) => d.is_correct).length;
            const isWeak  = correct / tagDetails.length < 0.5;
            return (
              <div key={tag} className="space-y-1">
                <div className="flex items-center gap-2">
                  {isWeak && <AlertTriangle className="h-3 w-3 text-orange-400 shrink-0" />}
                  <span className="text-xs font-medium text-gray-300 flex-1 truncate">{tag}</span>
                </div>
                <TopicBar correct={correct} total={tagDetails.length} />
              </div>
            );
          })}
        </div>
      )}

      {/* Filter pills */}
      <div className="flex gap-2">
        {(["all", "correct", "wrong"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={clsx(
              "px-4 py-1.5 rounded-full text-xs font-semibold border capitalize transition-all",
              filter === f
                ? "bg-brand-600 border-brand-500 text-white"
                : "bg-gray-900 border-gray-700 text-gray-400 hover:border-gray-600",
            )}
          >{f} {f === "all" ? `(${details.length})` : f === "correct" ? `(${correctCount})` : `(${wrongCount})`}</button>
        ))}
      </div>

      {/* Question cards */}
      <div className="space-y-3">
        <AnimatePresence>
          {filtered.map((detail, idx) => {
            const question = questions.find((q) => q.id === detail.question_id);
            if (!question) return null;
            const globalIdx = details.findIndex((d) => d.question_id === detail.question_id);
            return (
              <QuestionCard
                key={detail.question_id}
                detail={detail}
                question={question}
                index={globalIdx}
              />
            );
          })}
        </AnimatePresence>
        {filtered.length === 0 && (
          <p className="text-center text-gray-500 text-sm py-8">
            {filter === "correct" ? "No correct answers to show." : "No wrong answers — perfect score! 🎉"}
          </p>
        )}
      </div>
    </div>
  );
}
