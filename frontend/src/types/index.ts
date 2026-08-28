import type { SourceChunk } from "@/lib/api";

export interface UploadedDocument {
  doc_id: string;
  filename: string;
  chunks: number;
  uploadedAt: Date;
}

export interface ChatMessage {
  id: string;                          // stable ID for reliable removal/keying
  role: "user" | "assistant";
  content: string;
  sources?: SourceChunk[];             // rich source chunks (filename + page + snippet)
  sourceNames?: string[];              // simple filename list (legacy doubt/solve path)
  followUpQuestions?: string[];
  mode?: "standard" | "eli5";
  timestamp: Date;
}

export type AppTab = "upload" | "explain" | "quiz" | "planner" | "doubt";

export interface QuizState {
  currentIndex: number;
  answers: Record<string, number>;
  score: number;
  timeLeft: number;
  phase: "idle" | "playing" | "reviewing" | "results";
  startTime?: number;
}

export interface PlannerFormData {
  topics: string;
  examDate: string;
  dailyHours: number;
}
