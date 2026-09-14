"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { FileText, Upload, Download, Search, X } from "lucide-react";
import toast from "react-hot-toast";

interface Note {
  id: string;
  title: string;
  description: string;
  subject: string;
  course: string;
  semester: string;
  tags: string;
  file_url: string;
  original_filename: string;
  uploaded_by: string;
  uploader_name: string;
  visibility: string;
  created_at: string;
}

export default function NotesPage() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showUpload, setShowUpload] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", subject: "", course: "", semester: "", tags: "", visibility: "connections" });
  const [file, setFile] = useState<File | null>(null);
  const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const load = (q?: string) => {
    const params = q ? `?search=${encodeURIComponent(q)}` : "";
    api.get(`/api/notes${params}`, { withCredentials: true })
      .then(r => setNotes(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) { toast.error("Please select a file"); return; }
    setUploading(true);
    try {
      const fd = new FormData();
      Object.entries(form).forEach(([k, v]) => fd.append(k, v));
      fd.append("file", file);
      await api.post("/api/notes", fd, { withCredentials: true, headers: { "Content-Type": "multipart/form-data" } });
      toast.success("Note uploaded!");
      setShowUpload(false);
      setFile(null);
      setForm({ title: "", description: "", subject: "", course: "", semester: "", tags: "", visibility: "connections" });
      load();
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const deleteNote = async (id: string) => {
    if (!confirm("Delete this note?")) return;
    try {
      await api.delete(`/api/notes/${id}`, { withCredentials: true });
      setNotes(n => n.filter(x => x.id !== id));
      toast.success("Note deleted");
    } catch { toast.error("Could not delete"); }
  };

  const inp = "w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-xl text-white text-sm focus:outline-none focus:border-blue-500";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white flex items-center gap-2"><FileText className="w-6 h-6 text-yellow-400" />Notes</h1>
        <button onClick={() => setShowUpload(true)} className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-xl">
          <Upload className="w-4 h-4" />Upload Note
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-500" />
        <input value={search} onChange={e => { setSearch(e.target.value); if (!e.target.value) load(); }}
          onKeyDown={e => e.key === "Enter" && load(search)}
          placeholder="Search notes by title or tags..." className={`${inp} pl-10`} />
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" /></div>
      ) : notes.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-12 text-center">
          <FileText className="w-12 h-12 text-gray-700 mx-auto mb-4" />
          <p className="text-gray-400">No notes found</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {notes.map(n => (
            <div key={n.id} className="bg-gray-900 border border-gray-800 rounded-2xl p-5 hover:border-gray-700 transition-colors">
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-semibold text-white truncate flex-1">{n.title}</h3>
                <button onClick={() => deleteNote(n.id)} className="text-gray-600 hover:text-red-400 ml-2 shrink-0"><X className="w-4 h-4" /></button>
              </div>
              {n.description && <p className="text-gray-400 text-xs mb-2 line-clamp-2">{n.description}</p>}
              <div className="flex flex-wrap gap-1 mb-3">
                {n.subject && <span className="bg-blue-500/20 text-blue-400 text-xs px-2 py-0.5 rounded-full">{n.subject}</span>}
                {n.semester && <span className="bg-purple-500/20 text-purple-400 text-xs px-2 py-0.5 rounded-full">Sem {n.semester}</span>}
                {n.tags && n.tags.split(",").map((t, i) => <span key={i} className="bg-gray-700 text-gray-400 text-xs px-2 py-0.5 rounded-full">{t.trim()}</span>)}
              </div>
              <div className="flex items-center justify-between">
                <p className="text-xs text-gray-500">By {n.uploader_name}</p>
                <a href={`${BASE}/api/notes/${n.id}/download`} className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300">
                  <Download className="w-3 h-3" />Download
                </a>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Upload modal */}
      {showUpload && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-bold text-white mb-4">Upload Note</h2>
            <form onSubmit={handleUpload} className="space-y-3">
              <input required placeholder="Title *" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} className={inp} />
              <textarea placeholder="Description" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} rows={2} className={inp} />
              <div className="grid grid-cols-2 gap-3">
                <input placeholder="Subject" value={form.subject} onChange={e => setForm(f => ({ ...f, subject: e.target.value }))} className={inp} />
                <input placeholder="Course" value={form.course} onChange={e => setForm(f => ({ ...f, course: e.target.value }))} className={inp} />
                <input placeholder="Semester" value={form.semester} onChange={e => setForm(f => ({ ...f, semester: e.target.value }))} className={inp} />
                <input placeholder="Tags (comma separated)" value={form.tags} onChange={e => setForm(f => ({ ...f, tags: e.target.value }))} className={inp} />
              </div>
              <select value={form.visibility} onChange={e => setForm(f => ({ ...f, visibility: e.target.value }))} className={inp}>
                <option value="connections">My Connections only</option>
                <option value="class">My Class</option>
                <option value="public">All Students</option>
              </select>
              <input type="file" required onChange={e => setFile(e.target.files?.[0] || null)} className="w-full text-sm text-gray-300 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-blue-600 file:text-white" />
              <div className="flex gap-3 justify-end pt-2">
                <button type="button" onClick={() => setShowUpload(false)} className="px-4 py-2 text-sm text-gray-400 hover:text-white">Cancel</button>
                <button type="submit" disabled={uploading} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm rounded-xl">
                  {uploading ? "Uploading..." : "Upload"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
