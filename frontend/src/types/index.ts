export interface UploadedDocument {
  doc_id: string;
  filename: string;
  chunks: number;
  uploadedAt: Date;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: string[];
  followUpQuestions?: string[];
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
