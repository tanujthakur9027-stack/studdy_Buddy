"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Users, Search, ToggleLeft, ToggleRight, Eye, BookOpen } from "lucide-react";
import toast from "react-hot-toast";

interface Student {
  id: string; email: string; full_name: string; is_active: boolean;
  created_at: string; student_id: string; course: string; branch: string;
  semester: string; section: string; academic_year: string;
  class_id: string | null;
}

interface Class {
  id: string;
  name: string;
  course: string;
}

export default function AdminStudentsPage() {
  const [students, setStudents] = useState<Student[]>([]);
  const [classes, setClasses] = useState<Class[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Student | null>(null);
  const [assigningClass, setAssigningClass] = useState(false);
  const [selectedClassId, setSelectedClassId] = useState<string>("");

  const load = (q?: string) => {
    const params = q ? `?search=${encodeURIComponent(q)}` : "";
    api.get(`/api/admin/students${params}`, { withCredentials: true })
      .then(r => setStudents(r.data))
      .catch(() => toast.error("Failed to load students"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    api.get("/api/admin/classes", { withCredentials: true })
      .then(r => setClasses(r.data))
      .catch(() => {});
  }, []);

  const toggleStatus = async (id: string, current: boolean) => {
    try {
      await api.patch(`/api/admin/students/${id}/status`, { is_active: !current }, { withCredentials: true });
      setStudents(s => s.map(x => x.id === id ? { ...x, is_active: !current } : x));
      toast.success(`Student ${!current ? "activated" : "deactivated"}`);
    } catch { toast.error("Failed"); }
  };

  const openDetail = (s: Student) => {
    setSelected(s);
    setSelectedClassId(s.class_id ?? "");
  };

  const saveClassAssignment = async () => {
    if (!selected) return;
    setAssigningClass(true);
    try {
      await api.patch(
        `/api/admin/students/${selected.id}/class`,
        { class_id: selectedClassId || null },
        { withCredentials: true },
      );
      const updatedClassId = selectedClassId || null;
      setStudents(s => s.map(x => x.id === selected.id ? { ...x, class_id: updatedClassId } : x));
      setSelected(prev => prev ? { ...prev, class_id: updatedClassId } : null);
      toast.success(updatedClassId ? "Student assigned to class" : "Student removed from class");
    } catch {
      toast.error("Failed to update class assignment");
    } finally {
      setAssigningClass(false);
    }
  };

  const getClassName = (classId: string | null) => {
    if (!classId) return null;
    return classes.find(c => c.id === classId)?.name ?? null;
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white flex items-center gap-2">
        <Users className="w-6 h-6 text-blue-400" />Students
      </h1>

      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-500" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            onKeyDown={e => e.key === "Enter" && load(search)}
            placeholder="Search by name, email or student ID..."
            className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-xl text-white text-sm focus:outline-none focus:border-blue-500"
          />
        </div>
        <button onClick={() => load(search)} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-xl">Search</button>
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" /></div>
      ) : (
        <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-800/50">
              <tr>
                {["Name", "Student ID", "Email", "Course", "Class", "Status", "Actions"].map(h => (
                  <th key={h} className="text-left px-4 py-3 text-gray-400 font-medium text-xs">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {students.length === 0 ? (
                <tr><td colSpan={7} className="text-center py-8 text-gray-500">No students found</td></tr>
              ) : students.map(s => (
                <tr key={s.id} className="hover:bg-gray-800/30 transition-colors">
                  <td className="px-4 py-3 text-white font-medium">{s.full_name}</td>
                  <td className="px-4 py-3 text-gray-400">{s.student_id}</td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{s.email}</td>
                  <td className="px-4 py-3 text-gray-400">{s.course}</td>
                  <td className="px-4 py-3">
                    {getClassName(s.class_id) ? (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 flex items-center gap-1 w-fit">
                        <BookOpen className="w-3 h-3" />{getClassName(s.class_id)}
                      </span>
                    ) : (
                      <span className="text-xs text-gray-600">— Not assigned</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${s.is_active ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"}`}>
                      {s.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <button onClick={() => openDetail(s)} className="p-1.5 text-gray-400 hover:text-white"><Eye className="w-4 h-4" /></button>
                      <button onClick={() => toggleStatus(s.id, s.is_active)} className={`p-1.5 ${s.is_active ? "text-green-400 hover:text-red-400" : "text-red-400 hover:text-green-400"}`}>
                        {s.is_active ? <ToggleRight className="w-4 h-4" /> : <ToggleLeft className="w-4 h-4" />}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Student detail + class assignment modal */}
      {selected && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full max-w-lg">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-white">{selected.full_name}</h2>
              <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-white">✕</button>
            </div>

            <div className="grid grid-cols-2 gap-4 text-sm mb-6">
              {[
                ["Student ID", selected.student_id], ["Email", selected.email],
                ["Course", selected.course], ["Branch", selected.branch],
                ["Semester", selected.semester], ["Section", selected.section],
                ["Academic Year", selected.academic_year],
                ["Joined", new Date(selected.created_at).toLocaleDateString()],
              ].map(([label, value]) => (
                <div key={label}>
                  <p className="text-gray-500 text-xs">{label}</p>
                  <p className="text-white mt-0.5">{value || "—"}</p>
                </div>
              ))}
            </div>

            {/* Class assignment section */}
            <div className="border-t border-gray-800 pt-4">
              <p className="text-xs text-gray-400 mb-2 flex items-center gap-1">
                <BookOpen className="w-3.5 h-3.5" />Assign to Class
              </p>
              <div className="flex gap-2">
                <select
                  value={selectedClassId}
                  onChange={e => setSelectedClassId(e.target.value)}
                  className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-xl text-white text-sm focus:outline-none focus:border-blue-500"
                >
                  <option value="">— No class (unassign)</option>
                  {classes.map(c => (
                    <option key={c.id} value={c.id}>{c.name}{c.course ? ` (${c.course})` : ""}</option>
                  ))}
                </select>
                <button
                  onClick={saveClassAssignment}
                  disabled={assigningClass}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm rounded-xl"
                >
                  {assigningClass ? "Saving…" : "Save"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
