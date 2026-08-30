import axios from "axios";

// ── Chat History ──────────────────────────────────────────────────────────────
export interface ChatSessionEntry {
  id: string;
  title: string;
  doc_id: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ChatMessageEntry {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  sources_json: string;   // raw JSON — parse with JSON.parse()
  mode: string;
  created_at: string;
}

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

// ── Document Management ───────────────────────────────────────────────────────
export interface StoredDocument {
  doc_id: string;
  filename: string;
  description: string;
  pages: number;
  chunks: number;
  total_chars: number;
  total_tokens: number;
  parser_used: string;
  uploaded_at: string;
}

export async function fetchDocuments(): Promise<StoredDocument[]> {
  const { data } = await api.get("/api/documents");
  return data;
}

export async function deleteDocument(docId: string): Promise<void> {
  await api.delete(`/api/documents/${docId}`);
}

// ── Quiz History ──────────────────────────────────────────────────────────────
export interface QuizHistoryEntry {
  id: string;
  quiz_id: string;
  topic: string;
  difficulty: string;
  score: number;
  total: number;
  percentage: number;
  grade: string;
  time_taken: number;
  completed_at: string;
}

export async function fetchQuizHistory(limit = 20): Promise<QuizHistoryEntry[]> {
  const { data } = await api.get(`/api/quiz/history?limit=${limit}`);
  return data;
}

// ── Saved Answers ─────────────────────────────────────────────────────────────
export interface SavedAnswerEntry {
  id: string;
  question: string;
  answer: string;
  saved_at: string;
}

export async function fetchSavedAnswers(): Promise<SavedAnswerEntry[]> {
  const { data } = await api.get("/api/saved-answers");
  return data;
}

export async function saveAnswer(question: string, answer: string): Promise<{ id: string; saved_at: string }> {
  const { data } = await api.post("/api/saved-answers", { question, answer });
  return data;
}

export async function deleteSavedAnswer(id: string): Promise<void> {
  await api.delete(`/api/saved-answers/${id}`);
}

// ── Feynman Mode ─────────────────────────────────────────────────────────────
export interface QAPair {
  question: string;
  answer: string;
}

export interface FeynmanResponse {
  score: number;
  grade: string;
  strengths: string[];
  gaps: string[];
  qa_pairs: QAPair[];
  coaching_tip: string;
}

export async function evaluateFeynman(params: {
  concept: string;
  explanation: string;
  doc_id?: string | null;
}): Promise<FeynmanResponse> {
  const { data } = await api.post("/api/feynman/evaluate", params);
  return data;
}

// ── Cheat Sheet ───────────────────────────────────────────────────────────────
/** POST /api/cheatsheet — returns an AbortController (streaming SSE).
 *  Use streamPost from streamApi.ts to consume it; this just provides the type. */
export interface CheatsheetRequest {
  doc_id: string;
  topic?: string;
}

// ── Share Links ───────────────────────────────────────────────────────────────
export interface ShareOut {
  id: string;
  resource_type: string;
  title: string;
  created_at: string;
  expires_at: string | null;
  share_url: string;
}

export interface ShareResolved {
  id: string;
  resource_type: string;
  title: string;
  payload: Record<string, unknown>;
  created_at: string;
  expires_at: string | null;
}

export async function createShareLink(
  resourceType: "quiz" | "document",
  payload: Record<string, unknown>,
  title: string,
  expiresDays = 30,
): Promise<ShareOut> {
  const { data } = await api.post("/api/share", {
    resource_type: resourceType,
    payload,
    title,
    expires_days: expiresDays,
  });
  return data;
}

export async function resolveShareLink(shareId: string): Promise<ShareResolved> {
  const { data } = await api.get(`/api/share/${shareId}`);
  return data;
}

// ── Progress ──────────────────────────────────────────────────────────────────
export interface QuizScorePoint {
  date: string;
  percentage: number;
  grade: string;
  topic: string;
  score: number;
  total: number;
}

export interface TopicStat {
  topic: string;
  avg_pct: number;
  attempts: number;
}

export interface DailyActivity {
  date: string;   // YYYY-MM-DD
  count: number;
}

export interface FlashcardStats {
  total_sessions: number;
  total_cards: number;
}

export interface FeynmanHistoryPoint {
  date: string;
  score: number;
  concept: string;
  grade: string;
}

export interface ProgressSummary {
  total_quizzes: number;
  avg_score_pct: number;
  best_score_pct: number;
  current_streak_days: number;
  total_questions_answered: number;
  score_history: QuizScorePoint[];
  weak_topics: TopicStat[];
  strong_topics: TopicStat[];
  daily_activity: DailyActivity[];
  flashcard_stats: FlashcardStats;
  feynman_history: FeynmanHistoryPoint[];
}

export async function fetchProgressSummary(): Promise<ProgressSummary> {
  const { data } = await api.get("/api/progress/summary");
  return data;
}

export async function fetchChatSessions(): Promise<ChatSessionEntry[]> {
  const { data } = await api.get("/api/chats");
  return data;
}

export async function createChatSession(title = "New Chat", docId?: string): Promise<ChatSessionEntry> {
  const { data } = await api.post("/api/chats", { title, doc_id: docId ?? null });
  return data;
}

export async function deleteChatSession(sessionId: string): Promise<void> {
  await api.delete(`/api/chats/${sessionId}`);
}

export async function fetchChatMessages(sessionId: string): Promise<ChatMessageEntry[]> {
  const { data } = await api.get(`/api/chats/${sessionId}/messages`);
  return data;
}

export async function appendChatMessage(
  sessionId: string,
  role: "user" | "assistant",
  content: string,
  sourcesJson = "[]",
  mode = "standard",
): Promise<ChatMessageEntry> {
  const { data } = await api.post(`/api/chats/${sessionId}/messages`, {
    role, content, sources_json: sourcesJson, mode,
  });
  return data;
}

export async function renameChatSession(sessionId: string, title: string): Promise<ChatSessionEntry> {
  const { data } = await api.patch(`/api/chats/${sessionId}/title`, { title });
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
