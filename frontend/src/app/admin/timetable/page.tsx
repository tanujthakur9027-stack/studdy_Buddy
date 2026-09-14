"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Calendar, Plus, Send, Trash, X } from "lucide-react";
import toast from "react-hot-toast";

interface Class { id: string; name: string; }
interface Section { id: string; name: string; class_id: string; }
interface Subject { id: string; name: string; class_id: string; }
interface Timetable {
  id: string; class_id: string; section_id: string | null;
  name: string; start_time: string; periods_per_day: number;
  lunch_after_period: number; is_published: boolean; created_at: string;
}
interface Slot {
  id: string; day_of_week: number; period_number: number;
  subject_id: string | null; teacher_id: string | null;
  room: string; start_time: string; end_time: string;
}

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const DAY_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export default function AdminTimetablePage() {
  const [classes, setClasses] = useState<Class[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [timetables, setTimetables] = useState<Timetable[]>([]);
  const [selectedTT, setSelectedTT] = useState<Timetable | null>(null);
  const [slots, setSlots] = useState<Slot[]>([]);

  const [showTTForm, setShowTTForm] = useState(false);
  const [ttForm, setTTForm] = useState({
    class_id: "", section_id: "", name: "Timetable",
    start_time: "09:00", periods_per_day: "8", lunch_after_period: "4",
  });

  // Slot edit modal
  const [editSlot, setEditSlot] = useState<{ day: number; period: number; existing: Slot | null } | null>(null);
  const [slotForm, setSlotForm] = useState({ subject_id: "", room: "" });
  const [savingSlot, setSavingSlot] = useState(false);

  const inp = "w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-xl text-white text-sm focus:outline-none focus:border-blue-500";

  useEffect(() => {
    api.get("/api/admin/classes", { withCredentials: true }).then(r => setClasses(r.data)).catch(() => {});
    api.get("/api/admin/sections", { withCredentials: true }).then(r => setSections(r.data)).catch(() => {});
    api.get("/api/admin/subjects", { withCredentials: true }).then(r => setSubjects(r.data)).catch(() => {});
    api.get("/api/admin/timetables", { withCredentials: true }).then(r => setTimetables(r.data)).catch(() => {});
  }, []);

  const loadSlots = (tt: Timetable) => {
    setSelectedTT(tt);
    api.get(`/api/admin/timetables/${tt.id}/slots`, { withCredentials: true })
      .then(r => setSlots(r.data))
      .catch(() => toast.error("Failed to load slots"));
  };

  const createTimetable = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        class_id: ttForm.class_id,
        section_id: ttForm.section_id || null,
        name: ttForm.name,
        start_time: ttForm.start_time,
        periods_per_day: parseInt(ttForm.periods_per_day),
        lunch_after_period: parseInt(ttForm.lunch_after_period),
      };
      const r = await api.post("/api/admin/timetables", payload, { withCredentials: true });
      setTimetables(t => [r.data, ...t]);
      setShowTTForm(false);
      toast.success("Timetable created!");
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed");
    }
  };

  const deleteTimetable = async (id: string) => {
    if (!confirm("Delete this timetable?")) return;
    try {
      await api.delete(`/api/admin/timetables/${id}`, { withCredentials: true });
      setTimetables(t => t.filter(x => x.id !== id));
      if (selectedTT?.id === id) { setSelectedTT(null); setSlots([]); }
      toast.success("Deleted");
    } catch { toast.error("Failed"); }
  };

  const publishTimetable = async (id: string) => {
    try {
      const r = await api.post(`/api/admin/timetables/${id}/publish`, {}, { withCredentials: true });
      setTimetables(t => t.map(x => x.id === id ? { ...x, is_published: true } : x));
      if (selectedTT?.id === id) setSelectedTT(s => s ? { ...s, is_published: true } : s);
      toast.success(r.data.message || "Published!");
    } catch { toast.error("Failed to publish"); }
  };

  // Open cell for editing
  const openCell = (day: number, period: number) => {
    const existing = slots.find(s => s.day_of_week === day && s.period_number === period) || null;
    setEditSlot({ day, period, existing });
    setSlotForm({
      subject_id: existing?.subject_id || "",
      room: existing?.room || "",
    });
  };

  const saveSlot = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTT || !editSlot) return;
    setSavingSlot(true);
    try {
      const payload = {
        day_of_week: editSlot.day,
        period_number: editSlot.period,
        subject_id: slotForm.subject_id || null,
        teacher_id: null,
        room: slotForm.room,
      };

      let updated: Slot;
      if (editSlot.existing) {
        const r = await api.patch(
          `/api/admin/timetables/${selectedTT.id}/slots/${editSlot.existing.id}`,
          payload, { withCredentials: true }
        );
        updated = r.data;
        setSlots(s => s.map(x => x.id === editSlot.existing!.id ? updated : x));
      } else {
        const r = await api.post(
          `/api/admin/timetables/${selectedTT.id}/slots`,
          payload, { withCredentials: true }
        );
        updated = r.data;
        setSlots(s => [...s, updated]);
      }
      setEditSlot(null);
      toast.success("Slot saved!");
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Conflict detected");
    } finally { setSavingSlot(false); }
  };

  const deleteSlot = async (slotId: string) => {
    if (!selectedTT) return;
    try {
      await api.delete(`/api/admin/timetables/${selectedTT.id}/slots/${slotId}`, { withCredentials: true });
      setSlots(s => s.filter(x => x.id !== slotId));
      setEditSlot(null);
      toast.success("Slot cleared");
    } catch { toast.error("Failed"); }
  };

  // Build period headers from selected timetable
  const getPeriodTimes = (period: number): string => {
    if (!selectedTT) return "";
    const slot = slots.find(s => s.period_number === period);
    if (slot) return `${slot.start_time}–${slot.end_time}`;
    return "";
  };

  const filteredSections = ttForm.class_id
    ? sections.filter(s => s.class_id === ttForm.class_id)
    : sections;

  const periods = selectedTT
    ? Array.from({ length: selectedTT.periods_per_day }, (_, i) => i + 1)
    : [];

  const subjectMap = Object.fromEntries(subjects.map(s => [s.id, s.name]));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Calendar className="w-6 h-6 text-blue-400" />Timetable Management
        </h1>
        <button
          onClick={() => setShowTTForm(v => !v)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-xl"
        >
          <Plus className="w-4 h-4" />New Timetable
        </button>
      </div>

      {/* New Timetable Form */}
      {showTTForm && (
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-white mb-4">Create Timetable</h3>
          <form onSubmit={createTimetable} className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <select required value={ttForm.class_id}
              onChange={e => setTTForm(f => ({ ...f, class_id: e.target.value, section_id: "" }))}
              className={inp}>
              <option value="">Select Class *</option>
              {classes.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <select value={ttForm.section_id}
              onChange={e => setTTForm(f => ({ ...f, section_id: e.target.value }))}
              className={inp}>
              <option value="">All Sections</option>
              {filteredSections.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <input placeholder="Timetable Name" value={ttForm.name}
              onChange={e => setTTForm(f => ({ ...f, name: e.target.value }))} className={inp} />
            <div>
              <label className="text-xs text-gray-400 block mb-1">Start Time</label>
              <input type="time" value={ttForm.start_time}
                onChange={e => setTTForm(f => ({ ...f, start_time: e.target.value }))} className={inp} />
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">Periods Per Day</label>
              <input type="number" min="1" max="12" value={ttForm.periods_per_day}
                onChange={e => setTTForm(f => ({ ...f, periods_per_day: e.target.value }))} className={inp} />
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">Lunch After Period #</label>
              <input type="number" min="1" value={ttForm.lunch_after_period}
                onChange={e => setTTForm(f => ({ ...f, lunch_after_period: e.target.value }))} className={inp} />
            </div>
            <div className="col-span-2 md:col-span-3 flex gap-3 justify-end">
              <button type="button" onClick={() => setShowTTForm(false)} className="px-4 py-2 text-sm text-gray-400 hover:text-white">Cancel</button>
              <button type="submit" className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-xl">Create</button>
            </div>
          </form>
        </div>
      )}

      {/* Timetable List */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {timetables.length === 0 ? (
          <div className="col-span-full bg-gray-900 border border-gray-800 rounded-2xl p-12 text-center">
            <Calendar className="w-12 h-12 text-gray-700 mx-auto mb-4" />
            <p className="text-gray-400">No timetables yet</p>
          </div>
        ) : timetables.map(tt => (
          <div
            key={tt.id}
            className={`bg-gray-900 border rounded-2xl p-5 cursor-pointer transition-colors ${selectedTT?.id === tt.id ? "border-blue-500" : "border-gray-800 hover:border-gray-700"}`}
            onClick={() => loadSlots(tt)}
          >
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold text-white">{tt.name}</h3>
                <p className="text-xs text-gray-500 mt-1">
                  Start: {tt.start_time} • {tt.periods_per_day} periods • Lunch after P{tt.lunch_after_period}
                </p>
              </div>
              <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                {!tt.is_published && (
                  <button onClick={() => publishTimetable(tt.id)} className="p-1.5 text-gray-500 hover:text-green-400" title="Publish">
                    <Send className="w-4 h-4" />
                  </button>
                )}
                <button onClick={() => deleteTimetable(tt.id)} className="p-1.5 text-gray-500 hover:text-red-400" title="Delete">
                  <Trash className="w-4 h-4" />
                </button>
              </div>
            </div>
            <div className="mt-3">
              <span className={`text-xs px-2 py-0.5 rounded-full ${tt.is_published ? "bg-green-500/20 text-green-400" : "bg-yellow-500/20 text-yellow-400"}`}>
                {tt.is_published ? "Published" : "Draft"}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Timetable Grid Editor */}
      {selectedTT && (
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-white">{selectedTT.name} — Click a cell to edit</h3>
            {!selectedTT.is_published && (
              <button
                onClick={() => publishTimetable(selectedTT.id)}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm rounded-xl"
              >
                <Send className="w-4 h-4" />Publish
              </button>
            )}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-xs">
              <thead>
                <tr>
                  <th className="bg-gray-800 text-gray-400 font-medium px-3 py-2 text-left border border-gray-700 min-w-[80px]">Period</th>
                  {DAYS.slice(0, 6).map((d, i) => (
                    <th key={i} className="bg-gray-800 text-gray-400 font-medium px-3 py-2 border border-gray-700 min-w-[100px]">
                      <span className="hidden md:block">{d}</span>
                      <span className="md:hidden">{DAY_SHORT[i]}</span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {periods.map(period => {
                  // Insert lunch break row
                  const lunchRow = period === selectedTT.lunch_after_period + 1;
                  return (
                    <>
                      {lunchRow && (
                        <tr key={`lunch-${period}`}>
                          <td colSpan={7} className="bg-orange-500/10 text-orange-400 text-center py-2 border border-gray-700 text-xs font-medium">
                            🍽️ Lunch Break (45 min)
                          </td>
                        </tr>
                      )}
                      <tr key={period}>
                        <td className="bg-gray-800/50 border border-gray-700 px-3 py-2">
                          <div className="font-medium text-gray-300">P{period}</div>
                          <div className="text-gray-500">{getPeriodTimes(period)}</div>
                        </td>
                        {Array.from({ length: 6 }, (_, dayIdx) => {
                          const slot = slots.find(s => s.day_of_week === dayIdx && s.period_number === period);
                          return (
                            <td
                              key={dayIdx}
                              onClick={() => openCell(dayIdx, period)}
                              className={`border border-gray-700 px-2 py-2 cursor-pointer hover:bg-blue-500/10 transition-colors ${slot ? "bg-gray-800/30" : ""}`}
                            >
                              {slot ? (
                                <div>
                                  <div className="font-medium text-white">{slot.subject_id ? subjectMap[slot.subject_id] || "?" : "—"}</div>
                                  {slot.room && <div className="text-gray-500">{slot.room}</div>}
                                </div>
                              ) : (
                                <div className="text-gray-700 text-center">+</div>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    </>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Slot Edit Modal */}
      {editSlot && selectedTT && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full max-w-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-white">
                {DAYS[editSlot.day]} — Period {editSlot.period}
              </h3>
              <button onClick={() => setEditSlot(null)} className="text-gray-500 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={saveSlot} className="space-y-3">
              <div>
                <label className="text-xs text-gray-400 block mb-1">Subject</label>
                <select
                  value={slotForm.subject_id}
                  onChange={e => setSlotForm(f => ({ ...f, subject_id: e.target.value }))}
                  className={inp}
                >
                  <option value="">— Free Period —</option>
                  {subjects.filter(s => !selectedTT.class_id || s.class_id === selectedTT.class_id).map(s => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">Room (optional)</label>
                <input
                  placeholder="e.g. Lab 3, Room 201"
                  value={slotForm.room}
                  onChange={e => setSlotForm(f => ({ ...f, room: e.target.value }))}
                  className={inp}
                />
              </div>
              <div className="flex gap-2 pt-2">
                {editSlot.existing && (
                  <button
                    type="button"
                    onClick={() => deleteSlot(editSlot.existing!.id)}
                    className="px-3 py-2 bg-red-600/20 hover:bg-red-600/40 text-red-400 text-sm rounded-xl flex items-center gap-1"
                  >
                    <Trash className="w-3.5 h-3.5" />Clear
                  </button>
                )}
                <div className="flex-1" />
                <button type="button" onClick={() => setEditSlot(null)} className="px-4 py-2 text-sm text-gray-400 hover:text-white">Cancel</button>
                <button type="submit" disabled={savingSlot} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm rounded-xl">
                  {savingSlot ? "Saving..." : "Save"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
