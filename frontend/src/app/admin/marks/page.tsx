"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { BarChart2, Plus, Send, Trash, X } from "lucide-react";
import toast from "react-hot-toast";

interface Subject { id: string; name: string; class_id: string; }
interface Category {
  id: string; name: string; subject_id: string;
  max_marks: number; weightage: number; created_at: string;
}
interface MarkRow {
  student_id: string; student_name: string;
  obtained: number | null; max: number; percentage: number | null; is_published: boolean;
}
interface Student { id: string; full_name: string; email: string; }

export default function AdminMarksPage() {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [report, setReport] = useState<MarkRow[]>([]);
  const [students, setStudents] = useState<Student[]>([]);

  const [selectedSubject, setSelectedSubject] = useState<string>("");
  const [selectedCategory, setSelectedCategory] = useState<Category | null>(null);

  // Category form
  const [showCatForm, setShowCatForm] = useState(false);
  const [catForm, setCatForm] = useState({ name: "", subject_id: "", max_marks: "100", weightage: "100" });

  // Marks entry state: { [studentId]: obtainedStr }
  const [marksInput, setMarksInput] = useState<Record<string, string>>({});
  const [remarksInput, setRemarksInput] = useState<Record<string, string>>({});
  const [savingMarks, setSavingMarks] = useState(false);

  const inp = "w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-xl text-white text-sm focus:outline-none focus:border-blue-500";

  useEffect(() => {
    api.get("/api/admin/subjects", { withCredentials: true }).then(r => setSubjects(r.data)).catch(() => {});
    api.get("/api/admin/students", { withCredentials: true }).then(r => setStudents(r.data)).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedSubject) { setCategories([]); setReport([]); return; }
    api.get(`/api/admin/assessment-categories?subject_id=${selectedSubject}`, { withCredentials: true })
      .then(r => setCategories(r.data))
      .catch(() => {});
    api.get(`/api/admin/marks/report?subject_id=${selectedSubject}`, { withCredentials: true })
      .then(r => setReport(r.data))
      .catch(() => {});
  }, [selectedSubject]);

  useEffect(() => {
    if (!selectedCategory) { setMarksInput({}); setRemarksInput({}); return; }
    // Pre-fill existing marks from report for this category
    const catRows = report.filter(r => r.max === selectedCategory.max_marks);
    const newInput: Record<string, string> = {};
    const newRemarks: Record<string, string> = {};
    catRows.forEach(r => {
      newInput[r.student_id] = r.obtained != null ? String(r.obtained) : "";
    });
    setMarksInput(newInput);
    setRemarksInput(newRemarks);
  }, [selectedCategory]);

  const createCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const r = await api.post("/api/admin/assessment-categories", {
        name: catForm.name,
        subject_id: catForm.subject_id || selectedSubject,
        max_marks: parseFloat(catForm.max_marks),
        weightage: parseFloat(catForm.weightage),
      }, { withCredentials: true });
      setCategories(c => [...c, r.data]);
      setCatForm({ name: "", subject_id: "", max_marks: "100", weightage: "100" });
      setShowCatForm(false);
      toast.success("Category created!");
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed");
    }
  };

  const deleteCategory = async (id: string) => {
    if (!confirm("Delete this assessment category and all its marks?")) return;
    try {
      await api.delete(`/api/admin/assessment-categories/${id}`, { withCredentials: true });
      setCategories(c => c.filter(x => x.id !== id));
      if (selectedCategory?.id === id) setSelectedCategory(null);
      toast.success("Deleted");
    } catch { toast.error("Failed"); }
  };

  const saveMarks = async () => {
    if (!selectedCategory) return;
    setSavingMarks(true);
    try {
      const entries = students
        .filter(s => marksInput[s.id] !== undefined && marksInput[s.id] !== "")
        .map(s => ({
          student_id: s.id,
          category_id: selectedCategory.id,
          obtained_marks: parseFloat(marksInput[s.id]),
          remarks: remarksInput[s.id] || "",
        }));
      if (entries.length === 0) { toast.error("Enter at least one mark"); return; }
      await api.post("/api/admin/marks", entries, { withCredentials: true });
      toast.success(`Saved ${entries.length} marks`);
      // Refresh report
      api.get(`/api/admin/marks/report?subject_id=${selectedSubject}`, { withCredentials: true })
        .then(r => setReport(r.data)).catch(() => {});
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed");
    } finally { setSavingMarks(false); }
  };

  const publishMarks = async () => {
    if (!selectedSubject) return;
    if (!confirm("Publish all marks for this subject? Students will be notified.")) return;
    try {
      const r = await api.post("/api/admin/marks/publish", { subject_id: selectedSubject }, { withCredentials: true });
      toast.success(r.data.message || "Marks published!");
      // Refresh report
      api.get(`/api/admin/marks/report?subject_id=${selectedSubject}`, { withCredentials: true })
        .then(r2 => setReport(r2.data)).catch(() => {});
    } catch { toast.error("Failed to publish"); }
  };

  const unpublishedCount = report.filter(r => !r.is_published).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <BarChart2 className="w-6 h-6 text-yellow-400" />Marks Management
        </h1>
        {selectedSubject && unpublishedCount > 0 && (
          <button
            onClick={publishMarks}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm rounded-xl"
          >
            <Send className="w-4 h-4" />Publish Marks ({unpublishedCount} entries)
          </button>
        )}
      </div>

      {/* Subject Selector */}
      <div className="flex flex-wrap gap-3">
        <select
          value={selectedSubject}
          onChange={e => { setSelectedSubject(e.target.value); setSelectedCategory(null); }}
          className="px-3 py-2 bg-gray-900 border border-gray-700 rounded-xl text-white text-sm focus:outline-none focus:border-blue-500"
        >
          <option value="">Select Subject to Manage Marks</option>
          {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
        {selectedSubject && (
          <button
            onClick={() => { setCatForm(f => ({ ...f, subject_id: selectedSubject })); setShowCatForm(v => !v); }}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm rounded-xl"
          >
            <Plus className="w-4 h-4" />Add Assessment Category
          </button>
        )}
      </div>

      {/* New Category Form */}
      {showCatForm && (
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-white mb-3">New Assessment Category</h3>
          <form onSubmit={createCategory} className="flex flex-wrap gap-3 items-end">
            <input required placeholder="Category name (e.g. Mid-Term)" value={catForm.name}
              onChange={e => setCatForm(f => ({ ...f, name: e.target.value }))} className={`${inp} flex-1 min-w-[180px]`} />
            <input type="number" placeholder="Max Marks" value={catForm.max_marks}
              onChange={e => setCatForm(f => ({ ...f, max_marks: e.target.value }))} className={`${inp} w-28`} />
            <input type="number" placeholder="Weightage %" value={catForm.weightage}
              onChange={e => setCatForm(f => ({ ...f, weightage: e.target.value }))} className={`${inp} w-28`} />
            <button type="submit" className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm rounded-xl">Create</button>
            <button type="button" onClick={() => setShowCatForm(false)} className="px-4 py-2 text-sm text-gray-400 hover:text-white">Cancel</button>
          </form>
        </div>
      )}

      {!selectedSubject ? (
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-12 text-center">
          <BarChart2 className="w-12 h-12 text-gray-700 mx-auto mb-4" />
          <p className="text-gray-400">Select a subject to manage marks</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          {/* Assessment Categories Panel */}
          <div className="xl:col-span-1 bg-gray-900 border border-gray-800 rounded-2xl p-5">
            <h3 className="text-sm font-semibold text-gray-300 mb-4">Assessment Categories</h3>
            {categories.length === 0 ? (
              <p className="text-xs text-gray-600">No categories yet</p>
            ) : (
              <ul className="space-y-2">
                {categories.map(cat => (
                  <li
                    key={cat.id}
                    onClick={() => setSelectedCategory(selectedCategory?.id === cat.id ? null : cat)}
                    className={`flex items-center justify-between p-3 rounded-xl cursor-pointer transition-colors border ${
                      selectedCategory?.id === cat.id
                        ? "border-blue-500 bg-blue-500/10"
                        : "border-gray-800 hover:border-gray-700 hover:bg-gray-800/50"
                    }`}
                  >
                    <div>
                      <p className="text-sm text-white font-medium">{cat.name}</p>
                      <p className="text-xs text-gray-500">Max: {cat.max_marks} | {cat.weightage}% weight</p>
                    </div>
                    <button
                      onClick={e => { e.stopPropagation(); deleteCategory(cat.id); }}
                      className="text-gray-600 hover:text-red-400 ml-2"
                    >
                      <Trash className="w-3.5 h-3.5" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Marks Entry / Report Panel */}
          <div className="xl:col-span-2 bg-gray-900 border border-gray-800 rounded-2xl p-5">
            {selectedCategory ? (
              <>
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-sm font-semibold text-white">Enter Marks: {selectedCategory.name}</h3>
                    <p className="text-xs text-gray-500">Max marks: {selectedCategory.max_marks}</p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={saveMarks}
                      disabled={savingMarks}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm rounded-xl"
                    >
                      {savingMarks ? "Saving..." : "Save Marks"}
                    </button>
                    <button onClick={() => setSelectedCategory(null)} className="p-2 text-gray-500 hover:text-white">
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                {students.length === 0 ? (
                  <p className="text-sm text-gray-500">No students found</p>
                ) : (
                  <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                    {students.map(stu => (
                      <div key={stu.id} className="flex items-center gap-3 bg-gray-800 rounded-xl p-3">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-white truncate">{stu.full_name}</p>
                          <p className="text-xs text-gray-500 truncate">{stu.email}</p>
                        </div>
                        <input
                          type="number"
                          min="0"
                          max={selectedCategory.max_marks}
                          step="0.5"
                          placeholder={`/ ${selectedCategory.max_marks}`}
                          value={marksInput[stu.id] ?? ""}
                          onChange={e => setMarksInput(m => ({ ...m, [stu.id]: e.target.value }))}
                          className="w-24 px-2 py-1.5 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm text-center focus:outline-none focus:border-blue-500"
                        />
                        <input
                          placeholder="Remarks"
                          value={remarksInput[stu.id] ?? ""}
                          onChange={e => setRemarksInput(m => ({ ...m, [stu.id]: e.target.value }))}
                          className="w-32 px-2 py-1.5 bg-gray-700 border border-gray-600 rounded-lg text-white text-xs focus:outline-none focus:border-blue-500"
                        />
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <>
                <h3 className="text-sm font-semibold text-gray-300 mb-4">Marks Report</h3>
                {report.length === 0 ? (
                  <p className="text-sm text-gray-600">No marks entered yet. Select a category on the left to begin.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-800">
                          <th className="text-left text-xs text-gray-400 py-2 pr-4">Student</th>
                          <th className="text-left text-xs text-gray-400 py-2 pr-4">Category</th>
                          <th className="text-right text-xs text-gray-400 py-2 pr-4">Marks</th>
                          <th className="text-right text-xs text-gray-400 py-2 pr-4">%</th>
                          <th className="text-center text-xs text-gray-400 py-2">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {report.map((row, i) => (
                          <tr key={i} className="border-b border-gray-800/50">
                            <td className="py-2 pr-4 text-white">{row.student_name}</td>
                            <td className="py-2 pr-4 text-gray-400">{row.category}</td>
                            <td className="py-2 pr-4 text-right text-white">{row.obtained} / {row.max}</td>
                            <td className="py-2 pr-4 text-right">
                              <span className={row.percentage != null && row.percentage >= 40 ? "text-green-400" : "text-red-400"}>
                                {row.percentage}%
                              </span>
                            </td>
                            <td className="py-2 text-center">
                              <span className={`text-xs px-2 py-0.5 rounded-full ${row.is_published ? "bg-green-500/20 text-green-400" : "bg-yellow-500/20 text-yellow-400"}`}>
                                {row.is_published ? "Published" : "Draft"}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
