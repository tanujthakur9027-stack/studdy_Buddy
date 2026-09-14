"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { LayoutDashboard, Users, ClipboardList, BarChart2, ArrowRight, Plus } from "lucide-react";
import Link from "next/link";

export default function AdminDashboard() {
  const [stats, setStats] = useState({ total: 0, active: 0 });
  const [assignments, setAssignments] = useState<{ id: string; title: string; is_published: boolean }[]>([]);
  const [submissions, setSubmissions] = useState<{ id: string; student_name: string; status: string }[]>([]);

  useEffect(() => {
    api.get("/api/admin/students/count", { withCredentials: true }).then(r => setStats(r.data)).catch(() => {});
    api.get("/api/admin/assignments", { withCredentials: true }).then(r => setAssignments(r.data.slice(0, 5))).catch(() => {});
    api.get("/api/admin/submissions?page_size=5", { withCredentials: true }).then(r => setSubmissions(r.data)).catch(() => {});
  }, []);

  const published = assignments.filter(a => a.is_published).length;
  const pending = submissions.filter(s => s.status !== "evaluated").length;

  const cards = [
    { label: "Total Students", value: stats.total, icon: Users, color: "text-blue-400", bg: "bg-blue-500/10", href: "/admin/students" },
    { label: "Active Students", value: stats.active, icon: Users, color: "text-green-400", bg: "bg-green-500/10", href: "/admin/students" },
    { label: "Total Assignments", value: assignments.length, icon: ClipboardList, color: "text-purple-400", bg: "bg-purple-500/10", href: "/admin/assignments" },
    { label: "Pending Submissions", value: pending, icon: BarChart2, color: "text-orange-400", bg: "bg-orange-500/10", href: "/admin/submissions" },
  ];

  const quickActions = [
    { href: "/admin/students", label: "Register Student", icon: Users },
    { href: "/admin/assignments", label: "Create Assignment", icon: ClipboardList },
    { href: "/admin/marks", label: "Enter Marks", icon: BarChart2 },
    { href: "/admin/timetable", label: "Create Timetable", icon: ClipboardList },
    { href: "/admin/announcements", label: "Send Announcement", icon: ClipboardList },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2"><LayoutDashboard className="w-6 h-6 text-yellow-400" />Admin Dashboard</h1>
          <p className="text-gray-400 mt-1">Manage students, assignments, marks, and timetables</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
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
        {/* Recent assignments */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white">Recent Assignments</h2>
            <Link href="/admin/assignments" className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1">View all <ArrowRight className="w-3 h-3" /></Link>
          </div>
          {assignments.length === 0 ? <p className="text-gray-500 text-sm text-center py-4">No assignments yet</p> : (
            <ul className="space-y-2">
              {assignments.map(a => (
                <li key={a.id} className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0">
                  <p className="text-sm text-white">{a.title}</p>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${a.is_published ? "bg-green-500/20 text-green-400" : "bg-yellow-500/20 text-yellow-400"}`}>
                    {a.is_published ? "Published" : "Draft"}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Quick actions */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
          <h2 className="font-semibold text-white mb-4">Quick Actions</h2>
          <div className="space-y-2">
            {quickActions.map(a => (
              <Link key={a.href} href={a.href} className="flex items-center gap-3 p-3 bg-gray-800 rounded-xl hover:bg-gray-700 transition-colors">
                <Plus className="w-4 h-4 text-blue-400" />
                <span className="text-sm text-gray-300">{a.label}</span>
                <ArrowRight className="w-3 h-3 text-gray-600 ml-auto" />
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
