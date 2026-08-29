import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "studybuddy_saved_answers";
const MAX_SAVED = 50;

export interface SavedAnswer {
  id: string;
  question: string;
  answer: string;
  savedAt: string;   // ISO string
}

export function useSavedAnswers() {
  const [saved, setSaved] = useState<SavedAnswer[]>([]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setSaved(JSON.parse(raw) as SavedAnswer[]);
    } catch { /* ignore */ }
  }, []);

  const saveAnswer = useCallback((question: string, answer: string) => {
    setSaved((prev) => {
      // Avoid duplicates by question text
      const filtered = prev.filter((s) => s.question !== question);
      const next: SavedAnswer[] = [
        { id: `sa_${Date.now()}`, question, answer, savedAt: new Date().toISOString() },
        ...filtered,
      ].slice(0, MAX_SAVED);
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)); } catch { /* quota */ }
      return next;
    });
  }, []);

  const removeAnswer = useCallback((id: string) => {
    setSaved((prev) => {
      const next = prev.filter((s) => s.id !== id);
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)); } catch { /* quota */ }
      return next;
    });
  }, []);

  const isSaved = useCallback(
    (question: string) => saved.some((s) => s.question === question),
    [saved]
  );

  return { saved, saveAnswer, removeAnswer, isSaved };
}
