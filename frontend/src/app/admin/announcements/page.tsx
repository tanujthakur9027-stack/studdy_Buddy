"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Megaphone, Plus, Trash, X } from "lucide-react";
import toast from "react-hot-toast";

interface Class { id: string; name: string; }
interface Announcement {
  id: string; title: string; content: string;
  created_by: string; author_name: string;
  class_id: string | null; section_id: string | null;
  created_at: string;
}

export default function AdminAnnouncementsPage() {
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [classes, setClasses] = useState<Class[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: "", content: "", class_id: "" });
  const [submitting, setSubmitting] = useState(false);
  const [editing, setEditing] = useState<Announcement | null>(null);

  const inp = "w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-xl text-white text-sm focus:outline-none focus:border-blue-500";

  useEffect(() => {
    api.get("/api/admin/announcements", { withCredentials: true })
      .then(r => setAnnouncements(r.data))
      .catch(() => {});
    api.get("/api/admin/classes", { withCredentials: true })
      .then(r => setClasses(r.data))
      .catch(() => {});
  }, []);

  const openCreate = () => {
    setEditing(null);
    setForm({ title: "", content: "", class_id: "" });
    setShowForm(true);
  };

  const openEdit = (ann: Announcement) => {
    setEditing(ann);
    setForm({ title: ann.title, content: ann.content, class_id: ann.class_id || "" });
    setShowForm(true);
  };

  const submitForm = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    const payload = {
      title: form.title,
      content: form.content,
      class_id: form.class_id || null,
      section_id: null,
    };
    try {
      if (editing) {
        const r = await api.patch(`/api/admin/announcements/${editing.id}`, payload, { withCredentials: true });
        setAnnouncements(a => a.map(x => x.id === editing.id ? r.data : x));
        toast.success("Announcement updated!");
      } else {
        const r = await api.post("/api/admin/announcements", payload, { withCredentials: true });
        setAnnouncements(a => [r.data, ...a]);
        toast.success("Announcement posted!");
      }
      setShowForm(false);
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed");
    } finally { setSubmitting(false); }
  };

  const deleteAnnouncement = async (id: string) => {
    if (!confirm("Delete this announcement?")) return;
    try {
      await api.delete(`/api/admin/announcements/${id}`, { withCredentials: true });
      setAnnouncements(a => a.filter(x => x.id !== id));
      toast.success("Deleted");
    } catch { toast.error("Failed"); }
  };

  const className = (classId: string | null) =>
    classId ? classes.find(c => c.id === classId)?.name || "Unknown" : null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Megaphone className="w-6 h-6 text-orange-400" />Announcements
        </h1>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white text-sm rounded-xl"
        >
          <Plus className="w-4 h-4" />New Announcement
        </button>
      </div>

      {announcements.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-12 text-center">
          <Megaphone className="w-12 h-12 text-gray-700 mx-auto mb-4" />
          <p className="text-gray-400">No announcements yet</p>
        </div>
      ) : (
        <div className="space-y-4">
          {announcements.map(ann => (
            <div
              key={ann.id}
              className="bg-gray-900 border border-gray-800 rounded-2xl p-5 hover:border-gray-700 transition-colors"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 flex-wrap">
                    <h3 className="font-semibold text-white">{ann.title}</h3>
                    {ann.class_id ? (
                      <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded-full">
                        {className(ann.class_id)}
                      </span>
                    ) : (
                      <span className="text-xs bg-orange-500/20 text-orange-400 px-2 py-0.5 rounded-full">
                        All Students
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-300 mt-2 leading-relaxed">{ann.content}</p>
                  <div className="flex items-center gap-4 mt-3">
                    <span className="text-xs text-gray-500">By {ann.author_name}</span>
                    <span className="text-xs text-gray-600">
                      {new Date(ann.created_at).toLocaleDateString("en-US", {
                        year: "numeric", month: "short", day: "numeric",
                        hour: "2-digit", minute: "2-digit",
                      })}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => openEdit(ann)}
                    className="px-3 py-1.5 text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg transition-colors"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => deleteAnnouncement(ann.id)}
                    className="p-1.5 text-gray-500 hover:text-red-400 transition-colors"
                  >
                    <Trash className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create / Edit Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full max-w-lg">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-white">
                {editing ? "Edit Announcement" : "New Announcement"}
              </h2>
              <button onClick={() => setShowForm(false)} className="text-gray-500 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={submitForm} className="space-y-3">
              <input
                required
                placeholder="Title *"
                value={form.title}
                onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                className={inp}
              />
              <textarea
                required
                placeholder="Announcement content *"
                value={form.content}
                onChange={e => setForm(f => ({ ...f, content: e.target.value }))}
                rows={5}
                className={inp}
              />
              <div>
                <label className="text-xs text-gray-400 block mb-1">Target Audience</label>
                <select
                  value={form.class_id}
                  onChange={e => setForm(f => ({ ...f, class_id: e.target.value }))}
                  className={inp}
                >
                  <option value="">All Students (Broadcast)</option>
                  {classes.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div className="flex gap-3 justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="px-4 py-2 text-sm text-gray-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-white text-sm rounded-xl"
                >
                  {submitting ? "Posting..." : editing ? "Update" : "Post Announcement"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
