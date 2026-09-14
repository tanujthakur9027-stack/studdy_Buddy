"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Calendar } from "lucide-react";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

interface Period {
  period_number: number;
  subject: string;
  teacher: string;
  room: string;
  start_time: string;
  end_time: string;
}

interface DaySchedule {
  day: string;
  day_index: number;
  periods: Period[];
}

interface TimetableData {
  timetable_id: string;
  name: string;
  start_time: string;
  periods_per_day: number;
  lunch_after_period: number;
  lunch_start: string;
  lunch_end: string;
  schedule: DaySchedule[];
}

export default function TimetablePage() {
  const [data, setData] = useState<TimetableData | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeDay, setActiveDay] = useState(new Date().getDay() === 0 ? 0 : new Date().getDay() - 1);

  useEffect(() => {
    api.get("/api/timetable", { withCredentials: true })
      .then(r => { if (r.data.schedule) setData(r.data); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex justify-center py-12"><div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" /></div>;

  if (!data) return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white flex items-center gap-2"><Calendar className="w-6 h-6 text-blue-400" />Timetable</h1>
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-12 text-center">
        <Calendar className="w-12 h-12 text-gray-700 mx-auto mb-4" />
        <p className="text-gray-400">No timetable published yet</p>
      </div>
    </div>
  );

  const todayIdx = Math.min(activeDay, 5);
  const activeSched = data.schedule.find(d => d.day_index === todayIdx);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white flex items-center gap-2"><Calendar className="w-6 h-6 text-blue-400" />Timetable</h1>
        <p className="text-gray-400 text-sm">{data.name} • Start: {data.start_time}</p>
      </div>

      {/* Day selector */}
      <div className="flex gap-2 overflow-x-auto pb-2">
        {DAYS.map((day, idx) => (
          <button key={day} onClick={() => setActiveDay(idx)}
            className={`px-4 py-2 rounded-xl text-sm font-medium whitespace-nowrap transition-colors ${
              activeDay === idx ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-400 hover:text-white"
            }`}>
            {day.slice(0, 3)}
          </button>
        ))}
      </div>

      {/* Schedule */}
      <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
        <div className="p-4 border-b border-gray-800 bg-gray-800/50">
          <h2 className="font-semibold text-white">{DAYS[todayIdx]}</h2>
        </div>
        {!activeSched || activeSched.periods.length === 0 ? (
          <p className="text-gray-500 text-sm text-center py-8">No classes scheduled</p>
        ) : (
          <div className="divide-y divide-gray-800">
            {activeSched.periods.map((p, i) => (
              <>
                {i === data.lunch_after_period && (
                  <div key="lunch" className="flex items-center gap-4 p-4 bg-yellow-500/5">
                    <div className="w-20 text-xs text-yellow-400">{data.lunch_start} – {data.lunch_end}</div>
                    <div>
                      <p className="text-sm font-semibold text-yellow-400">🍽 Lunch Break</p>
                    </div>
                  </div>
                )}
                <div key={p.period_number} className="flex items-center gap-4 p-4 hover:bg-gray-800/50 transition-colors">
                  <div className="w-20 text-xs text-gray-500 shrink-0">{p.start_time} – {p.end_time}</div>
                  <div className="w-6 h-6 bg-blue-600/20 rounded-lg flex items-center justify-center text-blue-400 text-xs font-bold shrink-0">
                    {p.period_number}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-white">{p.subject || "—"}</p>
                    <p className="text-xs text-gray-500">{p.teacher}{p.room ? ` • Room ${p.room}` : ""}</p>
                  </div>
                </div>
              </>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
