import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "studybuddy_quiz_history";
const MAX_ENTRIES = 20;

export interface QuizHistoryEntry {
  id: string;
  date: string;          // ISO string
  topic: string;
  score: number;
  total: number;
  percentage: number;
  grade: string;
  timeTaken: number;     // seconds
  difficulty: string;
}

export function useQuizHistory() {
  const [history, setHistory] = useState<QuizHistoryEntry[]>([]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setHistory(JSON.parse(raw) as QuizHistoryEntry[]);
    } catch {
      // ignore corrupt storage
    }
  }, []);

  const addEntry = useCallback((entry: Omit<QuizHistoryEntry, "id" | "date">) => {
    setHistory((prev) => {
      const next: QuizHistoryEntry[] = [
        { ...entry, id: `qh_${Date.now()}`, date: new Date().toISOString() },
        ...prev,
      ].slice(0, MAX_ENTRIES);
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)); } catch { /* quota */ }
      return next;
    });
  }, []);

  const clearHistory = useCallback(() => {
    setHistory([]);
    try { localStorage.removeItem(STORAGE_KEY); } catch { /* ignore */ }
  }, []);

  return { history, addEntry, clearHistory };
}
