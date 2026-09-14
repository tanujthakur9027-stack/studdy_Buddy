"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { CheckCircle, Clock, Download, Star, X } from "lucide-react";
import toast from "react-hot-toast";

interface Assignment { id: string; title: string; max_marks: number; subject_id: string; }
interface Submission {
  id: string;
  assignment_id: string;
  student_id: string;
  student_name: string;
  student_email: string;
  file_url: string | null;
  notes: string;
  submitted_at: string;
  marks_obtained: number | null;
  feedback: string;
  is_evaluated: boolean;
  status: string;
}

export default function AdminSubmissionsPage() {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [selectedAssignment, setSelectedAssignment] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [grading, setGrading] = useState<Submission | null>(null);
  const [gradeForm, setGradeForm] = useState({ marks_obtained: "", feedback: "" });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.get("/api/admin/assignments", { withCredentials: true })
      .then(r => setAssignments(r.data))
      .catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    const params: Record<string, string> = {};
    if (selectedAssignment) params.assignment_id = selectedAssignment;
    if (statusFilter) params.status = statusFilter;
    api.get("/api/admin/submissions", { params, withCredentials: true })
      .then(r => setSubmissions(r.data))
      .catch(() => toast.error("Failed to load submissions"))
      .finally(() => setLoading(false));
  }, [selectedAssignment, statusFilter]);

  const openGrade = (sub: Submission) => {
    setGrading(sub);
    setGradeForm({
      marks_obtained: sub.marks_obtained != null ? String(sub.marks_obtained) : "",
      feedback: sub.feedback || "",
    });
  };

  const submitGrade = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!grading) return;
    setSubmitting(true);
    try {
      const r = await api.patch(`/api/admin/submissions/${grading.id}/grade`, {
        marks_obtained: parseFloat(gradeForm.marks_obtained),
        feedback: gradeForm.feedback,
      }, { withCredentials: true });
      toast.success(r.data.message || "Graded!");
      setSubmissions(s => s.map(x => x.id === grading.id ? {
        ...x,
        marks_obtained: parseFloat(gradeForm.marks_obtained),
        feedback: gradeForm.feedback,
        is_evaluated: true,
        status: "evaluated",
      } : x));
      setGrading(null);
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed");
    } finally { setSubmitting(false); }
  };

  const maxMarks = selectedAssignment
    ? assignments.find(a => a.id === selectedAssignment)?.max_marks
    : undefined;

  const inp = "w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-xl text-white text-sm focus:outline-none focus:border-blue-500";

  const statusBadge = (status: string) => {
    const map: Record<string, string> = {
      submitted: "bg-blue-500/20 text-blue-400",
      evaluated: "bg-green-500/20 text-green-400",
      late: "bg-yellow-500/20 text-yellow-400",
    };
    return map[status] || "bg-gray-700 text-gray-400";
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white flex items-center gap-2">
        <CheckCircle className="w-6 h-6 text-green-400" />Submissions
      </h1>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={selectedAssignment}
          onChange={e => setSelectedAssignment(e.target.value)}
          className="px-3 py-2 bg-gray-900 border border-gray-700 rounded-xl text-white text-sm focus:outline-none focus:border-blue-500"
        >
          <option value="">All Assignments</option>
          {assignments.map(a => <option key={a.id} value={a.id}>{a.title}</option>)}
        </select>
        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          className="px-3 py-2 bg-gray-900 border border-gray-700 rounded-xl text-white text-sm focus:outline-none focus:border-blue-500"
        >
          <option value="">All Statuses</option>
          <option value="submitted">Submitted</option>
          <option value="evaluated">Evaluated</option>
          <option value="late">Late</option>
        </select>
        <span className="px-3 py-2 text-sm text-gray-400">{submissions.length} submission{submissions.length !== 1 ? "s" : ""}</span>
      </div>

      {/* Table */}
      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading...</div>
      ) : submissions.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-12 text-center">
          <CheckCircle className="w-12 h-12 text-gray-700 mx-auto mb-4" />
          <p className="text-gray-400">No submissions found</p>
        </div>
      ) : (
        <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-left text-xs text-gray-400 px-5 py-3 font-medium">Student</th>
                  <th className="text-left text-xs text-gray-400 px-5 py-3 font-medium">Submitted</th>
                  <th className="text-left text-xs text-gray-400 px-5 py-3 font-medium">Status</th>
                  <th className="text-left text-xs text-gray-400 px-5 py-3 font-medium">Marks</th>
                  <th className="text-left text-xs text-gray-400 px-5 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {submissions.map((sub, i) => (
                  <tr key={sub.id} className={`border-b border-gray-800/50 hover:bg-gray-800/30 ${i % 2 === 0 ? "" : "bg-gray-800/10"}`}>
                    <td className="px-5 py-3">
                      <p className="text-sm text-white font-medium">{sub.student_name}</p>
                      <p className="text-xs text-gray-500">{sub.student_email}</p>
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-1 text-xs text-gray-400">
                        <Clock className="w-3 h-3" />
                        {new Date(sub.submitted_at).toLocaleDateString()}
                      </div>
                    </td>
                    <td className="px-5 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${statusBadge(sub.status)}`}>
                        {sub.status}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-sm text-white">
                      {sub.is_evaluated ? `${sub.marks_obtained} / ${maxMarks ?? "?"}` : <span className="text-gray-500">—</span>}
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2">
                        {sub.file_url && (
                          <a
                            href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}${sub.file_url}`}
                            target="_blank"
                            rel="noreferrer"
                            className="p-1.5 text-gray-500 hover:text-blue-400 transition-colors"
                            title="Download"
                          >
                            <Download className="w-4 h-4" />
                          </a>
                        )}
                        <button
                          onClick={() => openGrade(sub)}
                          className="flex items-center gap-1 text-xs bg-purple-600 hover:bg-purple-700 text-white px-3 py-1.5 rounded-lg transition-colors"
                        >
                          <Star className="w-3 h-3" />
                          {sub.is_evaluated ? "Re-grade" : "Grade"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Grade Modal */}
      {grading && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-white">Grade Submission</h2>
              <button onClick={() => setGrading(null)} className="text-gray-500 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="mb-4 p-3 bg-gray-800 rounded-xl">
              <p className="text-sm text-white font-medium">{grading.student_name}</p>
              <p className="text-xs text-gray-400 mt-1">{grading.notes || "No notes attached"}</p>
            </div>
            <form onSubmit={submitGrade} className="space-y-3">
              <div>
                <label className="text-xs text-gray-400 mb-1 block">
                  Marks Obtained {maxMarks ? `(max: ${maxMarks})` : ""}
                </label>
                <input
                  type="number"
                  required
                  step="0.5"
                  min="0"
                  max={maxMarks}
                  value={gradeForm.marks_obtained}
                  onChange={e => setGradeForm(f => ({ ...f, marks_obtained: e.target.value }))}
                  className={inp}
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Feedback / Comments</label>
                <textarea
                  value={gradeForm.feedback}
                  onChange={e => setGradeForm(f => ({ ...f, feedback: e.target.value }))}
                  rows={3}
                  placeholder="Optional feedback for the student..."
                  className={inp}
                />
              </div>
              <div className="flex gap-3 justify-end pt-2">
                <button type="button" onClick={() => setGrading(null)} className="px-4 py-2 text-sm text-gray-400 hover:text-white">
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white text-sm rounded-xl"
                >
                  {submitting ? "Saving..." : "Save Grade"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
