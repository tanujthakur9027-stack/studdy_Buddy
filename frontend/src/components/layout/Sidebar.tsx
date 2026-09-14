"use client";
import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  LayoutDashboard, BookOpen, ClipboardList, BarChart2,
  Calendar, Bell, FileText, Users, Settings, GraduationCap,
  Brain, ChevronLeft, ChevronRight, LogOut, Shield,
  BookMarked, Megaphone, Send, UserCheck,
} from "lucide-react";
import { clsx } from "clsx";

const studentNav = [
  { href: "/dashboard",     label: "Dashboard",    icon: LayoutDashboard },
  { href: "/assignments",   label: "Assignments",  icon: ClipboardList },
  { href: "/marks",         label: "Marks",        icon: BarChart2 },
  { href: "/timetable",     label: "Timetable",    icon: Calendar },
  { href: "/notifications", label: "Notifications",icon: Bell },
  { href: "/notes",         label: "Notes",        icon: FileText },
  { href: "/connections",   label: "Connections",  icon: Users },
  { href: "/learn",         label: "AI Study Tools",icon: Brain },
  { href: "/profile",       label: "Profile",      icon: Settings },
];

const adminNav = [
  { href: "/admin/dashboard",     label: "Dashboard",    icon: LayoutDashboard },
  { href: "/admin/students",      label: "Students",     icon: UserCheck },
  { href: "/admin/assignments",   label: "Assignments",  icon: ClipboardList },
  { href: "/admin/submissions",   label: "Submissions",  icon: Send },
  { href: "/admin/marks",         label: "Marks",        icon: BarChart2 },
  { href: "/admin/timetable",     label: "Timetable",    icon: Calendar },
  { href: "/admin/announcements", label: "Announcements",icon: Megaphone },
  { href: "/admin/classes",       label: "Classes",      icon: BookMarked },
];

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const navItems = user?.role === "admin" ? adminNav : studentNav;

  return (
    <aside
      className={clsx(
        "flex flex-col bg-gray-900 border-r border-gray-800 transition-all duration-300 shrink-0",
        collapsed ? "w-16" : "w-56"
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-4 border-b border-gray-800">
        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center shrink-0">
          <GraduationCap className="w-5 h-5 text-white" />
        </div>
        {!collapsed && (
          <span className="font-bold text-white text-sm truncate">Study Buddy</span>
        )}
      </div>

      {/* Role badge */}
      {!collapsed && user && (
        <div className="px-4 py-2 border-b border-gray-800">
          <div className="flex items-center gap-2">
            {user.role === "admin" ? (
              <Shield className="w-3.5 h-3.5 text-yellow-400" />
            ) : (
              <BookOpen className="w-3.5 h-3.5 text-blue-400" />
            )}
            <span className="text-xs text-gray-400 capitalize">{user.role}</span>
          </div>
          <p className="text-xs text-gray-300 truncate mt-0.5 font-medium">{user.full_name}</p>
        </div>
      )}

      {/* Nav items */}
      <nav className="flex-1 overflow-y-auto py-3">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                "flex items-center gap-3 px-4 py-2.5 mx-2 rounded-lg transition-colors",
                active
                  ? "bg-blue-600/20 text-blue-400 border border-blue-600/30"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"
              )}
              title={collapsed ? item.label : undefined}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {!collapsed && <span className="text-sm font-medium truncate">{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Collapse toggle + Logout */}
      <div className="border-t border-gray-800 py-2">
        <button
          onClick={logout}
          className="flex items-center gap-3 px-4 py-2.5 mx-2 rounded-lg text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition-colors w-full"
          title={collapsed ? "Logout" : undefined}
        >
          <LogOut className="w-4 h-4 shrink-0" />
          {!collapsed && <span className="text-sm">Logout</span>}
        </button>
        <button
          onClick={() => setCollapsed((c) => !c)}
          className="flex items-center justify-center w-full py-2 text-gray-600 hover:text-gray-400 transition-colors"
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>
    </aside>
  );
}
