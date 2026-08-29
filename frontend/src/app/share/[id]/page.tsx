"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Trophy, CheckCircle2, XCircle, Lightbulb,
  RotateCcw, ArrowRight, Share2, ChevronRight,
} from "lucide-react";
import { resolveShareLink } from "@/lib/api";
import type { QuizQuestion } from "@/lib/api";
import { Spinner, ProgressBar, Badge } from "@/components/ui";
import { clsx } from "clsx";

const OPTION_LETTERS = ["A", "B", "C", "D"] as const;
const OPTION_COLORS_DIM = [
  "border-blue-800   bg-blue-900/20   text-blue-400",
  "border-orange-800 bg-orange-900/20 text-orange-400",
  "border-green-800  bg-green-900/20  text-green-400",
  "border-red-800    bg-red-900/20    text-red-400",
] as const;
const OPTION_COLORS = [
  "from-blue-600   to-blue-500   border-blue-400",
  "from-orange-600 to-orange-500 border-orange-400",
  "from-green-600  to-green-500  border-green-400",
  "from-red-600    to-red-500    border-red-400",
] as const;

const GRADE_META: Record<string, { label: string; bg: string; text: string }> = {
  S: { label: "Perfect!",      bg: "bg-yellow-500/15 border-yellow-500/30", text: "text-yellow-400" },
  A: { label: "Outstanding!",  bg: "bg-green-500/15  border-green-500/30",  text: "text-green-400"  },
  B: { label: "Well done!",    bg: "bg-blue-500/15   border-blue-500/30",   text: "text-blue-400"   },
  C: { label: "Keep going!",   bg: "bg-orange-500/15 border-orange-500/30", text: "text-orange-400" },
  D: { label: "Don't give up!",bg: "bg-red-500/15    border-red-500/30",    text: "text-red-400"    },
};

function gradeFor(pct: number): string {
  if (pct >= 100) return "S";
  if (pct >= 80)  return "A";
  if (pct >= 65)  return "B";
  if (pct >= 50)  return "C";
  return "D";
}

export default function SharePage() {
  const params = useParams<{ id: string }>();
  const shareId = params.id;

  const [status, setStatus]       = useState<"loading" | "ready" | "playing" | "results" | "error">("loading");
  const [errMsg, setErrMsg]       = useState("");
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [title, setTitle]         = useState("");

  // Play state
  const [current,   setCurrent]  = useState(0);
  const [answers,   setAnswers]  = useState<Record<string, number>>({});
  const [selected,  setSelected] = useState<number | null>(null);
  const [revealed,  setRevealed] = useState(false);

  useEffect(() => {
    if (!shareId) return;
    resolveShareLink(shareId)
      .then((res) => {
        const qs = (res.payload.questions ?? []) as QuizQuestion[];
        if (!qs.length) { setErrMsg("This quiz has no questions."); setStatus("error"); return; }
        setQuestions(qs);
        setTitle(res.title || "Shared Quiz");
        setStatus("ready");
      })
      .catch((e) => {
        const detail = e?.response?.data?.detail ?? e?.message ?? "Could not load quiz";
        setErrMsg(detail);
        setStatus("error");
      });
  }, [shareId]);

  const q = questions[current];

  const handleAnswer = (idx: number) => {
    if (revealed) return;
    setSelected(idx);
    setRevealed(true);
    setAnswers((prev) => ({ ...prev, [q.id]: idx }));
  };

  const handleNext = () => {
    if (current + 1 < questions.length) {
      setCurrent((c) => c + 1);
      setSelected(null);
      setRevealed(false);
    } else {
      setStatus("results");
    }
  };

  const handleRestart = () => {
    setCurrent(0);
    setAnswers({});
    setSelected(null);
    setRevealed(false);
    setStatus("playing");
  };

  // ── Loading ──────────────────────────────────────────────────────────────────
  if (status === "loading") {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  // ── Error ────────────────────────────────────────────────────────────────────
  if (status === "error") {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center p-6">
        <div className="glass-card p-10 text-center max-w-md">
          <XCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">Quiz Not Found</h2>
          <p className="text-gray-400 text-sm">{errMsg}</p>
        </div>
      </div>
    );
  }

  // ── Ready screen ─────────────────────────────────────────────────────────────
  if (status === "ready") {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center p-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-10 text-center max-w-md w-full space-y-6"
        >
          <div className="h-16 w-16 rounded-2xl bg-brand-600/20 text-brand-400 flex items-center justify-center mx-auto">
            <Share2 className="h-8 w-8" />
          </div>
          <div>
            <p className="text-xs text-brand-400 font-semibold uppercase tracking-widest mb-2">Shared Quiz</p>
            <h1 className="text-2xl font-black text-white">{title}</h1>
            <p className="text-gray-400 text-sm mt-2">{questions.length} questions · take the quiz and see how you score!</p>
          </div>
          <motion.button
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.96 }}
            onClick={() => setStatus("playing")}
            className="btn-primary w-full justify-center text-base py-3"
          >
            <ArrowRight className="h-5 w-5" /> Start Quiz
          </motion.button>
        </motion.div>
      </div>
    );
  }

  // ── Results ───────────────────────────────────────────────────────────────────
  if (status === "results") {
    const correct = questions.filter((q) => answers[q.id] === q.correct_index).length;
    const pct     = Math.round((correct / questions.length) * 100);
    const grade   = gradeFor(pct);
    const gm      = GRADE_META[grade];
    return (
      <div className="min-h-screen bg-gray-950 p-6 flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-xl w-full space-y-5"
        >
          <div className={clsx("glass-card p-8 text-center border", gm.bg)}>
            <div className={clsx("text-7xl font-black mb-2", gm.text)}>{grade}</div>
            <p className={clsx("text-xl font-bold mb-1", gm.text)}>{gm.label}</p>
            <p className="text-gray-400 text-sm">{correct} / {questions.length} correct · {pct}%</p>
            <ProgressBar value={pct} className="max-w-xs mx-auto mt-4 h-2.5" />
          </div>

          <div className="space-y-3">
            {questions.map((q, i) => {
              const userIdx = answers[q.id] ?? -1;
              const ok = userIdx === q.correct_index;
              return (
                <div key={q.id} className={clsx("glass-card p-4 border", ok ? "border-green-700/40" : "border-red-700/40")}>
                  <p className="text-sm font-semibold text-white mb-2">{i + 1}. {q.question}</p>
                  <p className={clsx("text-xs font-medium", ok ? "text-green-400" : "text-red-400")}>
                    {ok ? "✓ Correct" : `✗ Your answer: ${userIdx >= 0 ? q.options[userIdx] : "No answer"}`}
                  </p>
                  {!ok && <p className="text-xs text-green-400 mt-0.5">Correct: {q.options[q.correct_index]}</p>}
                  {q.explanation && <p className="text-xs text-gray-500 mt-1 italic">{q.explanation}</p>}
                </div>
              );
            })}
          </div>

          <button onClick={handleRestart} className="btn-secondary w-full justify-center">
            <RotateCcw className="h-4 w-4" /> Try Again
          </button>
        </motion.div>
      </div>
    );
  }

  // ── Playing ───────────────────────────────────────────────────────────────────
  const progress = ((current) / questions.length) * 100;

  return (
    <div className="min-h-screen bg-gray-950 p-6 flex items-center justify-center">
      <div className="max-w-xl w-full space-y-4">
        {/* HUD */}
        <div className="flex items-center gap-3">
          <div className="flex-1 space-y-1">
            <ProgressBar value={progress} className="h-2" />
            <p className="text-xs text-gray-500">{current + 1} / {questions.length}</p>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gray-900 border border-gray-700">
            <Trophy className="h-3.5 w-3.5 text-yellow-400" />
            <span className="text-sm font-black text-yellow-400">
              {questions.filter((q) => answers[q.id] === q.correct_index).length}
            </span>
          </div>
        </div>

        {/* Shared quiz badge */}
        <div className="flex items-center gap-1.5 text-xs text-brand-400">
          <Share2 className="h-3.5 w-3.5" />
          <span>{title}</span>
        </div>

        {/* Question card */}
        <AnimatePresence mode="wait">
          <motion.div
            key={q.id}
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -50 }}
            transition={{ duration: 0.22 }}
            className="glass-card p-6 space-y-5"
          >
            <div className="flex items-start justify-between gap-3">
              <h3 className="text-base font-bold text-white leading-snug flex-1">{q.question}</h3>
              <Badge variant={q.difficulty === "easy" ? "green" : q.difficulty === "medium" ? "yellow" : "red"}>
                {q.difficulty}
              </Badge>
            </div>

            <div className="grid grid-cols-1 gap-2.5">
              {q.options.map((opt, i) => {
                const isCorrect = i === q.correct_index;
                const isChosen  = i === selected;
                let cls = "";
                if (!revealed) {
                  cls = clsx(
                    "w-full text-left flex items-center gap-3 p-3.5 rounded-xl border-2 font-medium transition-all cursor-pointer",
                    OPTION_COLORS_DIM[i],
                    "hover:brightness-125 hover:scale-[1.01]",
                  );
                } else if (isCorrect) {
                  cls = "w-full text-left flex items-center gap-3 p-3.5 rounded-xl border-2 font-medium bg-gradient-to-r text-white " + OPTION_COLORS[i];
                } else if (isChosen) {
                  cls = "w-full text-left flex items-center gap-3 p-3.5 rounded-xl border-2 font-medium bg-red-900/40 border-red-500 text-red-300";
                } else {
                  cls = "w-full text-left flex items-center gap-3 p-3.5 rounded-xl border-2 font-medium opacity-40 " + OPTION_COLORS_DIM[i];
                }
                return (
                  <button key={i} onClick={() => handleAnswer(i)} disabled={revealed} className={cls}>
                    <span className="shrink-0 w-7 h-7 rounded-lg bg-black/20 flex items-center justify-center text-xs font-black">
                      {OPTION_LETTERS[i]}
                    </span>
                    <span className="text-sm">{opt}</span>
                    {revealed && isCorrect && <CheckCircle2 className="h-4 w-4 text-white ml-auto shrink-0" />}
                    {revealed && isChosen && !isCorrect && <XCircle className="h-4 w-4 text-red-300 ml-auto shrink-0" />}
                  </button>
                );
              })}
            </div>

            {revealed && q.explanation && (
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-start gap-2 p-3 rounded-xl bg-brand-500/8 border border-brand-500/20 text-sm text-gray-300"
              >
                <Lightbulb className="h-4 w-4 text-brand-400 shrink-0 mt-0.5" />
                <span>{q.explanation}</span>
              </motion.div>
            )}
          </motion.div>
        </AnimatePresence>

        {revealed && (
          <motion.button
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            onClick={handleNext}
            className="btn-primary w-full justify-center"
          >
            {current + 1 < questions.length ? <><ChevronRight className="h-4 w-4" /> Next Question</> : <><Trophy className="h-4 w-4" /> See Results</>}
          </motion.button>
        )}
      </div>
    </div>
  );
}
