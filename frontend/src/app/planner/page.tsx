"use client";
import { Suspense } from "react";
import { motion } from "framer-motion";
import { GraduationCap, ArrowLeft, FileText, CalendarDays } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { RevisionPlanner } from "@/components/features/RevisionPlanner";
import { Spinner } from "@/components/ui";

/**
 * /planner — Standalone full-page revision planner.
 *
 * URL params:
 *   ?doc_id=<uuid>   — pre-selects a document for auto-topic extraction
 */
function PlannerPageInner() {
  const params = useSearchParams();
  const docId  = params.get("doc_id") ?? undefined;

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      {/* Nav */}
      <header className="sticky top-0 z-50 border-b border-gray-800/80 bg-gray-950/80 backdrop-blur-xl">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-3 flex items-center gap-4">
          <Link
            href="/"
            className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors group"
          >
            <ArrowLeft className="h-4 w-4 group-hover:-translate-x-0.5 transition-transform" />
            <span className="text-sm">Back</span>
          </Link>

          <div className="flex items-center gap-2 flex-1 justify-center">
            <div className="h-7 w-7 rounded-lg bg-brand-600 flex items-center justify-center">
              <GraduationCap className="h-4 w-4 text-white" />
            </div>
            <span className="font-bold text-white text-sm">StudyBuddy</span>
            <span className="text-xs text-emerald-400 font-semibold">Planner</span>
          </div>

          {docId ? (
            <div className="flex items-center gap-1.5 text-xs text-gray-500 bg-gray-900 border border-gray-700 px-2.5 py-1 rounded-full">
              <FileText className="h-3 w-3" />
              doc context
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-xs text-gray-500 bg-gray-900 border border-gray-700 px-2.5 py-1 rounded-full">
              <CalendarDays className="h-3 w-3" />
              planner
            </div>
          )}
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 max-w-4xl mx-auto w-full px-4 sm:px-6 py-8">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
          className="glass-card p-6 sm:p-8"
        >
          <RevisionPlanner docId={docId} />
        </motion.div>
      </main>
    </div>
  );
}

export default function PlannerPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-gray-950 flex items-center justify-center">
          <Spinner size="lg" />
        </div>
      }
    >
      <PlannerPageInner />
    </Suspense>
  );
}
