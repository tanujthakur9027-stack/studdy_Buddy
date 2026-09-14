"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ClipboardList, Plus, Send, Trash } from "lucide-react";
import toast from "react-hot-toast";

interface Assignment {
  id: string; title: string; subject_id: string; class_id: string;
  due_date: string; max_marks: number; is_published: boolean; created_at: string;
}
interface Subject { id: string; name: string; class_id: string; }
interface Class { id: string; name: string; }

export default function AdminAssignmentsPage() {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [classes, setClasses] = useState<Class[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: "", subject_id: "", class_id: "", section_id: "", description: "", instructions: "", due_date: "", due_time: "23:59", max_marks: "100" });
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.get("/api/admin/assignments", { withCredentials: true }).then(r => setAssignments(r.data)).catch(() => {});
    api.get("/api/admin/subjects", { withCredentials: true }).then(r => setSubjects(r.data)).catch(() => {});
    api.get("/api/admin/classes", { withCredentials: true }).then(r => setClasses(r.data)).catch(() => {});
  }, []);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const fd = new FormData();
      Object.entries(form).forEach(([k, v]) => { if (v) fd.append(k, v); });
      if (file) fd.append("file", file);
      const r = await api.post("/api/admin/assignments", fd, { withCredentials: true, headers: { "Content-Type": "multipart/form-data" } });
      setAssignments(a => [r.data, ...a]);
      setShowForm(false);
      toast.success("Assignment created!");
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed");
    } finally { setSubmitting(false); }
  };

  const publish = async (id: string) => {
    try {
      const r = await api.post(`/api/admin/assignments/${id}/publish`, {}, { withCredentials: true });
      setAssignments(a => a.map(x => x.id === id ? { ...x, is_published: true } : x));
      toast.success(r.data.message);
    } catch { toast.error("Failed to publish"); }
  };

  const del = async (id: string) => {
    if (!confirm("Delete this assignment?")) return;
    try {
      await api.delete(`/api/admin/assignments/${id}`, { withCredentials: true });
      setAssignments(a => a.filter(x => x.id !== id));
      toast.success("Deleted");
    } catch { toast.error("Failed"); }
  };

  const inp = "w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-xl text-white text-sm focus:outline-none focus:border-blue-500";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white flex items-center gap-2"><ClipboardList className="w-6 h-6 text-purple-400" />Assignments</h1>
        <button onClick={() => setShowForm(true)} className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-xl">
          <Plus className="w-4 h-4" />Create Assignment
        </button>
      </div>

      <div className="space-y-3">
        {assignments.length === 0 ? (
          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-12 text-center">
            <ClipboardList className="w-12 h-12 text-gray-700 mx-auto mb-4" />
            <p className="text-gray-400">No assignments yet</p>
          </div>
        ) : assignments.map(a => (
          <div key={a.id} className="bg-gray-900 border border-gray-800 rounded-2xl p-5 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3">
                <h3 className="font-semibold text-white">{a.title}</h3>
                <span className={`text-xs px-2 py-0.5 rounded-full ${a.is_published ? "bg-green-500/20 text-green-400" : "bg-yellow-500/20 text-yellow-400"}`}>
                  {a.is_published ? "Published" : "Draft"}
                </span>
              </div>
              <p className="text-xs text-gray-500 mt-1">Due: {a.due_date} • Max: {a.max_marks} marks</p>
            </div>
            <div className="flex items-center gap-2">
              {!a.is_published && (
                <button onClick={() => publish(a.id)} className="flex items-center gap-1 text-xs bg-green-600 hover:bg-green-700 text-white px-3 py-1.5 rounded-lg">
                  <Send className="w-3 h-3" />Publish
                </button>
              )}
              <button onClick={() => del(a.id)} className="p-1.5 text-gray-500 hover:text-red-400"><Trash className="w-4 h-4" /></button>
            </div>
          </div>
        ))}
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-bold text-white mb-4">Create Assignment</h2>
            <form onSubmit={create} className="space-y-3">
              <input required placeholder="Title *" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} className={inp} />
              <div className="grid grid-cols-2 gap-3">
                <select required value={form.class_id} onChange={e => setForm(f => ({ ...f, class_id: e.target.value }))} className={inp}>
                  <option value="">Select Class *</option>
                  {classes.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
                <select required value={form.subject_id} onChange={e => setForm(f => ({ ...f, subject_id: e.target.value }))} className={inp}>
                  <option value="">Select Subject *</option>
                  {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
                <input type="date" required placeholder="Due Date *" value={form.due_date} onChange={e => setForm(f => ({ ...f, due_date: e.target.value }))} className={inp} />
                <input type="time" value={form.due_time} onChange={e => setForm(f => ({ ...f, due_time: e.target.value }))} className={inp} />
                <input type="number" placeholder="Max Marks" value={form.max_marks} onChange={e => setForm(f => ({ ...f, max_marks: e.target.value }))} className={inp} />
              </div>
              <textarea placeholder="Description" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} rows={2} className={inp} />
              <textarea placeholder="Instructions" value={form.instructions} onChange={e => setForm(f => ({ ...f, instructions: e.target.value }))} rows={2} className={inp} />
              <input type="file" onChange={e => setFile(e.target.files?.[0] || null)} className="w-full text-sm text-gray-300 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-blue-600 file:text-white" />
              <div className="flex gap-3 justify-end pt-2">
                <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 text-sm text-gray-400 hover:text-white">Cancel</button>
                <button type="submit" disabled={submitting} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm rounded-xl">
                  {submitting ? "Creating..." : "Create Assignment"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
