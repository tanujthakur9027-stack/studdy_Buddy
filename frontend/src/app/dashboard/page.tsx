"use client";
import { useEffect, useState } from "react";
import { api, fetchProgressSummary } from "@/lib/api";
import type { ProgressSummary } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { ClipboardList, BarChart2, Calendar, Bell, FileText, Users, Brain, ArrowRight, Flame, Trophy } from "lucide-react";
import Link from "next/link";

export default function DashboardPage() {
  const { user } = useAuth();
  const [assignments, setAssignments] = useState<{ id: string; title: string; due_date: string; submission_status?: string }[]>([]);
  const [marks, setMarks] = useState<{ overall_percentage?: number; overall_grade?: string } | null>(null);
  const [unread, setUnread] = useState(0);
  const [todayPeriods, setTodayPeriods] = useState<{ subject: string; start_time: string; end_time: string }[]>([]);
  const [announcements, setAnnouncements] = useState<{ id: string; title: string; created_at: string }[]>([]);
  const [progress, setProgress] = useState<ProgressSummary | null>(null);

  useEffect(() => {
    api.get("/api/assignments", { withCredentials: true }).then(r => setAssignments(r.data.slice(0, 5))).catch(() => {});
    api.get("/api/marks/summary", { withCredentials: true }).then(r => setMarks(r.data)).catch(() => {});
    api.get("/api/notifications/unread-count", { withCredentials: true }).then(r => setUnread(r.data.count)).catch(() => {});
    api.get("/api/timetable/today", { withCredentials: true }).then(r => setTodayPeriods(r.data.periods || [])).catch(() => {});
    api.get("/api/announcements", { withCredentials: true }).then(r => setAnnouncements(r.data.slice(0, 3))).catch(() => {});
    fetchProgressSummary().then(setProgress).catch(() => {});
  }, []);

  const pending = assignments.filter(a => !a.submission_status).length;

  const cards = [
    { label: "Pending Assignments", value: pending, icon: ClipboardList, color: "text-orange-400", href: "/assignments", bg: "bg-orange-500/10" },
    { label: "Overall Grade", value: marks?.overall_grade || "—", icon: BarChart2, color: "text-green-400", href: "/marks", bg: "bg-green-500/10" },
    { label: "Today's Classes", value: todayPeriods.length, icon: Calendar, color: "text-blue-400", href: "/timetable", bg: "bg-blue-500/10" },
    { label: "Unread Notifications", value: unread, icon: Bell, color: "text-purple-400", href: "/notifications", bg: "bg-purple-500/10" },
    { label: "Study Streak", value: progress ? `${progress.current_streak_days}d` : "—", icon: Flame, color: "text-orange-400", href: "/learn", bg: "bg-orange-500/10" },
    { label: "Quizzes Taken", value: progress?.total_quizzes ?? "—", icon: Trophy, color: "text-yellow-400", href: "/learn", bg: "bg-yellow-500/10" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-gray-400 mt-1">Welcome back, {user?.full_name}!</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        {cards.map((c) => (
          <Link key={c.label} href={c.href} className="bg-gray-900 border border-gray-800 rounded-2xl p-5 hover:border-gray-700 transition-colors">
            <div className={`w-10 h-10 ${c.bg} rounded-xl flex items-center justify-center mb-3`}>
              <c.icon className={`w-5 h-5 ${c.color}`} />
            </div>
            <p className="text-2xl font-bold text-white">{c.value}</p>
            <p className="text-xs text-gray-400 mt-1">{c.label}</p>
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Upcoming assignments */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white flex items-center gap-2"><ClipboardList className="w-4 h-4 text-orange-400" />Assignments</h2>
            <Link href="/assignments" className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1">View all <ArrowRight className="w-3 h-3" /></Link>
          </div>
          {assignments.length === 0 ? (
            <p className="text-gray-500 text-sm text-center py-4">No assignments</p>
          ) : (
            <ul className="space-y-2">
              {assignments.slice(0, 5).map((a) => (
                <li key={a.id} className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0">
                  <div>
                    <p className="text-sm text-white font-medium">{a.title}</p>
                    <p className="text-xs text-gray-500">Due: {a.due_date}</p>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${a.submission_status ? "bg-green-500/20 text-green-400" : "bg-orange-500/20 text-orange-400"}`}>
                    {a.submission_status || "Pending"}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Today's timetable */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white flex items-center gap-2"><Calendar className="w-4 h-4 text-blue-400" />Today&apos;s Schedule</h2>
            <Link href="/timetable" className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1">Full view <ArrowRight className="w-3 h-3" /></Link>
          </div>
          {todayPeriods.length === 0 ? (
            <p className="text-gray-500 text-sm text-center py-4">No classes today</p>
          ) : (
            <ul className="space-y-2">
              {todayPeriods.slice(0, 5).map((p, i) => (
                <li key={i} className="flex items-center gap-3 py-2 border-b border-gray-800 last:border-0">
                  <div className="text-xs text-gray-500 w-20 shrink-0">{p.start_time} - {p.end_time}</div>
                  <p className="text-sm text-white">{p.subject || "—"}</p>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Announcements */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
          <h2 className="font-semibold text-white flex items-center gap-2 mb-4"><Bell className="w-4 h-4 text-purple-400" />Announcements</h2>
          {announcements.length === 0 ? (
            <p className="text-gray-500 text-sm text-center py-4">No announcements</p>
          ) : (
            <ul className="space-y-2">
              {announcements.map((a) => (
                <li key={a.id} className="py-2 border-b border-gray-800 last:border-0">
                  <p className="text-sm text-white font-medium">{a.title}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{new Date(a.created_at).toLocaleDateString()}</p>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Quick links */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
          <h2 className="font-semibold text-white mb-4">Quick Links</h2>
          <div className="grid grid-cols-2 gap-3">
            {[
              { href: "/marks", label: "View Marks", icon: BarChart2, color: "text-green-400" },
              { href: "/notes", label: "Study Notes", icon: FileText, color: "text-yellow-400" },
              { href: "/connections", label: "Connections", icon: Users, color: "text-blue-400" },
              { href: "/learn", label: "AI Tools", icon: Brain, color: "text-pink-400" },
            ].map((l) => (
              <Link key={l.href} href={l.href} className="flex items-center gap-2 p-3 bg-gray-800 rounded-xl hover:bg-gray-700 transition-colors">
                <l.icon className={`w-4 h-4 ${l.color}`} />
                <span className="text-sm text-gray-300">{l.label}</span>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
