"use client";
import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  BarChart2, Trophy, Flame, Target, Brain, TrendingUp,
  RefreshCw, BookOpen, Zap, Layers,
} from "lucide-react";
import { fetchProgressSummary } from "@/lib/api";
import type { ProgressSummary, TopicStat, DailyActivity, FeynmanHistoryPoint } from "@/lib/api";
import { Spinner, ProgressBar } from "@/components/ui";

const GRADE_COLOR: Record<string, string> = {
  S: "text-yellow-400",
  A: "text-green-400",
  B: "text-blue-400",
  C: "text-orange-400",
  D: "text-red-400",
};

function StatCard({
  icon: Icon,
  label,
  value,
  color,
  sub,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  color: string;
  sub?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card p-5 text-center"
    >
      <Icon className={`h-5 w-5 mx-auto mb-2 ${color}`} />
      <p className="text-2xl font-black text-white">{value}</p>
      <p className="text-[11px] text-gray-500 mt-0.5">{label}</p>
      {sub && <p className="text-[10px] text-gray-600 mt-0.5">{sub}</p>}
    </motion.div>
  );
}

function TopicBar({ stat, max, variant }: { stat: TopicStat; max: number; variant: "weak" | "strong" }) {
  const pct = max > 0 ? (stat.avg_pct / max) * 100 : 0;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-gray-300 truncate">{stat.topic}</span>
        <span className={variant === "weak" ? "text-red-400" : "text-green-400"}>
          {stat.avg_pct}%
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-gray-800 overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className={`h-full rounded-full ${variant === "weak" ? "bg-red-500" : "bg-green-500"}`}
        />
      </div>
      <p className="text-[10px] text-gray-600">{stat.attempts} {stat.attempts === 1 ? "quiz" : "quizzes"}</p>
    </div>
  );
}

function ScoreHistoryChart({ history }: { history: ProgressSummary["score_history"] }) {
  if (!history.length) return null;
  const reversed = [...history].reverse();
  const max = Math.max(...reversed.map((h) => h.percentage), 100);
  return (
    <div className="glass-card p-5 space-y-3">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest flex items-center gap-1.5">
        <TrendingUp className="h-3.5 w-3.5 text-brand-400" />
        Score History (last {reversed.length})
      </p>
      <div className="relative h-28">
        {/* Y-axis reference lines */}
        {[0, 50, 100].map((v) => (
          <div
            key={v}
            className="absolute left-0 right-0 border-t border-gray-800/60"
            style={{ bottom: `${(v / 100) * 100}%` }}
          >
            <span className="text-[9px] text-gray-700 absolute -top-2.5 -left-1">{v}</span>
          </div>
        ))}

        {/* Bars */}
        <div className="absolute inset-0 flex items-end gap-px pl-5">
          {reversed.map((pt, i) => {
            const h = (pt.percentage / max) * 100;
            const grade = pt.grade;
            const color =
              grade === "S" || grade === "A" ? "bg-green-500" :
              grade === "B" ? "bg-blue-500" :
              grade === "C" ? "bg-orange-500" : "bg-red-500";
            return (
              <motion.div
                key={i}
                title={`${pt.topic} · ${pt.percentage}% · ${grade}`}
                className={`flex-1 rounded-t-sm cursor-default ${color} opacity-80 hover:opacity-100 transition-opacity`}
                style={{ height: `${h}%` }}
                initial={{ height: 0 }}
                animate={{ height: `${h}%` }}
                transition={{ duration: 0.5, delay: i * 0.04 }}
              />
            );
          })}
        </div>
      </div>
      {/* X-axis labels — topic truncated */}
      <div className="flex pl-5 gap-px">
        {reversed.map((pt, i) => (
          <div key={i} className="flex-1 text-center">
            <span className="text-[8px] text-gray-700 truncate block">{pt.topic.slice(0, 6)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Activity Heatmap (GitHub-style, 13 weeks × 7 days) ───────────────────────
function ActivityHeatmap({ activity }: { activity: DailyActivity[] }) {
  // Build a lookup: date string → count
  const lookup: Record<string, number> = {};
  for (const a of activity) lookup[a.date] = a.count;

  // Build grid: 13 weeks (cols) × 7 days (rows), ending today
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  // Start from Sunday of the week 12 weeks ago
  const startOffset = (today.getDay() + 7 * 12); // days back to last Sunday of first week
  const startDate = new Date(today);
  startDate.setDate(today.getDate() - startOffset);

  const weeks: { date: string; count: number }[][] = [];
  for (let w = 0; w < 13; w++) {
    const week: { date: string; count: number }[] = [];
    for (let d = 0; d < 7; d++) {
      const cell = new Date(startDate);
      cell.setDate(startDate.getDate() + w * 7 + d);
      const iso = cell.toISOString().slice(0, 10);
      week.push({ date: iso, count: lookup[iso] ?? 0 });
    }
    weeks.push(week);
  }

  const maxCount = Math.max(...activity.map((a) => a.count), 1);

  function cellColor(count: number): string {
    if (count === 0) return "bg-gray-800";
    const intensity = count / maxCount;
    if (intensity < 0.25) return "bg-green-900";
    if (intensity < 0.5)  return "bg-green-700";
    if (intensity < 0.75) return "bg-green-500";
    return "bg-green-400";
  }

  const DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  return (
    <div className="glass-card p-5 space-y-3">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest flex items-center gap-1.5">
        <Flame className="h-3.5 w-3.5 text-orange-400" />
        Study Activity — Last 90 Days
      </p>
      <div className="flex gap-1 overflow-x-auto pb-1">
        {/* Day labels column */}
        <div className="flex flex-col gap-1 mr-1 shrink-0">
          <div className="h-2" />{/* spacer for month label row */}
          {DAY_LABELS.map((d, i) => (
            <div key={d} className="h-3 flex items-center">
              {i % 2 === 1 && (
                <span className="text-[8px] text-gray-600 w-6 leading-none">{d}</span>
              )}
              {i % 2 === 0 && <span className="w-6" />}
            </div>
          ))}
        </div>
        {/* Week columns */}
        {weeks.map((week, wi) => (
          <div key={wi} className="flex flex-col gap-1 shrink-0">
            {/* Month label — show on first day of month */}
            <div className="h-2 flex items-end">
              {week[0].date.slice(8, 10) === "01" && (
                <span className="text-[8px] text-gray-600 leading-none">
                  {new Date(week[0].date + "T00:00:00").toLocaleString("default", { month: "short" })}
                </span>
              )}
            </div>
            {week.map((cell) => (
              <div
                key={cell.date}
                title={`${cell.date}: ${cell.count} event${cell.count !== 1 ? "s" : ""}`}
                className={`h-3 w-3 rounded-sm ${cellColor(cell.count)}`}
              />
            ))}
          </div>
        ))}
      </div>
      {/* Legend */}
      <div className="flex items-center gap-1.5 text-[9px] text-gray-600">
        <span>Less</span>
        {["bg-gray-800", "bg-green-900", "bg-green-700", "bg-green-500", "bg-green-400"].map((c) => (
          <div key={c} className={`h-3 w-3 rounded-sm ${c}`} />
        ))}
        <span>More</span>
      </div>
    </div>
  );
}

// ── Feynman Score Sparkline ───────────────────────────────────────────────────
function FeynmanSparkline({ history }: { history: FeynmanHistoryPoint[] }) {
  if (!history.length) return null;
  const reversed = [...history].reverse(); // oldest → newest
  const W = 200;
  const H = 48;
  const pad = 4;
  const n = reversed.length;

  const points = reversed.map((pt, i) => {
    const x = pad + (i / Math.max(n - 1, 1)) * (W - pad * 2);
    const y = H - pad - (pt.score / 100) * (H - pad * 2);
    return `${x},${y}`;
  });

  const polyline = points.join(" ");

  return (
    <div className="glass-card p-5 space-y-3">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest flex items-center gap-1.5">
        <Brain className="h-3.5 w-3.5 text-pink-400" />
        Feynman Scores
      </p>
      <div className="flex items-end gap-4">
        <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="shrink-0">
          {/* Zero line */}
          <line x1={pad} y1={H - pad} x2={W - pad} y2={H - pad} stroke="#374151" strokeWidth="1" />
          {/* 50% reference */}
          <line
            x1={pad} y1={(H - pad) / 2 + pad / 2} x2={W - pad} y2={(H - pad) / 2 + pad / 2}
            stroke="#374151" strokeWidth="1" strokeDasharray="2 3"
          />
          {/* Sparkline */}
          <polyline
            points={polyline}
            fill="none"
            stroke="#f472b6"
            strokeWidth="2"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
          {/* Dots */}
          {reversed.map((pt, i) => {
            const x = pad + (i / Math.max(n - 1, 1)) * (W - pad * 2);
            const y = H - pad - (pt.score / 100) * (H - pad * 2);
            return (
              <circle key={i} cx={x} cy={y} r={2.5} fill="#f472b6">
                <title>{`${pt.concept} · ${pt.score}/100 · ${pt.grade}`}</title>
              </circle>
            );
          })}
        </svg>
        {/* Latest score callout */}
        <div className="shrink-0 text-right">
          <p className="text-2xl font-black text-pink-400">{reversed[reversed.length - 1].score}</p>
          <p className="text-[10px] text-gray-600">latest</p>
        </div>
      </div>
      {/* Mini history list */}
      <div className="space-y-1">
        {[...history].slice(0, 3).map((pt, i) => (
          <div key={i} className="flex items-center justify-between text-xs">
            <span className="text-gray-400 truncate max-w-[140px]">{pt.concept}</span>
            <span className={`font-semibold ${GRADE_COLOR[pt.grade] ?? "text-gray-400"}`}>
              {pt.score}/100 · {pt.grade}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ProgressDashboard() {
  const [data,    setData]    = useState<ProgressSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(false);

  const load = () => {
    setLoading(true);
    setError(false);
    fetchProgressSummary()
      .then(setData)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div className="p-3 rounded-2xl bg-brand-500/10 text-brand-400 shrink-0">
          <BarChart2 className="h-7 w-7" />
        </div>
        <div className="flex-1">
          <h2 className="section-heading">Progress Dashboard</h2>
          <p className="text-sm text-gray-400 mt-1">
            Your study stats across all quizzes, flashcards, and Feynman sessions.
          </p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="p-2 rounded-xl bg-gray-900 border border-gray-700 text-gray-400 hover:text-gray-200 transition-colors"
          title="Refresh"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-16">
          <Spinner size="lg" />
        </div>
      )}

      {error && !loading && (
        <div className="text-center py-16 text-gray-500 text-sm">
          Failed to load progress. <button onClick={load} className="text-brand-400 hover:underline">Try again</button>
        </div>
      )}

      {data && !loading && (
        <>
          {/* Zero-state */}
          {data.total_quizzes === 0 && data.flashcard_stats.total_sessions === 0 && data.feynman_history.length === 0 && (
            <div className="text-center py-16 space-y-3">
              <div className="h-14 w-14 rounded-2xl bg-brand-500/10 text-brand-400 flex items-center justify-center mx-auto">
                <Zap className="h-7 w-7" />
              </div>
              <p className="text-gray-400">No activity yet.</p>
              <p className="text-xs text-gray-600">Take a quiz, study flashcards, or try Feynman mode!</p>
            </div>
          )}

          {(data.total_quizzes > 0 || data.flashcard_stats.total_sessions > 0 || data.feynman_history.length > 0) && (
            <>
              {/* Stat cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <StatCard icon={Trophy}   label="Quizzes taken"       value={data.total_quizzes}             color="text-yellow-400" />
                <StatCard icon={Brain}    label="Avg quiz score"       value={`${data.avg_score_pct}%`}       color="text-brand-400"  />
                <StatCard icon={Flame}    label="Study streak"          value={`${data.current_streak_days}d`} color="text-orange-400" sub="consecutive days" />
                <StatCard icon={BookOpen} label="Questions answered"   value={data.total_questions_answered}  color="text-green-400"  />
              </div>

              {/* Flashcard stats row */}
              {data.flashcard_stats.total_sessions > 0 && (
                <div className="grid grid-cols-2 gap-3">
                  <StatCard
                    icon={Layers}
                    label="Flashcard sessions"
                    value={data.flashcard_stats.total_sessions}
                    color="text-amber-400"
                  />
                  <StatCard
                    icon={Zap}
                    label="Cards studied"
                    value={data.flashcard_stats.total_cards}
                    color="text-amber-400"
                  />
                </div>
              )}

              {/* Activity Heatmap */}
              <ActivityHeatmap activity={data.daily_activity} />

              {/* Best score */}
              {data.total_quizzes > 0 && (
                <div className="glass-card p-5 flex items-center gap-4">
                  <Trophy className="h-8 w-8 text-yellow-400 shrink-0" />
                  <div className="flex-1">
                    <p className="text-xs text-gray-500 uppercase tracking-widest mb-1">Personal Best</p>
                    <ProgressBar value={data.best_score_pct} className="h-3" />
                  </div>
                  <span className="text-2xl font-black text-yellow-400 shrink-0">{data.best_score_pct}%</span>
                </div>
              )}

              {/* Score history chart */}
              {data.total_quizzes > 0 && <ScoreHistoryChart history={data.score_history} />}

              {/* Feynman sparkline */}
              {data.feynman_history.length > 0 && <FeynmanSparkline history={data.feynman_history} />}

              {/* Topic breakdown */}
              {data.total_quizzes > 0 && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Weak topics */}
                  {data.weak_topics.length > 0 && (
                    <div className="glass-card p-5 space-y-4">
                      <p className="text-xs font-semibold text-red-400 uppercase tracking-widest flex items-center gap-1.5">
                        <Target className="h-3.5 w-3.5" /> Topics to Revisit
                      </p>
                      {data.weak_topics.map((t) => (
                        <TopicBar key={t.topic} stat={t} max={100} variant="weak" />
                      ))}
                    </div>
                  )}
                  {/* Strong topics */}
                  {data.strong_topics.length > 0 && (
                    <div className="glass-card p-5 space-y-4">
                      <p className="text-xs font-semibold text-green-400 uppercase tracking-widest flex items-center gap-1.5">
                        <Trophy className="h-3.5 w-3.5" /> Strongest Topics
                      </p>
                      {data.strong_topics.map((t) => (
                        <TopicBar key={t.topic} stat={t} max={100} variant="strong" />
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Recent quiz list */}
              {data.score_history.length > 0 && (
                <div className="glass-card overflow-hidden">
                  <p className="px-5 pt-5 pb-3 text-xs font-semibold text-gray-400 uppercase tracking-widest">Recent Quizzes</p>
                  <div className="divide-y divide-gray-800">
                    {data.score_history.map((pt, i) => (
                      <div key={i} className="flex items-center gap-3 px-5 py-3">
                        <span className={`text-lg font-black shrink-0 w-7 ${GRADE_COLOR[pt.grade] ?? "text-gray-400"}`}>
                          {pt.grade}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-gray-200 truncate">{pt.topic || "General"}</p>
                          <p className="text-xs text-gray-600">
                            {pt.score}/{pt.total} · {new Date(pt.date).toLocaleDateString()}
                          </p>
                        </div>
                        <span className={`text-sm font-bold shrink-0 ${pt.percentage >= 80 ? "text-green-400" : pt.percentage >= 50 ? "text-orange-400" : "text-red-400"}`}>
                          {pt.percentage}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
