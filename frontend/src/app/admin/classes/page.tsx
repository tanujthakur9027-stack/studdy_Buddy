"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { BookOpen, ChevronDown, ChevronRight, Plus, Trash } from "lucide-react";
import toast from "react-hot-toast";

interface Class { id: string; name: string; course: string; created_at: string; }
interface Section { id: string; name: string; class_id: string; }
interface Subject { id: string; name: string; code: string; class_id: string; }

export default function AdminClassesPage() {
  const [classes, setClasses] = useState<Class[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);

  // Create forms
  const [classForm, setClassForm] = useState({ name: "", course: "" });
  const [sectionForm, setSectionForm] = useState({ name: "", class_id: "" });
  const [subjectForm, setSubjectForm] = useState({ name: "", code: "", class_id: "" });

  const [showClassForm, setShowClassForm] = useState(false);
  const [showSectionForm, setShowSectionForm] = useState(false);
  const [showSubjectForm, setShowSubjectForm] = useState(false);

  const inp = "w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-xl text-white text-sm focus:outline-none focus:border-blue-500";

  const load = () => {
    api.get("/api/admin/classes", { withCredentials: true }).then(r => setClasses(r.data)).catch(() => {});
    api.get("/api/admin/sections", { withCredentials: true }).then(r => setSections(r.data)).catch(() => {});
    api.get("/api/admin/subjects", { withCredentials: true }).then(r => setSubjects(r.data)).catch(() => {});
  };

  useEffect(() => { load(); }, []);

  // ── Classes ────────────────────────────────────────────────────────────────
  const createClass = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const r = await api.post("/api/admin/classes", classForm, { withCredentials: true });
      setClasses(c => [...c, r.data]);
      setClassForm({ name: "", course: "" });
      setShowClassForm(false);
      toast.success("Class created!");
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed");
    }
  };

  const deleteClass = async (id: string) => {
    if (!confirm("Delete this class? This will also delete its sections and subjects.")) return;
    try {
      await api.delete(`/api/admin/classes/${id}`, { withCredentials: true });
      setClasses(c => c.filter(x => x.id !== id));
      setSections(s => s.filter(x => x.class_id !== id));
      setSubjects(s => s.filter(x => x.class_id !== id));
      toast.success("Deleted");
    } catch { toast.error("Failed"); }
  };

  // ── Sections ───────────────────────────────────────────────────────────────
  const createSection = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const r = await api.post("/api/admin/sections", sectionForm, { withCredentials: true });
      setSections(s => [...s, r.data]);
      setSectionForm(f => ({ ...f, name: "" }));
      setShowSectionForm(false);
      toast.success("Section created!");
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed");
    }
  };

  const deleteSection = async (id: string) => {
    if (!confirm("Delete this section?")) return;
    try {
      await api.delete(`/api/admin/sections/${id}`, { withCredentials: true });
      setSections(s => s.filter(x => x.id !== id));
      toast.success("Deleted");
    } catch { toast.error("Failed"); }
  };

  // ── Subjects ───────────────────────────────────────────────────────────────
  const createSubject = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const r = await api.post("/api/admin/subjects", subjectForm, { withCredentials: true });
      setSubjects(s => [...s, r.data]);
      setSubjectForm(f => ({ ...f, name: "", code: "" }));
      setShowSubjectForm(false);
      toast.success("Subject created!");
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed");
    }
  };

  const deleteSubject = async (id: string) => {
    if (!confirm("Delete this subject?")) return;
    try {
      await api.delete(`/api/admin/subjects/${id}`, { withCredentials: true });
      setSubjects(s => s.filter(x => x.id !== id));
      toast.success("Deleted");
    } catch { toast.error("Failed"); }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <BookOpen className="w-6 h-6 text-blue-400" />Classes, Sections & Subjects
        </h1>
      </div>

      {/* ── Quick Create Buttons ──────────────────────────────────────────── */}
      <div className="flex flex-wrap gap-3">
        <button
          onClick={() => setShowClassForm(v => !v)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-xl"
        >
          <Plus className="w-4 h-4" />New Class
        </button>
        <button
          onClick={() => { setSectionForm(f => ({ ...f, class_id: classes[0]?.id || "" })); setShowSectionForm(v => !v); }}
          className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm rounded-xl"
        >
          <Plus className="w-4 h-4" />New Section
        </button>
        <button
          onClick={() => { setSubjectForm(f => ({ ...f, class_id: classes[0]?.id || "" })); setShowSubjectForm(v => !v); }}
          className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm rounded-xl"
        >
          <Plus className="w-4 h-4" />New Subject
        </button>
      </div>

      {/* ── New Class Form ────────────────────────────────────────────────── */}
      {showClassForm && (
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-white mb-3">Create New Class</h3>
          <form onSubmit={createClass} className="flex flex-wrap gap-3 items-end">
            <input required placeholder="Class Name (e.g. B.Tech - CSE)" value={classForm.name}
              onChange={e => setClassForm(f => ({ ...f, name: e.target.value }))} className={`${inp} flex-1 min-w-[200px]`} />
            <input placeholder="Course (optional)" value={classForm.course}
              onChange={e => setClassForm(f => ({ ...f, course: e.target.value }))} className={`${inp} flex-1 min-w-[160px]`} />
            <button type="submit" className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-xl">Create</button>
            <button type="button" onClick={() => setShowClassForm(false)} className="px-4 py-2 text-sm text-gray-400 hover:text-white">Cancel</button>
          </form>
        </div>
      )}

      {/* ── New Section Form ──────────────────────────────────────────────── */}
      {showSectionForm && (
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-white mb-3">Create New Section</h3>
          <form onSubmit={createSection} className="flex flex-wrap gap-3 items-end">
            <select required value={sectionForm.class_id}
              onChange={e => setSectionForm(f => ({ ...f, class_id: e.target.value }))}
              className={`${inp} flex-1 min-w-[200px]`}>
              <option value="">Select Class *</option>
              {classes.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <input required placeholder="Section Name (e.g. A, B, Morning)" value={sectionForm.name}
              onChange={e => setSectionForm(f => ({ ...f, name: e.target.value }))} className={`${inp} flex-1 min-w-[160px]`} />
            <button type="submit" className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm rounded-xl">Create</button>
            <button type="button" onClick={() => setShowSectionForm(false)} className="px-4 py-2 text-sm text-gray-400 hover:text-white">Cancel</button>
          </form>
        </div>
      )}

      {/* ── New Subject Form ──────────────────────────────────────────────── */}
      {showSubjectForm && (
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-white mb-3">Create New Subject</h3>
          <form onSubmit={createSubject} className="flex flex-wrap gap-3 items-end">
            <select required value={subjectForm.class_id}
              onChange={e => setSubjectForm(f => ({ ...f, class_id: e.target.value }))}
              className={`${inp} flex-1 min-w-[200px]`}>
              <option value="">Select Class *</option>
              {classes.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <input required placeholder="Subject Name" value={subjectForm.name}
              onChange={e => setSubjectForm(f => ({ ...f, name: e.target.value }))} className={`${inp} flex-1 min-w-[160px]`} />
            <input placeholder="Code (e.g. CS301)" value={subjectForm.code}
              onChange={e => setSubjectForm(f => ({ ...f, code: e.target.value }))} className={`${inp} flex-1 min-w-[120px]`} />
            <button type="submit" className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm rounded-xl">Create</button>
            <button type="button" onClick={() => setShowSubjectForm(false)} className="px-4 py-2 text-sm text-gray-400 hover:text-white">Cancel</button>
          </form>
        </div>
      )}

      {/* ── Classes List (expandable) ─────────────────────────────────────── */}
      {classes.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-12 text-center">
          <BookOpen className="w-12 h-12 text-gray-700 mx-auto mb-4" />
          <p className="text-gray-400">No classes yet. Create your first class to get started.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {classes.map(cls => {
            const classSections = sections.filter(s => s.class_id === cls.id);
            const classSubjects = subjects.filter(s => s.class_id === cls.id);
            const isExpanded = expanded === cls.id;

            return (
              <div key={cls.id} className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
                {/* Class header */}
                <div
                  className="flex items-center justify-between p-5 cursor-pointer hover:bg-gray-800/30"
                  onClick={() => setExpanded(isExpanded ? null : cls.id)}
                >
                  <div className="flex items-center gap-3">
                    {isExpanded
                      ? <ChevronDown className="w-4 h-4 text-gray-400" />
                      : <ChevronRight className="w-4 h-4 text-gray-400" />}
                    <div>
                      <h3 className="font-semibold text-white">{cls.name}</h3>
                      {cls.course && <p className="text-xs text-gray-500">{cls.course}</p>}
                    </div>
                    <div className="flex gap-2 ml-4">
                      <span className="text-xs bg-purple-500/20 text-purple-400 px-2 py-0.5 rounded-full">
                        {classSections.length} section{classSections.length !== 1 ? "s" : ""}
                      </span>
                      <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full">
                        {classSubjects.length} subject{classSubjects.length !== 1 ? "s" : ""}
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={ev => { ev.stopPropagation(); deleteClass(cls.id); }}
                    className="p-1.5 text-gray-600 hover:text-red-400 transition-colors"
                  >
                    <Trash className="w-4 h-4" />
                  </button>
                </div>

                {/* Expanded content */}
                {isExpanded && (
                  <div className="border-t border-gray-800 grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-gray-800">
                    {/* Sections column */}
                    <div className="p-5">
                      <h4 className="text-xs font-semibold text-purple-400 uppercase tracking-wider mb-3">Sections</h4>
                      {classSections.length === 0
                        ? <p className="text-xs text-gray-600">No sections</p>
                        : (
                          <ul className="space-y-2">
                            {classSections.map(sec => (
                              <li key={sec.id} className="flex items-center justify-between bg-gray-800 rounded-lg px-3 py-2">
                                <span className="text-sm text-white">{sec.name}</span>
                                <button onClick={() => deleteSection(sec.id)} className="text-gray-600 hover:text-red-400">
                                  <Trash className="w-3.5 h-3.5" />
                                </button>
                              </li>
                            ))}
                          </ul>
                        )
                      }
                    </div>

                    {/* Subjects column */}
                    <div className="p-5">
                      <h4 className="text-xs font-semibold text-green-400 uppercase tracking-wider mb-3">Subjects</h4>
                      {classSubjects.length === 0
                        ? <p className="text-xs text-gray-600">No subjects</p>
                        : (
                          <ul className="space-y-2">
                            {classSubjects.map(sub => (
                              <li key={sub.id} className="flex items-center justify-between bg-gray-800 rounded-lg px-3 py-2">
                                <div>
                                  <span className="text-sm text-white">{sub.name}</span>
                                  {sub.code && <span className="text-xs text-gray-500 ml-2">({sub.code})</span>}
                                </div>
                                <button onClick={() => deleteSubject(sub.id)} className="text-gray-600 hover:text-red-400">
                                  <Trash className="w-3.5 h-3.5" />
                                </button>
                              </li>
                            ))}
                          </ul>
                        )
                      }
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
