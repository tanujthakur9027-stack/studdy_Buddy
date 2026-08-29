import type { SourceChunk } from "@/lib/api";

export interface UploadedDocument {
  doc_id: string;
  filename: string;
  chunks: number;
  pages: number;
  parser_used: string;
  description: string;
  uploadedAt: Date;
  previewUrl?: string;   // object URL for image thumbnails (images only)
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
  /** DB-persisted message id (set after the API saves it) */
  dbId?: string;
}

/** Lightweight session summary shown in the sidebar */
export interface ChatSessionSummary {
  id: string;
  title: string;
  doc_id: string | null;
  updated_at: string;
  message_count: number;
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
