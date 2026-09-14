"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { BarChart2 } from "lucide-react";

interface SubjectSummary {
  subject_id: string;
  subject_name: string;
  total_obtained: number;
  total_max: number;
  percentage: number;
  grade: string;
  categories: { category_name: string; obtained: number; max_marks: number; percentage: number; remarks: string }[];
}

interface MarksSummary {
  subjects: SubjectSummary[];
  overall_obtained: number;
  overall_max: number;
  overall_percentage: number;
  overall_grade: string;
}

const gradeColor = (g: string) => {
  if (g === "S" || g === "A") return "text-green-400";
  if (g === "B" || g === "C") return "text-yellow-400";
  return "text-red-400";
};

export default function MarksPage() {
  const [summary, setSummary] = useState<MarksSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    api.get("/api/marks/summary", { withCredentials: true })
      .then(r => setSummary(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex justify-center py-12"><div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" /></div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white flex items-center gap-2"><BarChart2 className="w-6 h-6 text-green-400" />Marks</h1>

      {!summary || summary.subjects.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-12 text-center">
          <BarChart2 className="w-12 h-12 text-gray-700 mx-auto mb-4" />
          <p className="text-gray-400">No marks published yet</p>
        </div>
      ) : (
        <>
          {/* Overall summary */}
          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Overall Performance</h2>
            <div className="flex items-center gap-8">
              <div className="text-center">
                <div className={`text-5xl font-black ${gradeColor(summary.overall_grade)}`}>{summary.overall_grade}</div>
                <p className="text-gray-400 text-sm mt-1">Grade</p>
              </div>
              <div>
                <div className="text-3xl font-bold text-white">{summary.overall_percentage}%</div>
                <p className="text-gray-400 text-sm">{summary.overall_obtained} / {summary.overall_max} marks</p>
                <div className="w-48 h-2 bg-gray-700 rounded-full mt-2">
                  <div className="h-2 bg-blue-500 rounded-full" style={{ width: `${summary.overall_percentage}%` }} />
                </div>
              </div>
            </div>
          </div>

          {/* Subject breakdown */}
          {summary.subjects.map((s) => (
            <div key={s.subject_id} className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
              <button
                onClick={() => setExpanded(expanded === s.subject_id ? null : s.subject_id)}
                className="w-full flex items-center justify-between p-5 hover:bg-gray-800/50 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className={`text-2xl font-bold ${gradeColor(s.grade)}`}>{s.grade}</div>
                  <div className="text-left">
                    <p className="font-semibold text-white">{s.subject_name}</p>
                    <p className="text-sm text-gray-400">{s.total_obtained} / {s.total_max} marks • {s.percentage}%</p>
                  </div>
                </div>
                <div className="text-gray-500">{expanded === s.subject_id ? "▲" : "▼"}</div>
              </button>

              {expanded === s.subject_id && (
                <div className="px-5 pb-5 border-t border-gray-800">
                  <div className="mt-4 space-y-2">
                    {s.categories.map((c, i) => (
                      <div key={i} className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0">
                        <div>
                          <p className="text-sm text-white">{c.category_name}</p>
                          {c.remarks && <p className="text-xs text-gray-500 mt-0.5">{c.remarks}</p>}
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-semibold text-white">{c.obtained} / {c.max_marks}</p>
                          <p className="text-xs text-gray-400">{c.percentage}%</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </>
      )}
    </div>
  );
}
