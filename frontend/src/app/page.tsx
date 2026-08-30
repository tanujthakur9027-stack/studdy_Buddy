"use client";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload, Lightbulb, Zap, CalendarDays, MessageCircle,
  GraduationCap, ChevronRight, Sparkles, ExternalLink, FileText, BarChart2,
  Brain, Layers,
} from "lucide-react";
import Link from "next/link";
import { FileUpload } from "@/components/features/FileUpload";
import { ExplainModule } from "@/components/features/ExplainModule";
import { QuizGame } from "@/components/features/QuizGame";
import { RevisionPlanner } from "@/components/features/RevisionPlanner";
import { DoubtSolver } from "@/components/features/DoubtSolver";
import { ProgressDashboard } from "@/components/features/ProgressDashboard";
import { FeynmanMode } from "@/components/features/FeynmanMode";
import { Flashcards } from "@/components/features/Flashcards";
import { fetchDocuments } from "@/lib/api";
import type { UploadedDocument, AppTab } from "@/types";
import { clsx } from "clsx";

const TABS: { id: AppTab; label: string; icon: React.ElementType; color: string; desc: string }[] = [
  { id: "upload",     label: "Upload",    icon: Upload,       color: "text-brand-400",   desc: "Syllabus & notes" },
  { id: "explain",    label: "ELI10",     icon: Lightbulb,    color: "text-yellow-400",  desc: "Simplified learning" },
  { id: "quiz",       label: "Quiz",      icon: Zap,          color: "text-purple-400",  desc: "Kahoot-style game" },
  { id: "planner",    label: "Planner",   icon: CalendarDays, color: "text-emerald-400", desc: "Revision schedule" },
  { id: "doubt",      label: "Ask AI",    icon: MessageCircle,color: "text-cyan-400",    desc: "RAG doubt solver" },
  { id: "feynman",    label: "Feynman",   icon: Brain,        color: "text-pink-400",    desc: "Teach it back" },
  { id: "flashcards", label: "Flashcards",icon: Layers,       color: "text-amber-400",   desc: "Flip card practice" },
  { id: "progress",   label: "Progress",  icon: BarChart2,    color: "text-brand-400",   desc: "Study analytics" },
];

export default function HomePage() {
  const [activeTab,    setActiveTab]    = useState<AppTab>("upload");
  const [documents,    setDocuments]    = useState<UploadedDocument[]>([]);
  const [selectedDoc,  setSelectedDoc]  = useState<string | undefined>(undefined);

  // Load persisted documents from the backend DB on mount
  useEffect(() => {
    fetchDocuments()
      .then((stored) => {
        if (stored.length) {
          const docs: UploadedDocument[] = stored.map((d) => ({
            doc_id: d.doc_id,
            filename: d.filename,
            description: d.description,
            pages: d.pages,
            chunks: d.chunks,
            parser_used: d.parser_used,
            uploadedAt: new Date(d.uploaded_at),
          }));
          setDocuments(docs);
          setSelectedDoc(docs[docs.length - 1].doc_id);
        }
      })
      .catch(() => {
        // API not reachable — start with empty state, user can re-upload
      });
  }, []);

  // When a new document is uploaded, auto-select it
  const handleUploaded = (doc: UploadedDocument) => {
    setDocuments((prev) => {
      const next = [...prev.filter((d) => d.doc_id !== doc.doc_id), doc];
      return next;
    });
    setSelectedDoc(doc.doc_id);
  };

  const handleRemove = (docId: string) => {
    setDocuments((prev) => {
      const next = prev.filter((d) => d.doc_id !== docId);
      // If we removed the selected doc, fall back to the last remaining one
      if (selectedDoc === docId) {
        setSelectedDoc(next[next.length - 1]?.doc_id);
      }
      return next;
    });
  };

  // The active doc ID used by all features
  const activeDocId = selectedDoc ?? documents[documents.length - 1]?.doc_id;

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      {/* Top Nav */}
      <header className="sticky top-0 z-50 border-b border-gray-800/80 bg-gray-950/80 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-xl bg-brand-600 flex items-center justify-center">
              <GraduationCap className="h-5 w-5 text-white" />
            </div>
            <div>
              <span className="font-bold text-white text-base">StudyBuddy</span>
              <span className="ml-2 text-xs text-brand-400 font-medium">AI</span>
            </div>
          </div>
          {documents.length > 0 && (
            <div className="flex items-center gap-2 text-xs text-gray-400 bg-gray-900 border border-gray-700 px-3 py-1.5 rounded-full">
              <span className="h-2 w-2 rounded-full bg-green-400 animate-pulse" />
              {documents.length} doc{documents.length > 1 ? "s" : ""} indexed
            </div>
          )}
        </div>
      </header>

      {/* Hero (shown on first load) */}
      <AnimatePresence>
        {activeTab === "upload" && documents.length === 0 && (
          <motion.section
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, height: 0, marginBottom: 0 }}
            className="bg-gradient-to-b from-brand-950/40 to-transparent border-b border-gray-800/40"
          >
            <div className="max-w-6xl mx-auto px-4 sm:px-6 py-14 text-center">
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-brand-500/10 border border-brand-500/25 text-brand-400 text-xs font-semibold mb-6"
              >
                <Sparkles className="h-3.5 w-3.5" />
                Powered by RAG + LLM
              </motion.div>
              <h1 className="text-4xl sm:text-5xl font-black text-white tracking-tight mb-4">
                Your Personal{" "}
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-400 to-purple-400">
                  AI Study Buddy
                </span>
              </h1>
              <p className="text-gray-400 text-lg max-w-xl mx-auto mb-8">
                Upload your notes or syllabus, get simplified explanations, play quiz games,
                build a revision plan, and solve doubts — all in one place.
              </p>
              <div className="flex flex-wrap justify-center gap-4 text-sm">
                {[
                  "📄 PDF & Text Upload",
                  "🧒 ELI10 Explanations",
                  "⚡ Timed Quiz Game",
                  "📅 Smart Revision Plan",
                  "🤖 RAG Chat",
                ].map((f) => (
                  <span key={f} className="px-4 py-2 rounded-full bg-gray-900 border border-gray-700 text-gray-300">
                    {f}
                  </span>
                ))}
              </div>
            </div>
          </motion.section>
        )}
      </AnimatePresence>

      {/* Main layout */}
      <div className="flex-1 max-w-6xl mx-auto w-full px-4 sm:px-6 py-8 flex gap-6">
        {/* Sidebar Tabs */}
        <aside className="hidden md:flex flex-col gap-1 w-48 shrink-0">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <motion.button
                key={tab.id}
                whileHover={{ x: isActive ? 0 : 3 }}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl text-left transition-all duration-200 ${
                  isActive
                    ? "bg-gray-800 border border-gray-700/80 shadow-sm"
                    : "hover:bg-gray-900/60 border border-transparent"
                }`}
              >
                <Icon className={`h-4 w-4 shrink-0 ${isActive ? tab.color : "text-gray-500"}`} />
                <div>
                  <p className={`text-sm font-semibold ${isActive ? "text-white" : "text-gray-400"}`}>
                    {tab.label}
                  </p>
                  <p className="text-[10px] text-gray-600">{tab.desc}</p>
                </div>
                {isActive && <ChevronRight className="h-3.5 w-3.5 text-gray-500 ml-auto" />}
              </motion.button>
            );
          })}

          {/* Active doc list with selector */}
          {documents.length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-800">
              <p className="text-[10px] text-gray-500 uppercase tracking-widest px-4 mb-2">
                {documents.length > 1 ? "Select Document" : "Active Doc"}
              </p>
              {documents.slice(-5).map((doc) => (
                <button
                  key={doc.doc_id}
                  onClick={() => setSelectedDoc(doc.doc_id)}
                  className={clsx(
                    "w-full flex items-center gap-2 px-3 py-1.5 rounded-lg text-left text-xs transition-colors",
                    selectedDoc === doc.doc_id
                      ? "bg-gray-800 text-gray-200 border border-gray-700"
                      : "text-gray-500 hover:text-gray-300 hover:bg-gray-900/60",
                  )}
                >
                  <FileText className={clsx(
                    "h-3 w-3 shrink-0",
                    selectedDoc === doc.doc_id ? "text-brand-400" : "text-gray-600",
                  )} />
                  <span className="truncate">{doc.filename}</span>
                </button>
              ))}
            </div>
          )}
        </aside>

        {/* Mobile Tab Bar */}
        <div className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-gray-950/95 backdrop-blur-xl border-t border-gray-800 px-2 py-2 flex justify-around">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-xl transition-colors ${
                  isActive ? "text-white" : "text-gray-500"
                }`}
              >
                <Icon className={`h-5 w-5 ${isActive ? tab.color : ""}`} />
                <span className="text-[9px] font-medium">{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Content Panel */}
        <main className="flex-1 min-w-0 pb-20 md:pb-0">
          {/* Document selector banner for mobile / multi-doc */}
          {documents.length > 1 && activeTab !== "upload" && (
            <div className="mb-4 flex items-center gap-2 p-3 rounded-xl bg-gray-900 border border-gray-800 overflow-x-auto">
              <FileText className="h-3.5 w-3.5 text-brand-400 shrink-0" />
              <p className="text-xs text-gray-500 shrink-0">Context:</p>
              <div className="flex gap-1.5">
                {documents.map((doc) => (
                  <button
                    key={doc.doc_id}
                    onClick={() => setSelectedDoc(doc.doc_id)}
                    className={clsx(
                      "px-2.5 py-1 rounded-lg text-xs font-medium border transition-all whitespace-nowrap",
                      selectedDoc === doc.doc_id
                        ? "bg-brand-600 border-brand-500 text-white"
                        : "bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-600",
                    )}
                  >
                    {doc.filename}
                  </button>
                ))}
              </div>
            </div>
          )}

          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.22 }}
              className="glass-card p-6 sm:p-8 min-h-[500px]"
            >
              {activeTab === "upload" && (
                <div className="space-y-6">
                  <div>
                    <h2 className="section-heading">Upload Documents</h2>
                    <p className="text-sm text-gray-400 mt-1">
                      Upload your syllabus, PDF notes, or text files to enable AI features.
                    </p>
                  </div>
                  <FileUpload
                    onUploaded={handleUploaded}
                    documents={documents}
                    onRemove={handleRemove}
                  />
                  {documents.length > 0 && (
                    <motion.div
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="p-4 rounded-xl bg-green-500/8 border border-green-500/20 text-sm text-green-300"
                    >
                      ✅ Documents indexed! Use the tabs on the left to explore features.
                    </motion.div>
                  )}
                </div>
              )}
              {activeTab === "explain" && <ExplainModule docId={activeDocId} />}
              {activeTab === "quiz"    && (
                <div className="space-y-4">
                  <div className="flex items-center justify-end">
                    <Link
                      href={`/quiz${activeDocId ? `?doc_id=${activeDocId}` : ""}`}
                      className="btn-secondary text-xs py-1.5 px-3"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                      Open full-page
                    </Link>
                  </div>
                  <QuizGame docId={activeDocId} />
                </div>
              )}
              {activeTab === "planner" && (
                <div className="space-y-4">
                  <div className="flex items-center justify-end">
                    <Link
                      href={`/planner${activeDocId ? `?doc_id=${activeDocId}` : ""}`}
                      className="btn-secondary text-xs py-1.5 px-3"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                      Open full-page
                    </Link>
                  </div>
                  <RevisionPlanner docId={activeDocId} />
                </div>
              )}
              {activeTab === "doubt"      && <DoubtSolver docId={activeDocId} />}
              {activeTab === "feynman"    && <FeynmanMode docId={activeDocId} />}
              {activeTab === "flashcards" && <Flashcards docId={activeDocId} />}
              {activeTab === "progress"   && <ProgressDashboard />}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
