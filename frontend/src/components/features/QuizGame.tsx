"use client";
import {
  useState, useEffect, useCallback, useRef,
} from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Zap, Play, RotateCcw, ChevronRight, Trophy,
  HelpCircle, Star, Target, Clock, CheckCircle2,
  XCircle, Lightbulb, Flame, History, Trash2, Share2, Copy, CheckCheck,
} from "lucide-react";
import { generateQuiz, submitQuizResult, createShareLink } from "@/lib/api";
import type { QuizQuestion, QuizSubmitResponse } from "@/lib/api";
import { Spinner, ProgressBar, Badge } from "@/components/ui";
import { QuizTimer } from "@/components/ui/QuizTimer";
import { useSound } from "@/hooks/useSound";
import { useQuizHistory } from "@/hooks/useQuizHistory";
import { ReviewScreen } from "@/components/features/ReviewScreen";
import toast from "react-hot-toast";
import { clsx } from "clsx";

// ── Constants ─────────────────────────────────────────────────────────────────

const OPTION_LETTERS   = ["A", "B", "C", "D"] as const;
const OPTION_COLORS    = [
  "from-blue-600   to-blue-500   border-blue-400",
  "from-orange-600 to-orange-500 border-orange-400",
  "from-green-600  to-green-500  border-green-400",
  "from-red-600    to-red-500    border-red-400",
] as const;
const OPTION_COLORS_DIM = [
  "border-blue-800   bg-blue-900/20   text-blue-400",
  "border-orange-800 bg-orange-900/20 text-orange-400",
  "border-green-800  bg-green-900/20  text-green-400",
  "border-red-800    bg-red-900/20    text-red-400",
] as const;

const DIFF_BADGE: Record<string, "green" | "yellow" | "red"> = {
  easy: "green", medium: "yellow", hard: "red",
};

// Points: base + time bonus (max 300 for answering instantly)
function calcPoints(timeLeft: number, totalTime: number, correct: boolean): number {
  if (!correct) return 0;
  const timePct = timeLeft / totalTime;
  return Math.round(100 + 200 * timePct);
}

// Grade label + colour
const GRADE_META: Record<string, { label: string; bg: string; text: string }> = {
  S: { label: "Perfect!",      bg: "bg-yellow-500/15 border-yellow-500/30", text: "text-yellow-400" },
  A: { label: "Outstanding!",  bg: "bg-green-500/15  border-green-500/30",  text: "text-green-400"  },
  B: { label: "Well done!",    bg: "bg-blue-500/15   border-blue-500/30",   text: "text-blue-400"   },
  C: { label: "Keep going!",   bg: "bg-orange-500/15 border-orange-500/30", text: "text-orange-400" },
  D: { label: "Don't give up!",bg: "bg-red-500/15    border-red-500/30",    text: "text-red-400"    },
};

// ── Types ─────────────────────────────────────────────────────────────────────

interface Props { docId?: string }

type Phase = "config" | "countdown" | "playing" | "results";

// ── Share Quiz Button ─────────────────────────────────────────────────────────

function ShareQuizButton({
  questions,
  topic,
  results,
}: {
  questions: QuizQuestion[];
  topic: string;
  results: QuizSubmitResponse;
}) {
  const [sharing,  setSharing]  = useState(false);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [copied,   setCopied]   = useState(false);

  const handleShare = async () => {
    setSharing(true);
    try {
      const BASE = process.env.NEXT_PUBLIC_APP_URL || (typeof window !== "undefined" ? window.location.origin : "");
      const res = await createShareLink(
        "quiz",
        { questions, topic, score: results.score, total: results.total, grade: results.grade },
        `Quiz: ${topic || "General"} · ${results.score}/${results.total} (${results.grade})`,
      );
      const url = `${BASE}/share/${res.id}`;
      setShareUrl(url);
      await navigator.clipboard.writeText(url).catch(() => {});
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    } catch {
      import("react-hot-toast").then(({ default: toast }) => toast.error("Could not create share link"));
    }
    setSharing(false);
  };

  if (shareUrl) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-green-500/10 border border-green-500/25 text-green-400 text-xs flex-1 min-w-[130px]">
        <CheckCheck className="h-4 w-4 shrink-0" />
        <span className="truncate">{copied ? "Copied!" : shareUrl}</span>
        <button
          onClick={() => navigator.clipboard.writeText(shareUrl).then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000); })}
          className="ml-auto shrink-0"
          title="Copy link"
        >
          <Copy className="h-3.5 w-3.5" />
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={handleShare}
      disabled={sharing}
      className="btn-secondary flex-1 justify-center min-w-[130px]"
    >
      {sharing ? <><span className="h-4 w-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" /></> : <Share2 className="h-4 w-4" />}
      Share
    </button>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────

export function QuizGame({ docId }: Props) {
  const { play } = useSound();
  const { history, addEntry, clearHistory } = useQuizHistory();
  const [showHistory, setShowHistory] = useState(false);

  // ── Config state ──────────────────────────────────────────────────────────
  const [topic,    setTopic]    = useState("");
  const [numQ,     setNumQ]     = useState(5);
  const [diff,     setDiff]     = useState<"easy" | "medium" | "hard" | "mixed">("mixed");
  const [timerSec, setTimerSec] = useState<15 | 30>(30);

  // ── Game state ────────────────────────────────────────────────────────────
  const [phase,     setPhase]    = useState<Phase>("config");
  const [questions, setQuestions]= useState<QuizQuestion[]>([]);
  const [quizId,    setQuizId]   = useState("");
  const [quizTopic, setQuizTopic]= useState("");
  const [current,   setCurrent]  = useState(0);

  // answers: question_id → chosen option index (-1 = timed out)
  const [answers,   setAnswers]  = useState<Record<string, number>>({});
  const [selected,  setSelected] = useState<number | null>(null);
  const [revealed,  setRevealed] = useState(false);
  const [timeLeft,  setTimeLeft] = useState(30);

  // scoring
  const [points,   setPoints]   = useState(0);
  const [streak,   setStreak]   = useState(0);
  const [bestStreak, setBestStreak] = useState(0);

  // results
  const [results,     setResults]     = useState<QuizSubmitResponse | null>(null);
  const [totalTimeSec, setTotalTime]  = useState(0);
  const [reviewMode,  setReviewMode]  = useState(false);

  // loading
  const [loading, setLoading] = useState(false);
  // 3-2-1 countdown before first question
  const [cdCount, setCdCount] = useState(3);

  const timerRef  = useRef<ReturnType<typeof setInterval> | null>(null);
  const startRef  = useRef<number>(0);
  const revealedRef = useRef(false); // stable ref for use inside interval

  // ── Timer helpers ─────────────────────────────────────────────────────────
  const stopTimer = useCallback(() => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
  }, []);

  const startTimer = useCallback((seconds: number) => {
    stopTimer();
    revealedRef.current = false;
    setTimeLeft(seconds);
    timerRef.current = setInterval(() => {
      setTimeLeft((t) => {
        const next = t - 1;
        if (next <= 5 && next > 0) play("countdown");
        else if (next > 5)         play("tick");
        if (next <= 0) {
          stopTimer();
          if (!revealedRef.current) {
            revealedRef.current = true;
            setRevealed(true);
          }
          return 0;
        }
        return next;
      });
    }, 1000);
  }, [stopTimer, play]);

  useEffect(() => () => stopTimer(), [stopTimer]);

  // ── Generate quiz ─────────────────────────────────────────────────────────
  const handleStart = async () => {
    setLoading(true);
    try {
      const data = await generateQuiz({
        doc_id:        docId,
        topic:         topic.trim() || undefined,
        num_questions: numQ,
        difficulty:    diff,
        timer_seconds: timerSec,
      });
      setQuestions(data.questions);
      setQuizId(data.quiz_id);
      setQuizTopic(data.topic);
      setAnswers({});
      setCurrent(0);
      setSelected(null);
      setRevealed(false);
      setResults(null);
      setPoints(0);
      setStreak(0);
      setBestStreak(0);
      setReviewMode(false);
      // 3-2-1 countdown
      setCdCount(3);
      setPhase("countdown");
    } catch (e: unknown) {
      toast.error(
        (e as { response?: { data?: { detail?: string } } })
          ?.response?.data?.detail || "Failed to generate quiz",
      );
    }
    setLoading(false);
  };

  // Countdown → playing
  useEffect(() => {
    if (phase !== "countdown") return;
    if (cdCount <= 0) {
      startRef.current = Date.now();
      setPhase("playing");
      startTimer(timerSec);
      return;
    }
    play("tick");
    const t = setTimeout(() => setCdCount((c) => c - 1), 900);
    return () => clearTimeout(t);
  }, [phase, cdCount, timerSec, startTimer, play]);

  // ── Answer selection ──────────────────────────────────────────────────────
  const handleSelect = useCallback((optIdx: number) => {
    if (revealed || revealedRef.current) return;
    stopTimer();
    revealedRef.current = true;
    setSelected(optIdx);
    setRevealed(true);

    const q = questions[current];
    const correct = optIdx === q.correct_index;
    const gained  = calcPoints(timeLeft, timerSec, correct);

    setAnswers((prev) => ({ ...prev, [q.id]: optIdx }));
    setPoints((p)  => p  + gained);
    setStreak((s)  => {
      const next = correct ? s + 1 : 0;
      setBestStreak((b) => Math.max(b, next));
      return next;
    });

    if (correct) play("correct");
    else         play("wrong");
  }, [revealed, questions, current, timeLeft, timerSec, stopTimer, play]);

  // ── Advance question ──────────────────────────────────────────────────────
  const handleNext = useCallback(async () => {
    const q = questions[current];
    // If timed out with no answer, record -1
    if (!(q.id in answers)) {
      setAnswers((prev) => ({ ...prev, [q.id]: -1 }));
    }

    if (current < questions.length - 1) {
      setCurrent((c) => c + 1);
      setSelected(null);
      setRevealed(false);
      startTimer(timerSec);
    } else {
      // Last question — submit
      stopTimer();
      const spent = Math.round((Date.now() - startRef.current) / 1000);
      setTotalTime(spent);
      setLoading(true);
      try {
        const finalAnswers = { ...answers };
        if (!(q.id in finalAnswers)) finalAnswers[q.id] = -1;
        const res = await submitQuizResult({
          quiz_id:    quizId,
          answers:    finalAnswers,
          time_taken: spent,
        });
        setResults(res);
        // ── Save to history ───────────────────────────────────────────────
        addEntry({
          topic: quizTopic || topic || "General",
          score: res.score,
          total: res.total,
          percentage: res.percentage,
          grade: res.grade,
          timeTaken: spent,
          difficulty: diff,
        });
        setPhase("results");
        play("complete");
      } catch {
        toast.error("Failed to submit results");
      }
      setLoading(false);
    }
  }, [questions, current, answers, timerSec, quizId, stopTimer, startTimer, play]);

  const handleRestart = () => {
    setPhase("config");
    setQuestions([]);
    setResults(null);
    setReviewMode(false);
  };

  // ── Current question ref ──────────────────────────────────────────────────
  const q = questions[current];

  // ═══════════════════════════════════════════════════════════════════════════
  // CONFIG SCREEN
  // ═══════════════════════════════════════════════════════════════════════════
  if (phase === "config") {
    return (
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start gap-4">
          <div className="p-3 rounded-2xl bg-purple-500/10 text-purple-400">
            <Zap className="h-7 w-7" />
          </div>
          <div className="flex-1">
            <h2 className="section-heading">Kahoot-Style Quiz</h2>
            <p className="text-sm text-gray-400 mt-1">
              Test your knowledge with timed MCQs, live scoring, and instant explanations.
            </p>
          </div>
          {history.length > 0 && (
            <button
              onClick={() => setShowHistory((s) => !s)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border border-gray-700 bg-gray-900 text-gray-400 hover:text-gray-200 hover:border-gray-600 transition-all"
            >
              <History className="h-3.5 w-3.5" />
              History ({history.length})
            </button>
          )}
        </div>

        {/* History panel */}
        <AnimatePresence>
          {showHistory && history.length > 0 && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden"
            >
              <div className="glass-card p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest">Recent Quizzes</p>
                  <button
                    onClick={clearHistory}
                    className="flex items-center gap-1 text-xs text-gray-600 hover:text-red-400 transition-colors"
                  >
                    <Trash2 className="h-3 w-3" /> Clear
                  </button>
                </div>
                <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                  {history.map((h) => {
                    const gradeColor: Record<string, string> = {
                      S: "text-yellow-400", A: "text-green-400", B: "text-blue-400",
                      C: "text-orange-400", D: "text-red-400",
                    };
                    return (
                      <div
                        key={h.id}
                        className="flex items-center gap-3 p-2.5 rounded-xl bg-gray-800/60 border border-gray-700/50"
                      >
                        <span className={clsx("text-lg font-black w-6 text-center shrink-0", gradeColor[h.grade] ?? "text-gray-400")}>
                          {h.grade}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-gray-200 truncate">{h.topic}</p>
                          <p className="text-[10px] text-gray-500">
                            {h.score}/{h.total} · {h.percentage}% · {h.difficulty}
                          </p>
                        </div>
                        <p className="text-[10px] text-gray-600 shrink-0">
                          {new Date(h.date).toLocaleDateString()}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="glass-card p-6 space-y-6">
          {/* Topic */}
          <div>
            <label className="text-sm font-medium text-gray-300 mb-2 block">
              Topic <span className="text-gray-600 font-normal">(optional)</span>
            </label>
            <input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleStart()}
              placeholder={docId ? "Leave blank to quiz from your document…" : "e.g. Newton's Laws, Photosynthesis…"}
              className="input-field"
            />
          </div>

          {/* Num questions */}
          <div>
            <label className="text-sm font-medium text-gray-300 mb-3 block">
              Questions
            </label>
            <div className="grid grid-cols-4 gap-2">
              {([3, 5, 7, 10] as const).map((n) => (
                <button
                  key={n}
                  onClick={() => setNumQ(n)}
                  className={clsx(
                    "py-2.5 rounded-xl text-sm font-bold border-2 transition-all",
                    numQ === n
                      ? "bg-brand-600 border-brand-500 text-white shadow-lg shadow-brand-900/40"
                      : "bg-gray-900 border-gray-700 text-gray-400 hover:border-gray-600 hover:text-gray-200",
                  )}
                >{n}</button>
              ))}
            </div>
          </div>

          {/* Difficulty */}
          <div>
            <label className="text-sm font-medium text-gray-300 mb-3 block">Difficulty</label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {(["easy", "medium", "hard", "mixed"] as const).map((d) => {
                const icons = { easy: "🟢", medium: "🟡", hard: "🔴", mixed: "🎲" };
                return (
                  <button
                    key={d}
                    onClick={() => setDiff(d)}
                    className={clsx(
                      "py-2.5 rounded-xl text-sm font-semibold border-2 capitalize transition-all",
                      diff === d
                        ? "bg-brand-600 border-brand-500 text-white shadow-lg shadow-brand-900/40"
                        : "bg-gray-900 border-gray-700 text-gray-400 hover:border-gray-600 hover:text-gray-200",
                    )}
                  >{icons[d]} {d}</button>
                );
              })}
            </div>
          </div>

          {/* Timer */}
          <div>
            <label className="text-sm font-medium text-gray-300 mb-3 block">
              Time per question
            </label>
            <div className="grid grid-cols-2 gap-3">
              {([15, 30] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => setTimerSec(s)}
                  className={clsx(
                    "flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-bold border-2 transition-all",
                    timerSec === s
                      ? "bg-brand-600 border-brand-500 text-white shadow-lg shadow-brand-900/40"
                      : "bg-gray-900 border-gray-700 text-gray-400 hover:border-gray-600 hover:text-gray-200",
                  )}
                >
                  <Clock className="h-4 w-4" /> {s}s
                </button>
              ))}
            </div>
          </div>

          {/* Start button */}
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.97 }}
            onClick={handleStart}
            disabled={loading}
            className="btn-primary w-full justify-center py-3.5 text-base"
          >
            {loading ? <Spinner size="sm" /> : <Play className="h-5 w-5" />}
            {loading ? "Generating Quiz…" : "Start Quiz"}
          </motion.button>
        </div>
      </div>
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // 3-2-1 COUNTDOWN
  // ═══════════════════════════════════════════════════════════════════════════
  if (phase === "countdown") {
    return (
      <div className="flex flex-col items-center justify-center min-h-[420px] gap-6">
        <p className="text-gray-400 text-sm font-medium uppercase tracking-widest">Get ready…</p>
        <AnimatePresence mode="wait">
          <motion.div
            key={cdCount}
            initial={{ scale: 0.4, opacity: 0 }}
            animate={{ scale: 1,   opacity: 1 }}
            exit={{   scale: 1.6,  opacity: 0 }}
            transition={{ type: "spring", stiffness: 260, damping: 20 }}
            className="text-[120px] font-black text-brand-400 leading-none tabular-nums"
          >
            {cdCount === 0 ? "GO!" : cdCount}
          </motion.div>
        </AnimatePresence>
        <p className="text-gray-500 text-sm">{quizTopic} · {questions.length} questions · {timerSec}s each</p>
      </div>
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // RESULTS SCREEN
  // ═══════════════════════════════════════════════════════════════════════════
  if (phase === "results" && results) {
    if (reviewMode) {
      return (
        <ReviewScreen
          questions={questions}
          answers={answers}
          details={results.details}
          onBack={() => setReviewMode(false)}
          onRestart={handleRestart}
        />
      );
    }

    const gm = GRADE_META[results.grade] ?? GRADE_META["C"];
    const pct = results.percentage;
    const correctCount = results.score;

    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-5"
      >
        {/* Grade banner */}
        <div className={clsx("glass-card p-8 text-center border", gm.bg)}>
          <motion.div
            initial={{ scale: 0, rotate: -15 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ type: "spring", stiffness: 200, delay: 0.15 }}
            className={clsx("text-7xl font-black mb-2", gm.text)}
          >
            {results.grade}
          </motion.div>
          <p className={clsx("text-xl font-bold mb-1", gm.text)}>{gm.label}</p>
          <p className="text-gray-400 text-sm">
            {correctCount} / {results.total} correct · {pct}% · {totalTimeSec}s
          </p>
          <ProgressBar value={pct} className="max-w-xs mx-auto mt-4 h-2.5" />
        </div>

        {/* Score + streak stats */}
        <div className="grid grid-cols-3 gap-3">
          <div className="glass-card p-4 text-center">
            <Trophy className="h-5 w-5 text-yellow-400 mx-auto mb-1" />
            <p className="text-2xl font-black text-white">{points}</p>
            <p className="text-[11px] text-gray-500">Points</p>
          </div>
          <div className="glass-card p-4 text-center">
            <Flame className="h-5 w-5 text-orange-400 mx-auto mb-1" />
            <p className="text-2xl font-black text-white">{bestStreak}</p>
            <p className="text-[11px] text-gray-500">Best streak</p>
          </div>
          <div className="glass-card p-4 text-center">
            <Clock className="h-5 w-5 text-brand-400 mx-auto mb-1" />
            <p className="text-2xl font-black text-white">{totalTimeSec}s</p>
            <p className="text-[11px] text-gray-500">Time taken</p>
          </div>
        </div>

        {/* Weak topics */}
        {results.weak_topics?.length > 0 && (
          <div className="glass-card p-5">
            <p className="text-sm font-semibold text-orange-400 flex items-center gap-2 mb-3">
              <Target className="h-4 w-4" /> Topics to Revisit
            </p>
            <div className="flex flex-wrap gap-2">
              {results.weak_topics.map((t) => (
                <Badge key={t} variant="yellow">{t}</Badge>
              ))}
            </div>
          </div>
        )}

        {/* Strong topics */}
        {results.strong_topics?.length > 0 && (
          <div className="glass-card p-5">
            <p className="text-sm font-semibold text-green-400 flex items-center gap-2 mb-3">
              <Star className="h-4 w-4" /> Strong Topics
            </p>
            <div className="flex flex-wrap gap-2">
              {results.strong_topics.map((t) => (
                <Badge key={t} variant="green">{t}</Badge>
              ))}
            </div>
          </div>
        )}

        {/* Recommendations */}
        {results.recommendations?.length > 0 && (
          <div className="glass-card p-5 space-y-2">
            <p className="text-sm font-semibold text-brand-400 flex items-center gap-2 mb-1">
              <Lightbulb className="h-4 w-4" /> Study Recommendations
            </p>
            {results.recommendations.map((r, i) => (
              <div key={i} className="flex items-start gap-2 text-sm text-gray-300">
                <span className="text-brand-400 font-bold shrink-0 mt-0.5">{i + 1}.</span>
                {r}
              </div>
            ))}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3 flex-wrap">
          <button onClick={handleRestart} className="btn-secondary flex-1 justify-center min-w-[130px]">
            <RotateCcw className="h-4 w-4" /> New Quiz
          </button>
          <button onClick={() => setReviewMode(true)} className="btn-primary flex-1 justify-center min-w-[130px]">
            <HelpCircle className="h-4 w-4" /> Review Answers
          </button>
          <ShareQuizButton
            questions={questions}
            topic={quizTopic}
            results={results}
          />
        </div>
      </motion.div>
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // PLAYING SCREEN
  // ═══════════════════════════════════════════════════════════════════════════
  if (phase !== "playing" || !q) return null;

  const progress = ((current) / questions.length) * 100;

  return (
    <div className="space-y-4">
      {/* Top HUD */}
      <div className="flex items-center gap-3">
        <div className="flex-1 space-y-1">
          <ProgressBar value={progress} className="h-2" />
          <p className="text-xs text-gray-500">
            {current + 1} / {questions.length}
            {quizTopic ? ` · ${quizTopic}` : ""}
          </p>
        </div>
        {/* Live score */}
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gray-900 border border-gray-700 shrink-0">
          <Trophy className="h-3.5 w-3.5 text-yellow-400" />
          <span className="text-sm font-black text-yellow-400 tabular-nums">{points}</span>
        </div>
        {/* Streak */}
        {streak >= 2 && (
          <motion.div
            initial={{ scale: 0.8 }}
            animate={{ scale: 1 }}
            className="flex items-center gap-1 px-3 py-1.5 rounded-xl bg-orange-500/10 border border-orange-500/25 shrink-0"
          >
            <Flame className="h-3.5 w-3.5 text-orange-400" />
            <span className="text-sm font-black text-orange-400">{streak}×</span>
          </motion.div>
        )}
        {/* Circular timer */}
        <QuizTimer timeLeft={timeLeft} totalTime={timerSec} />
      </div>

      {/* Hint bar (appears with 5s left) */}
      <AnimatePresence>
        {timeLeft <= 5 && timeLeft > 0 && !revealed && q.hint && (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex items-start gap-2 px-4 py-2.5 rounded-xl bg-amber-500/8 border border-amber-500/20 text-sm text-amber-300"
          >
            <Lightbulb className="h-4 w-4 shrink-0 mt-0.5 text-amber-400" />
            <span><strong className="text-amber-400">Hint:</strong> {q.hint}</span>
          </motion.div>
        )}
      </AnimatePresence>

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
          {/* Question header */}
          <div className="flex items-start justify-between gap-3">
            <h3 className="text-base sm:text-lg font-bold text-white leading-snug flex-1">
              {q.question}
            </h3>
            <div className="flex flex-col items-end gap-1 shrink-0">
              <Badge variant={DIFF_BADGE[q.difficulty]}>{q.difficulty}</Badge>
              {q.topic_tag && (
                <span className="text-[10px] text-gray-500 font-medium">{q.topic_tag}</span>
              )}
            </div>
          </div>

          {/* Options — 2-column grid, each with distinct Kahoot-style colour */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {q.options.map((opt, oi) => {
              const isCorrect  = oi === q.correct_index;
              const isSelected = oi === selected;
              const isOther    = revealed && !isCorrect && !isSelected;

              return (
                <motion.button
                  key={`${q.id}-${oi}`}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: oi * 0.06 }}
                  whileHover={!revealed ? { scale: 1.025, y: -2 } : {}}
                  whileTap={!revealed ? { scale: 0.97 } : {}}
                  onClick={() => handleSelect(oi)}
                  disabled={revealed}
                  aria-label={`Option ${OPTION_LETTERS[oi]}: ${opt}`}
                  className={clsx(
                    "relative flex items-center gap-3 p-4 rounded-2xl border-2 text-left",
                    "font-semibold text-sm transition-all duration-200 select-none min-h-[64px]",
                    // Pre-reveal: vivid Kahoot colours
                    !revealed && `bg-gradient-to-br ${OPTION_COLORS[oi]} text-white shadow-lg`,
                    // Post-reveal states
                    revealed && isCorrect  && "bg-green-500/25 border-green-400 text-green-200 shadow-lg shadow-green-900/30",
                    revealed && isSelected && !isCorrect && "bg-red-500/20 border-red-400 text-red-300",
                    revealed && isOther    && `${OPTION_COLORS_DIM[oi]} opacity-50`,
                  )}
                >
                  {/* Letter badge */}
                  <span className={clsx(
                    "h-8 w-8 shrink-0 rounded-xl flex items-center justify-center",
                    "font-black text-sm border-2 transition-all",
                    !revealed && "bg-white/20 border-white/30 text-white",
                    revealed && isCorrect  && "bg-green-500  border-green-300  text-white",
                    revealed && isSelected && !isCorrect && "bg-red-500 border-red-300 text-white",
                    revealed && isOther    && "bg-gray-800 border-gray-600 text-gray-500",
                  )}>
                    {OPTION_LETTERS[oi]}
                  </span>
                  <span className="leading-snug">{opt}</span>

                  {/* Inline correct/wrong icon */}
                  {revealed && isCorrect && (
                    <CheckCircle2 className="h-5 w-5 text-green-300 ml-auto shrink-0" />
                  )}
                  {revealed && isSelected && !isCorrect && (
                    <XCircle className="h-5 w-5 text-red-300 ml-auto shrink-0" />
                  )}
                </motion.button>
              );
            })}
          </div>

          {/* Explanation (slides in after reveal) */}
          <AnimatePresence>
            {revealed && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                transition={{ duration: 0.25 }}
                className="overflow-hidden"
              >
                <div className="p-4 rounded-2xl bg-brand-500/8 border border-brand-500/20">
                  <p className="text-sm text-gray-300 leading-relaxed">
                    <span className="text-brand-400 font-semibold">💡 Explanation: </span>
                    {q.explanation}
                  </p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Next / Finish button */}
          {revealed && (
            <motion.button
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              onClick={handleNext}
              disabled={loading}
              className="btn-primary w-full justify-center py-3"
            >
              {loading
                ? <><Spinner size="sm" /> Submitting…</>
                : current < questions.length - 1
                  ? <><ChevronRight className="h-4 w-4" /> Next Question</>
                  : <><Trophy className="h-4 w-4" /> Finish &amp; See Results</>
              }
            </motion.button>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
