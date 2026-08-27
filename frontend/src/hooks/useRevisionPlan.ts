"use client";
/**
 * useRevisionPlan — manages completion state for a generated revision plan.
 *
 * Completion state is persisted to localStorage keyed by a plan fingerprint
 * (hash of all task dates + topics), so it survives page refreshes.
 *
 * Returns:
 *   completed          — Set<taskKey>  (key = "date::topic::index")
 *   toggleTask(key)    — mark/unmark a task complete
 *   isComplete(key)    — boolean
 *   overallProgress    — 0–100 (% of all tasks ticked)
 *   dayProgress(date)  — 0–100 for one day's tasks
 *   resetPlan()        — clear all completions for current plan
 *   planKey            — the storage key used (useful for debugging)
 */

import { useState, useCallback, useEffect, useMemo } from "react";
import type { RevisionTask } from "@/lib/api";

function makePlanKey(tasks: RevisionTask[]): string {
  // Stable fingerprint: concat first 6 chars of each date+topic
  const raw = tasks.map((t) => `${t.date}:${t.topic}`).join("|");
  // Simple djb2-style hash
  let h = 5381;
  for (let i = 0; i < raw.length; i++) {
    h = ((h << 5) + h) ^ raw.charCodeAt(i);
    h = h >>> 0;
  }
  return `revision_plan_${h.toString(36)}`;
}

export function makeTaskKey(task: RevisionTask, index: number): string {
  return `${task.date}::${task.topic}::${index}`;
}

export function useRevisionPlan(tasks: RevisionTask[]) {
  const planKey = useMemo(() => (tasks.length ? makePlanKey(tasks) : ""), [tasks]);

  const [completed, setCompleted] = useState<Set<string>>(() => {
    if (typeof window === "undefined" || !planKey) return new Set();
    try {
      const stored = localStorage.getItem(planKey);
      return stored ? new Set<string>(JSON.parse(stored)) : new Set();
    } catch {
      return new Set();
    }
  });

  // Re-load from storage whenever planKey changes (new plan generated)
  useEffect(() => {
    if (!planKey) return;
    try {
      const stored = localStorage.getItem(planKey);
      setCompleted(stored ? new Set<string>(JSON.parse(stored)) : new Set());
    } catch {
      setCompleted(new Set());
    }
  }, [planKey]);

  // Persist to localStorage whenever completed changes
  useEffect(() => {
    if (!planKey) return;
    try {
      localStorage.setItem(planKey, JSON.stringify(Array.from(completed)));
    } catch {
      // localStorage quota exceeded — silently ignore
    }
  }, [planKey, completed]);

  const toggleTask = useCallback((key: string) => {
    setCompleted((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const isComplete = useCallback(
    (key: string) => completed.has(key),
    [completed],
  );

  const overallProgress = useMemo(() => {
    if (!tasks.length) return 0;
    return Math.round((completed.size / tasks.length) * 100);
  }, [tasks.length, completed.size]);

  const dayProgress = useCallback(
    (date: string, dayTasks: RevisionTask[]) => {
      if (!dayTasks.length) return 0;
      const done = dayTasks.filter((t, i) => {
        const globalIdx = tasks.findIndex(
          (x) => x.date === t.date && x.topic === t.topic,
        );
        return completed.has(makeTaskKey(t, globalIdx));
      }).length;
      return Math.round((done / dayTasks.length) * 100);
    },
    [tasks, completed],
  );

  const resetPlan = useCallback(() => {
    setCompleted(new Set());
    if (planKey) {
      try { localStorage.removeItem(planKey); } catch { /* ignore */ }
    }
  }, [planKey]);

  return { completed, toggleTask, isComplete, overallProgress, dayProgress, resetPlan, planKey };
}
