"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ClipboardList, Download, Upload, Clock } from "lucide-react";
import toast from "react-hot-toast";

interface Assignment {
  id: string;
  title: string;
  subject_id: string;
  description: string;
  instructions: string;
  file_url?: string;
  due_date: string;
  due_time: string;
  max_marks: number;
  submission_status?: string;
}

export default function AssignmentsPage() {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Assignment | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [notes, setNotes] = useState("");
  const [filter, setFilter] = useState<"all" | "pending" | "submitted" | "evaluated">("all");

  useEffect(() => {
    api.get("/api/assignments", { withCredentials: true })
      .then(r => setAssignments(r.data))
      .catch(() => toast.error("Failed to load assignments"))
      .finally(() => setLoading(false));
  }, []);

  const filtered = filter === "all" ? assignments
    : filter === "pending" ? assignments.filter(a => !a.submission_status)
    : assignments.filter(a => a.submission_status === filter);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selected) return;
    setSubmitting(true);
    try {
      const form = new FormData();
      form.append("notes", notes);
      if (file) form.append("file", file);
      await api.post(`/api/assignments/${selected.id}/submit`, form, {
        withCredentials: true,
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success("Assignment submitted!");
      setAssignments(a => a.map(x => x.id === selected.id ? { ...x, submission_status: "submitted" } : x));
      setSelected(null);
      setFile(null);
      setNotes("");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Submission failed";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const statusColor = (s?: string) => {
    if (!s) return "bg-orange-500/20 text-orange-400";
    if (s === "evaluated") return "bg-green-500/20 text-green-400";
    if (s === "submitted") return "bg-blue-500/20 text-blue-400";
    if (s === "late") return "bg-red-500/20 text-red-400";
    return "bg-gray-500/20 text-gray-400";
  };

  const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white flex items-center gap-2"><ClipboardList className="w-6 h-6 text-orange-400" />Assignments</h1>

      {/* Filter tabs */}
      <div className="flex gap-2">
        {(["all", "pending", "submitted", "evaluated"] as const).map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors capitalize ${filter === f ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-400 hover:text-white"}`}>
            {f}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" /></div>
      ) : filtered.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-12 text-center">
          <ClipboardList className="w-12 h-12 text-gray-700 mx-auto mb-4" />
          <p className="text-gray-400">No {filter} assignments</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {filtered.map((a) => (
            <div key={a.id} className="bg-gray-900 border border-gray-800 rounded-2xl p-5 hover:border-gray-700 transition-colors">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-1">
                    <h3 className="font-semibold text-white">{a.title}</h3>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(a.submission_status)}`}>
                      {a.submission_status || "Pending"}
                    </span>
                  </div>
                  <p className="text-gray-400 text-sm line-clamp-2">{a.description}</p>
                  <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                    <span className="flex items-center gap-1"><Clock className="w-3 h-3" />Due: {a.due_date} {a.due_time}</span>
                    <span>Max: {a.max_marks} marks</span>
                  </div>
                </div>
                <div className="flex flex-col gap-2 ml-4">
                  {a.file_url && (
                    <a href={`${BASE}${a.file_url}`} target="_blank" rel="noopener noreferrer"
                      className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300">
                      <Download className="w-3 h-3" /> Download
                    </a>
                  )}
                  {!a.submission_status && (
                    <button onClick={() => setSelected(a)}
                      className="flex items-center gap-1 text-xs bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg">
                      <Upload className="w-3 h-3" /> Submit
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Submit modal */}
      {selected && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full max-w-lg">
            <h2 className="text-lg font-bold text-white mb-1">Submit: {selected.title}</h2>
            <p className="text-gray-400 text-sm mb-4">{selected.instructions}</p>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm text-gray-300 mb-1">Attach File</label>
                <input type="file" onChange={e => setFile(e.target.files?.[0] || null)}
                  className="w-full text-sm text-gray-300 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-blue-600 file:text-white hover:file:bg-blue-700" />
              </div>
              <div>
                <label className="block text-sm text-gray-300 mb-1">Notes (optional)</label>
                <textarea value={notes} onChange={e => setNotes(e.target.value)}
                  rows={3} placeholder="Any comments..."
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-xl text-white text-sm focus:outline-none focus:border-blue-500" />
              </div>
              <div className="flex gap-3 justify-end">
                <button type="button" onClick={() => setSelected(null)} className="px-4 py-2 text-sm text-gray-400 hover:text-white">Cancel</button>
                <button type="submit" disabled={submitting} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm rounded-xl">
                  {submitting ? "Submitting..." : "Submit Assignment"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
