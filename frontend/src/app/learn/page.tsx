"use client";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload, Lightbulb, Zap, CalendarDays, MessageCircle,
  Brain, Layers, BarChart2, FileText, ChevronRight, Sparkles, GraduationCap,
} from "lucide-react";
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
  { id: "upload",     label: "Upload",     icon: Upload,        color: "text-blue-400",    desc: "Syllabus & notes" },
  { id: "explain",    label: "ELI10",      icon: Lightbulb,     color: "text-yellow-400",  desc: "Simplified learning" },
  { id: "quiz",       label: "Quiz",       icon: Zap,           color: "text-purple-400",  desc: "Kahoot-style game" },
  { id: "planner",    label: "Planner",    icon: CalendarDays,  color: "text-emerald-400", desc: "Revision schedule" },
  { id: "doubt",      label: "Ask AI",     icon: MessageCircle, color: "text-cyan-400",    desc: "RAG doubt solver" },
  { id: "feynman",    label: "Feynman",    icon: Brain,         color: "text-pink-400",    desc: "Teach it back" },
  { id: "flashcards", label: "Flashcards", icon: Layers,        color: "text-amber-400",   desc: "Flip card practice" },
  { id: "progress",   label: "Progress",   icon: BarChart2,     color: "text-blue-400",    desc: "Study analytics" },
];

export default function LearnPage() {
  const [activeTab, setActiveTab] = useState<AppTab>("upload");
  const [documents, setDocuments] = useState<UploadedDocument[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<string | undefined>(undefined);

  useEffect(() => {
    fetchDocuments()
      .then((stored) => {
        if (stored.length) {
          const docs: UploadedDocument[] = stored.map((d) => ({
            doc_id: d.doc_id, filename: d.filename, description: d.description,
            pages: d.pages, chunks: d.chunks, parser_used: d.parser_used,
            uploadedAt: new Date(d.uploaded_at),
          }));
          setDocuments(docs);
          setSelectedDoc(docs[docs.length - 1].doc_id);
        }
      })
      .catch(() => {});
  }, []);

  const handleUploaded = (doc: UploadedDocument) => {
    setDocuments((prev) => [...prev.filter((d) => d.doc_id !== doc.doc_id), doc]);
    setSelectedDoc(doc.doc_id);
  };

  const handleRemove = (docId: string) => {
    setDocuments((prev) => {
      const next = prev.filter((d) => d.doc_id !== docId);
      if (selectedDoc === docId) setSelectedDoc(next[next.length - 1]?.doc_id);
      return next;
    });
  };

  const activeDocId = selectedDoc ?? documents[documents.length - 1]?.doc_id;

  return (
    <div className="flex gap-6">
      {/* Tab sidebar */}
      <aside className="hidden md:flex flex-col gap-1 w-44 shrink-0">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={clsx(
                "flex items-center gap-2 px-3 py-2.5 rounded-xl text-left transition-all",
                isActive ? "bg-gray-800 border border-gray-700 text-white" : "hover:bg-gray-900 text-gray-400"
              )}
            >
              <Icon className={clsx("h-4 w-4 shrink-0", isActive ? tab.color : "text-gray-500")} />
              <div>
                <p className="text-xs font-semibold">{tab.label}</p>
                <p className="text-[9px] text-gray-600">{tab.desc}</p>
              </div>
              {isActive && <ChevronRight className="h-3 w-3 text-gray-500 ml-auto" />}
            </button>
          );
        })}

        {documents.length > 1 && (
          <div className="mt-3 pt-3 border-t border-gray-800">
            <p className="text-[10px] text-gray-500 uppercase tracking-widest px-2 mb-1">Context</p>
            {documents.slice(-5).map((doc) => (
              <button
                key={doc.doc_id}
                onClick={() => setSelectedDoc(doc.doc_id)}
                className={clsx(
                  "w-full flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-left text-xs transition-colors",
                  selectedDoc === doc.doc_id ? "bg-gray-800 text-gray-200" : "text-gray-500 hover:text-gray-300"
                )}
              >
                <FileText className="h-3 w-3 shrink-0" />
                <span className="truncate">{doc.filename}</span>
              </button>
            ))}
          </div>
        )}
      </aside>

      {/* Content */}
      <main className="flex-1 min-w-0">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
            className="bg-gray-900 border border-gray-800 rounded-2xl p-6 min-h-[500px]"
          >
            {activeTab === "upload" && (
              <FileUpload onUploaded={handleUploaded} documents={documents} onRemove={handleRemove} />
            )}
            {activeTab === "explain" && <ExplainModule docId={activeDocId} />}
            {activeTab === "quiz" && <QuizGame docId={activeDocId} />}
            {activeTab === "planner" && <RevisionPlanner docId={activeDocId} />}
            {activeTab === "doubt" && <DoubtSolver docId={activeDocId} />}
            {activeTab === "feynman" && <FeynmanMode docId={activeDocId} />}
            {activeTab === "flashcards" && <Flashcards docId={activeDocId} />}
            {activeTab === "progress" && <ProgressDashboard />}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}
