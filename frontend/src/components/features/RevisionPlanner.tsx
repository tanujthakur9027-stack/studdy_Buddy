"use client";
import { useState, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CalendarDays, Clock, Target, BookOpen, Sparkles,
  ChevronDown, ChevronUp, RotateCcw, CheckCircle2,
  Brain, Zap, Coffee, Shield, Lightbulb, AlarmClock,
  FileText, Trophy,
} from "lucide-react";
import { generateRevisionPlan } from "@/lib/api";
import type { RevisionTask, PlanStats } from "@/lib/api";
import { Spinner, Badge, ProgressBar } from "@/components/ui";
import { useRevisionPlan, makeTaskKey } from "@/hooks/useRevisionPlan";
import toast from "react-hot-toast";
import { clsx } from "clsx";

// ── Constants ─────────────────────────────────────────────────────────────────

interface Props { docId?: string }

const SESSION_META = {
  concept: {
    label: "Core Concept",
    icon: Brain,
    bg:   "bg-brand-500/10  border-brand-500/20",
    text: "text-brand-400",
    dot:  "bg-brand-500",
    /** Static Tailwind class — must be literal so Tailwind's purge keeps it */
    borderLeft: "border-l-blue-500",
    badge: "blue" as const,
  },
  quiz: {
    label: "Practice Quiz",
    icon: Zap,
    bg:   "bg-purple-500/10 border-purple-500/20",
    text: "text-purple-400",
    dot:  "bg-purple-500",
    borderLeft: "border-l-purple-500",
    badge: "purple" as const,
  },
  buffer: {
    label: "Buffer / Catch-up",
    icon: Shield,
    bg:   "bg-amber-500/10  border-amber-500/20",
    text: "text-amber-400",
    dot:  "bg-amber-500",
    borderLeft: "border-l-amber-500",
    badge: "yellow" as const,
  },
  rest: {
    label: "Rest Day",
    icon: Coffee,
    bg:   "bg-gray-700/30   border-gray-700/50",
    text: "text-gray-400",
    dot:  "bg-gray-600",
    borderLeft: "border-l-gray-600",
    badge: "gray" as const,
  },
} as const;

const PRIORITY_DOT: Record<string, string> = {
  high:   "bg-red-400",
  medium: "bg-yellow-400",
  low:    "bg-green-400",
};

const TECHNIQUE_EMOJIS: Record<string, string> = {
  "Pomodoro":           "🍅",
  "Active Recall":      "🧠",
  "Spaced Repetition":  "🔁",
  "Mind Map":           "🗺️",
  "Feynman Technique":  "📝",
  "Practice Problems":  "✏️",
  "Flashcards":         "📇",
  "Reading":            "📖",
  "Mock Test":          "📋",
  "Past Papers":        "📄",
};

function getTechniqueEmoji(t: string) {
  for (const [k, v] of Object.entries(TECHNIQUE_EMOJIS)) {
    if (t.toLowerCase().includes(k.toLowerCase())) return v;
  }
  return "📌";
}

// ── Sub-components ────────────────────────────────────────────────────────────

function StatsGrid({ stats, topicCount }: { stats: PlanStats; topicCount: number }) {
  const items = [
    { icon: CalendarDays, color: "text-brand-400",   value: stats.total_days,      label: "Total days"   },
    { icon: BookOpen,     color: "text-emerald-400",  value: stats.study_days,      label: "Study days"   },
    { icon: Zap,          color: "text-purple-400",   value: stats.quiz_days,       label: "Quiz days"    },
    { icon: Shield,       color: "text-amber-400",    value: stats.buffer_days,     label: "Buffer days"  },
    { icon: Coffee,       color: "text-gray-400",     value: stats.rest_days,       label: "Rest days"    },
    { icon: Clock,        color: "text-cyan-400",     value: `${Math.round(stats.total_study_mins / 60)}h`, label: "Total study" },
    { icon: Target,       color: "text-pink-400",     value: topicCount,            label: "Topics"       },
    { icon: CalendarDays, color: "text-orange-400",   value: `${stats.days_to_exam}d`, label: "To exam"   },
  ];
  return (
    <div className="grid grid-cols-4 gap-2 sm:grid-cols-8">
      {items.map(({ icon: Icon, color, value, label }) => (
        <div key={label} className="glass-card p-3 text-center space-y-1">
          <Icon className={clsx("h-4 w-4 mx-auto", color)} />
          <p className="text-base font-black text-white leading-none">{value}</p>
          <p className="text-[9px] text-gray-500 leading-none">{label}</p>
        </div>
      ))}
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────

export function RevisionPlanner({ docId }: Props) {
  // ── form state ────────────────────────────────────────────────────────────
  const [syllabusText, setSyllabusText] = useState("");
  const [topics,       setTopics]       = useState("");
  const [weakTopics,   setWeakTopics]   = useState("");
  const [examDate,     setExamDate]     = useState("");
  const [dailyHours,   setDailyHours]   = useState(2);

  // ── plan state ────────────────────────────────────────────────────────────
  const [plan,       setPlan]       = useState<RevisionTask[]>([]);
  const [stats,      setStats]      = useState<PlanStats | null>(null);
  const [topicList,  setTopicList]  = useState<string[]>([]);
  const [summary,    setSummary]    = useState("");
  const [tips,       setTips]       = useState<string[]>([]);
  const [loading,    setLoading]    = useState(false);

  // ── calendar UI state ─────────────────────────────────────────────────────
  const [expandedDays, setExpandedDays] = useState<Set<string>>(new Set());
  const [filterType,   setFilterType]   = useState<"all" | "concept" | "quiz" | "buffer" | "rest">("all");

  // ── completion tracking ───────────────────────────────────────────────────
  const { completed, toggleTask, isComplete, overallProgress, resetPlan } =
    useRevisionPlan(plan);

  // ── derived ───────────────────────────────────────────────────────────────
  const grouped = useMemo(() => {
    const g: Record<string, RevisionTask[]> = {};
    plan.forEach((t) => {
      if (!g[t.date]) g[t.date] = [];
      g[t.date].push(t);
    });
    return g;
  }, [plan]);

  const dates = useMemo(
    () => Object.keys(grouped).sort(),
    [grouped],
  );

  const filteredDates = useMemo(() => {
    if (filterType === "all") return dates;
    return dates.filter((d) =>
      grouped[d].some((t) => t.session_type === filterType),
    );
  }, [dates, grouped, filterType]);

  // ── generate ──────────────────────────────────────────────────────────────
  const handleGenerate = async () => {
    if (!examDate) { toast.error("Set your exam date"); return; }
    if (!syllabusText.trim() && !topics.trim() && !docId) {
      toast.error("Enter topics, paste a syllabus, or upload a document"); return;
    }
    setLoading(true);
    setPlan([]);
    setStats(null);
    try {
      // Renamed from topicList to avoid shadowing the topicList state variable
      const topicsArr = topics.split(",").map((t) => t.trim()).filter(Boolean);
      const weakList  = weakTopics.split(",").map((t) => t.trim()).filter(Boolean);
      const data = await generateRevisionPlan({
        exam_date:     examDate,
        daily_hours:   dailyHours,
        syllabus_text: syllabusText.trim() || undefined,
        topics:        topicsArr.length ? topicsArr : undefined,
        weak_topics:   weakList.length  ? weakList  : undefined,
        doc_id:        docId,
      });
      setPlan(data.plan);
      setStats(data.stats);
      setTopicList(data.topic_list);
      setSummary(data.summary);
      setTips(data.tips);
      // Auto-expand today or the first day
      const todayStr = new Date().toISOString().split("T")[0];
      const firstDay = data.plan[0]?.date ?? "";
      const autoOpen = data.plan.some((t) => t.date === todayStr) ? todayStr : firstDay;
      setExpandedDays(new Set(autoOpen ? [autoOpen] : []));
      resetPlan();
      toast.success(`Plan ready — ${data.stats.total_days} days, ${data.stats.topics_covered} topics`);
    } catch (e: unknown) {
      toast.error(
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Failed to generate plan",
      );
    }
    setLoading(false);
  };

  const toggleDay = useCallback((d: string) => {
    setExpandedDays((prev) => {
      const next = new Set(prev);
      next.has(d) ? next.delete(d) : next.add(d);
      return next;
    });
  }, []);

  const expandAll  = () => setExpandedDays(new Set(filteredDates));
  const collapseAll= () => setExpandedDays(new Set());

  // ── render ────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">

      {/* ── Header ── */}
      <div className="flex items-start gap-4">
        <div className="p-3 rounded-2xl bg-emerald-500/10 text-emerald-400">
          <CalendarDays className="h-7 w-7" />
        </div>
        <div>
          <h2 className="section-heading">Smart Revision Planner</h2>
          <p className="text-sm text-gray-400 mt-1">
            Paste your syllabus or enter topics — get a personalised day-by-day roadmap
            with concept sessions, practice quizzes, buffer &amp; rest days.
          </p>
        </div>
      </div>

      {/* ── Form ── */}
      <div className="glass-card p-6 space-y-5">

        {/* Syllabus textarea */}
        <div>
          <label className="text-sm font-medium text-gray-300 mb-2 flex items-center gap-2">
            <FileText className="h-3.5 w-3.5 text-gray-500" />
            Syllabus / Notes
            <span className="text-gray-600 font-normal text-xs">(paste raw text — topics extracted automatically)</span>
          </label>
          <textarea
            value={syllabusText}
            onChange={(e) => setSyllabusText(e.target.value)}
            placeholder={"Unit 1: Newton's Laws of Motion\nUnit 2: Thermodynamics…\n\nPaste your full syllabus here"}
            rows={4}
            className="input-field resize-none font-mono text-xs leading-relaxed"
          />
        </div>

        {/* OR divider */}
        <div className="flex items-center gap-3">
          <div className="flex-1 h-px bg-gray-800" />
          <span className="text-xs text-gray-600 font-semibold uppercase tracking-widest">or enter topics manually</span>
          <div className="flex-1 h-px bg-gray-800" />
        </div>

        {/* Topics + Weak topics */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-gray-300 mb-2 block">Topics to Cover</label>
            <input
              value={topics}
              onChange={(e) => setTopics(e.target.value)}
              placeholder="Calculus, Thermodynamics, Optics…"
              className="input-field"
            />
            <p className="text-xs text-gray-600 mt-1">Comma-separated</p>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-300 mb-2 block">Weak Topics</label>
            <input
              value={weakTopics}
              onChange={(e) => setWeakTopics(e.target.value)}
              placeholder="Topics you struggle with…"
              className="input-field"
            />
            <p className="text-xs text-gray-600 mt-1">Comma-separated · scheduled first &amp; more often</p>
          </div>
        </div>

        {/* Exam date + daily hours */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-gray-300 mb-2 block">Exam Date *</label>
            <input
              type="date"
              value={examDate}
              onChange={(e) => setExamDate(e.target.value)}
              min={new Date().toISOString().split("T")[0]}
              className="input-field"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-300 mb-2 flex items-center gap-2">
              Daily Study Hours
              <span className="text-brand-400 font-black">{dailyHours}h</span>
            </label>
            <input
              type="range" min={0.5} max={8} step={0.5}
              value={dailyHours}
              onChange={(e) => setDailyHours(parseFloat(e.target.value))}
              className="w-full accent-brand-500"
            />
            <div className="flex justify-between text-xs text-gray-600 mt-1">
              <span>0.5h</span><span>4h</span><span>8h</span>
            </div>
          </div>
        </div>

        {/* Generate button */}
        <motion.button
          whileHover={{ scale: 1.015 }}
          whileTap={{ scale: 0.98 }}
          onClick={handleGenerate}
          disabled={loading}
          className="btn-primary w-full justify-center py-3.5 text-base"
        >
          {loading ? <Spinner size="sm" /> : <Sparkles className="h-5 w-5" />}
          {loading ? "Building your plan…" : "Generate Revision Plan"}
        </motion.button>
      </div>

      {/* ── Plan output ── */}
      <AnimatePresence>
        {plan.length > 0 && !loading && (
          <motion.div
            key="plan"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-5"
          >

            {/* Overall progress bar */}
            <div className="glass-card p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Trophy className="h-4 w-4 text-yellow-400" />
                  <span className="text-sm font-semibold text-gray-200">Overall Progress</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm font-black text-yellow-400">{overallProgress}%</span>
                  <button
                    onClick={resetPlan}
                    title="Reset all completions"
                    className="text-gray-600 hover:text-gray-400 transition-colors"
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
              <ProgressBar
                value={overallProgress}
                className="h-3"
                color={overallProgress === 100 ? "bg-green-500" : "bg-brand-500"}
              />
              <p className="text-xs text-gray-500">
                {completed.size} / {plan.length} sessions completed
              </p>
            </div>

            {/* Stats grid */}
            {stats && <StatsGrid stats={stats} topicCount={topicList.length} />}

            {/* Summary */}
            {summary && (
              <div className="p-4 rounded-2xl bg-emerald-500/8 border border-emerald-500/20 text-sm text-gray-300">
                <span className="text-emerald-400 font-semibold">📋 Plan Strategy: </span>
                {summary}
              </div>
            )}

            {/* Topics covered */}
            {topicList.length > 0 && (
              <div className="glass-card p-4">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">
                  Topics Covered
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {topicList.map((t) => (
                    <span key={t} className="text-xs px-2.5 py-1 rounded-full bg-gray-800 border border-gray-700 text-gray-300">
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* ── Calendar controls ── */}
            <div className="flex items-center gap-3 flex-wrap">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest flex-1">
                Daily Schedule ({filteredDates.length} days)
              </p>
              {/* Session type filter */}
              <div className="flex gap-1.5 flex-wrap">
                {(["all", "concept", "quiz", "buffer", "rest"] as const).map((f) => {
                  const meta = f === "all" ? null : SESSION_META[f];
                  return (
                    <button
                      key={f}
                      onClick={() => setFilterType(f)}
                      className={clsx(
                        "px-3 py-1 rounded-full text-xs font-semibold border capitalize transition-all",
                        filterType === f
                          ? "bg-brand-600 border-brand-500 text-white"
                          : "bg-gray-900 border-gray-700 text-gray-400 hover:border-gray-600",
                      )}
                    >
                      {f === "all" ? "All" : meta?.label}
                    </button>
                  );
                })}
              </div>
              {/* Expand / Collapse all */}
              <div className="flex gap-2">
                <button onClick={expandAll}   className="text-xs text-gray-500 hover:text-gray-300 transition-colors">Expand all</button>
                <span className="text-gray-700">·</span>
                <button onClick={collapseAll} className="text-xs text-gray-500 hover:text-gray-300 transition-colors">Collapse all</button>
              </div>
            </div>

            {/* ── Day cards ── */}
            <div className="space-y-2">
              {filteredDates.map((dateStr, di) => {
                const dayTasks = grouped[dateStr];
                if (!dayTasks) return null;

                const isOpen  = expandedDays.has(dateStr);
                const todayStr = new Date().toISOString().split("T")[0];
                const isToday  = dateStr === todayStr;
                const isPast   = dateStr < todayStr;
                const dayMins  = dayTasks.reduce((s, t) => s + t.duration_mins, 0);

                // Determine dominant session type for visual accent
                const typeCount: Record<string, number> = {};
                dayTasks.forEach((t) => { typeCount[t.session_type] = (typeCount[t.session_type] ?? 0) + 1; });
                const dominant = (Object.entries(typeCount).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "concept") as keyof typeof SESSION_META;
                const dm = SESSION_META[dominant];

                // Per-day progress
                const globalIndexOf = (t: RevisionTask) =>
                  plan.findIndex((x) => x.date === t.date && x.topic === t.topic);
                const dayDone = dayTasks.filter((t) => isComplete(makeTaskKey(t, globalIndexOf(t)))).length;
                const dayPct  = Math.round((dayDone / dayTasks.length) * 100);
                const dayFull = dayDone === dayTasks.length;

                // First task's day_label (human-readable)
                const displayLabel = dayTasks[0]?.day_label ||
                  new Date(dateStr + "T00:00:00").toLocaleDateString("en-US", {
                    weekday: "short", month: "short", day: "numeric",
                  });

                return (
                  <motion.div
                    key={dateStr}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: Math.min(di * 0.025, 0.4) }}
                    className={clsx(
                      "glass-card overflow-hidden border-l-4 transition-all",
                      dayFull    ? "border-l-green-500"
                      : isToday  ? "border-l-blue-500"
                      : isPast   ? "border-l-gray-700"
                      : dm.borderLeft,
                    )}
                  >
                    {/* Day header */}
                    <button
                      onClick={() => toggleDay(dateStr)}
                      className="w-full flex items-center gap-3 px-4 py-3.5 hover:bg-gray-800/30 transition-colors text-left"
                    >
                      {/* Date badge */}
                      <div className={clsx(
                        "h-10 w-10 rounded-xl shrink-0 flex flex-col items-center justify-center text-center",
                        dayFull   ? "bg-green-500  text-white"
                        : isToday ? "bg-brand-600  text-white"
                        : isPast  ? "bg-gray-800   text-gray-500"
                        : "bg-gray-800 text-gray-300",
                      )}>
                        <span className="text-[10px] font-medium leading-none uppercase">
                          {new Date(dateStr + "T00:00:00").toLocaleDateString("en-US", { month: "short" })}
                        </span>
                        <span className="text-base font-black leading-tight">
                          {new Date(dateStr + "T00:00:00").getDate()}
                        </span>
                      </div>

                      {/* Label + meta */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="text-sm font-semibold text-gray-200 truncate">
                            {displayLabel}
                            {isToday && <span className="ml-1.5 text-xs text-brand-400">(Today)</span>}
                          </p>
                          {dayFull && (
                            <span className="text-xs text-green-400 font-semibold flex items-center gap-0.5">
                              <CheckCircle2 className="h-3 w-3" /> Done
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 mt-0.5">
                          <span className="text-xs text-gray-500">
                            {dayTasks.length} session{dayTasks.length !== 1 ? "s" : ""}
                            {dominant !== "rest" ? ` · ${dayMins}min` : ""}
                          </span>
                          {/* Session type pills */}
                          <div className="flex gap-1">
                            {(Object.keys(typeCount) as (keyof typeof SESSION_META)[]).map((st) => {
                              const sm = SESSION_META[st];
                              const Ic = sm.icon;
                              return (
                                <span key={st} className={clsx("flex items-center gap-0.5 px-1.5 py-0.5 rounded-md text-[10px] font-semibold border", sm.bg, sm.text)}>
                                  <Ic className="h-2.5 w-2.5" />
                                  {typeCount[st] > 1 ? typeCount[st] : ""}
                                </span>
                              );
                            })}
                          </div>
                        </div>
                      </div>

                      {/* Day progress bar */}
                      <div className="hidden sm:flex flex-col items-end gap-1 shrink-0 w-24">
                        <span className="text-[10px] text-gray-500">{dayPct}%</span>
                        <ProgressBar
                          value={dayPct}
                          className="h-1.5 w-24"
                          color={dayFull ? "bg-green-500" : "bg-brand-500"}
                        />
                      </div>

                      {isOpen
                        ? <ChevronUp   className="h-4 w-4 text-gray-500 shrink-0" />
                        : <ChevronDown className="h-4 w-4 text-gray-500 shrink-0" />}
                    </button>

                    {/* ── Session list ── */}
                    <AnimatePresence>
                      {isOpen && (
                        <motion.div
                          initial={{ height: 0 }}
                          animate={{ height: "auto" }}
                          exit={{ height: 0 }}
                          className="overflow-hidden"
                        >
                          <div className="border-t border-gray-800 divide-y divide-gray-800/50">
                            {dayTasks.map((task, ti) => {
                              const globalIdx = plan.findIndex(
                                (x) => x.date === task.date && x.topic === task.topic,
                              );
                              const taskKey = makeTaskKey(task, globalIdx);
                              const done    = isComplete(taskKey);
                              const sm      = SESSION_META[task.session_type];
                              const emoji   = getTechniqueEmoji(task.technique);

                              return (
                                <TaskRow
                                  key={taskKey}
                                  task={task}
                                  done={done}
                                  onToggle={() => toggleTask(taskKey)}
                                  sm={sm}
                                  emoji={emoji}
                                  index={ti}
                                />
                              );
                            })}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                );
              })}
            </div>

            {/* ── Study tips ── */}
            {tips.length > 0 && (
              <div className="glass-card p-5 space-y-3">
                <p className="text-sm font-semibold text-yellow-400 flex items-center gap-2">
                  <Lightbulb className="h-4 w-4" /> Study Tips
                </p>
                <ul className="space-y-2.5">
                  {tips.map((tip, i) => (
                    <li key={i} className="flex items-start gap-2.5 text-sm text-gray-300">
                      <span className="h-5 w-5 rounded-full bg-yellow-500/15 text-yellow-400 text-xs flex items-center justify-center font-bold shrink-0 mt-0.5">
                        {i + 1}
                      </span>
                      {tip}
                    </li>
                  ))}
                </ul>
              </div>
            )}

          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── TaskRow sub-component ─────────────────────────────────────────────────────

interface TaskRowProps {
  task: RevisionTask;
  done: boolean;
  onToggle: () => void;
  sm: typeof SESSION_META[keyof typeof SESSION_META];
  emoji: string;
  index: number;
}

function TaskRow({ task, done, onToggle, sm, emoji, index }: TaskRowProps) {
  const [open, setOpen] = useState(false);
  const TIcon = sm.icon;
  const hasDetails = task.subtopics.length > 0 || task.notes || task.resources.length > 0;

  return (
    <motion.div
      initial={{ opacity: 0, x: -6 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.04 }}
      className={clsx(
        "px-4 py-3 transition-colors",
        done && "opacity-60",
      )}
    >
      <div className="flex items-start gap-3">
        {/* Completion toggle */}
        <button
          onClick={onToggle}
          className={clsx(
            "mt-0.5 h-5 w-5 rounded-full border-2 shrink-0 flex items-center justify-center transition-all",
            done
              ? "bg-green-500 border-green-400 text-white"
              : "border-gray-600 hover:border-brand-500 text-transparent hover:text-brand-500",
          )}
          title={done ? "Mark incomplete" : "Mark complete"}
        >
          <CheckCircle2 className="h-3 w-3" />
        </button>

        {/* Session type icon */}
        <div className={clsx("mt-0.5 p-1.5 rounded-lg shrink-0 border", sm.bg)}>
          <TIcon className={clsx("h-3.5 w-3.5", sm.text)} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0 space-y-1">
          <div className="flex items-start gap-2 flex-wrap">
            <p className={clsx(
              "text-sm font-semibold leading-snug",
              done ? "line-through text-gray-500" : "text-gray-200",
            )}>
              {task.topic}
            </p>
            <Badge variant={sm.badge} className="text-[10px]">{sm.label}</Badge>
            <div className={clsx("h-1.5 w-1.5 rounded-full shrink-0 mt-1.5", PRIORITY_DOT[task.priority])} />
          </div>

          {/* Meta row */}
          <div className="flex items-center gap-3 text-xs text-gray-500 flex-wrap">
            {task.session_type !== "rest" && (
              <span className="flex items-center gap-1">
                <AlarmClock className="h-3 w-3" /> {task.duration_mins}min
              </span>
            )}
            <span className="flex items-center gap-1">
              {emoji} {task.technique}
            </span>
          </div>

          {/* Expandable details */}
          {hasDetails && (
            <>
              <button
                onClick={() => setOpen((v) => !v)}
                className="flex items-center gap-1 text-[10px] text-gray-600 hover:text-gray-400 transition-colors mt-0.5"
              >
                {open ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                {open ? "Hide details" : "Show details"}
              </button>

              <AnimatePresence>
                {open && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="pt-2 space-y-2">
                      {/* Subtopics */}
                      {task.subtopics.length > 0 && (
                        <ul className="space-y-0.5">
                          {task.subtopics.map((st, i) => (
                            <li key={i} className="flex items-start gap-1.5 text-xs text-gray-400">
                              <span className="text-gray-600 mt-0.5">·</span>
                              {st}
                            </li>
                          ))}
                        </ul>
                      )}

                      {/* Coaching note */}
                      {task.notes && (
                        <p className="text-xs text-gray-500 italic border-l-2 border-brand-500/30 pl-2">
                          {task.notes}
                        </p>
                      )}

                      {/* Resources */}
                      {task.resources.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {task.resources.map((r, ri) => (
                            <span key={ri} className="text-[10px] px-2 py-0.5 rounded-full bg-gray-800 border border-gray-700/60 text-gray-400">
                              {r}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </>
          )}
        </div>
      </div>
    </motion.div>
  );
}
