import axios from "axios";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: BASE,
  timeout: 120_000,
});

// ── Document Upload ──────────────────────────────────────────────────────────
export async function uploadDocument(file: File): Promise<{
  doc_id: string;
  filename: string;
  chunks: number;
  pages: number;
  parser_used: string;
  description: string;
}> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post("/api/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

// ── Explain Like I'm 10 ──────────────────────────────────────────────────────
export async function explainTopic(params: {
  topic: string;
  doc_id?: string;
  level?: "eli5" | "beginner" | "intermediate";
}): Promise<{ explanation: string; analogy: string; key_points: string[] }> {
  const { data } = await api.post("/api/explain", params);
  return data;
}

// ── Ask (RAG Q&A with mode toggle + rich sources) ────────────────────────────
export interface SourceChunk {
  filename: string;
  page: number;
  chunk_index: number;
  snippet: string;
}

export interface AskResponse {
  answer: string;
  mode_used: "standard" | "eli5";
  sources: SourceChunk[];
  follow_up_questions: string[];
  context_chunks_used: number;
}

export async function askQuestion(params: {
  question: string;
  doc_id?: string;
  mode?: "standard" | "eli5";
  k?: number;
  conversation_history?: Array<{ role: "user" | "assistant"; content: string }>;
}): Promise<AskResponse> {
  const { data } = await api.post("/api/ask", params);
  return data;
}

// ── Quiz Generation ──────────────────────────────────────────────────────────
export interface QuizQuestion {
  id: string;
  question: string;
  options: string[];           // always 4 items
  correct_index: number;       // 0-based
  explanation: string;
  difficulty: "easy" | "medium" | "hard";
  topic_tag: string;           // sub-topic label e.g. "Newton's Laws"
  hint: string;                // nudge shown after timeout
}

export interface QuizGenerateResponse {
  quiz_id: string;
  questions: QuizQuestion[];
  topic: string;               // resolved topic label
  timer_seconds: number;       // per-question countdown (15 or 30)
  difficulty: string;
}

export interface QuizAnswerDetail {
  question_id: string;
  question: string;
  user_index: number;          // -1 = timed out
  correct_index: number;
  is_correct: boolean;
  topic_tag: string;
  difficulty: "easy" | "medium" | "hard";
  explanation: string;
}

export interface QuizSubmitResponse {
  score: number;
  total: number;
  percentage: number;
  time_taken: number;
  details: QuizAnswerDetail[];
  weak_topics: string[];
  strong_topics: string[];
  recommendations: string[];
  grade: string;               // "S" | "A" | "B" | "C" | "D"
}

export async function generateQuiz(params: {
  doc_id?: string;
  topic?: string;
  num_questions?: number;
  difficulty?: "easy" | "medium" | "hard" | "mixed";
  timer_seconds?: number;
}): Promise<QuizGenerateResponse> {
  // Hit the new canonical endpoint; falls back gracefully if not found
  const { data } = await api.post("/api/generate-quiz", params);
  return data;
}

export async function submitQuizResult(params: {
  quiz_id: string;
  answers: Record<string, number>;
  time_taken: number;
}): Promise<QuizSubmitResponse> {
  const { data } = await api.post("/quiz/submit", params);
  return data;
}

// ── Revision Planner ─────────────────────────────────────────────────────────
export interface RevisionTask {
  date: string;
  day_label: string;
  session_type: "concept" | "quiz" | "buffer" | "rest";
  topic: string;
  subtopics: string[];
  duration_mins: number;
  priority: "high" | "medium" | "low";
  technique: string;
  resources: string[];
  notes: string;
}

export interface PlanStats {
  total_days: number;
  study_days: number;
  quiz_days: number;
  buffer_days: number;
  rest_days: number;
  total_study_mins: number;
  topics_covered: number;
  days_to_exam: number;
}

export interface RevisionPlanResponse {
  plan: RevisionTask[];
  summary: string;
  tips: string[];
  stats: PlanStats;
  topic_list: string[];
}

export async function generateRevisionPlan(params: {
  exam_date: string;
  daily_hours: number;
  syllabus_text?: string;
  topics?: string[];
  weak_topics?: string[];
  doc_id?: string;
}): Promise<RevisionPlanResponse> {
  const { data } = await api.post("/api/generate-plan", params);
  return data;
}

// ── RAG Doubt Solver (legacy — kept for backwards compat) ────────────────────
export async function solveDoubt(params: {
  question: string;
  doc_id?: string;
  conversation_history?: Array<{ role: "user" | "assistant"; content: string }>;
}): Promise<{ answer: string; sources: string[]; follow_up_questions: string[] }> {
  const { data } = await api.post("/api/doubt/solve", params);
  return data;
}
