"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  LayoutDashboard, BookOpen, ClipboardList, BarChart2,
  Calendar, Bell, FileText, Users, Settings, GraduationCap,
  Brain, ChevronLeft, ChevronRight, LogOut, Shield,
  BookMarked, Megaphone, Send, UserCheck, Menu, X,
} from "lucide-react";
import { clsx } from "clsx";
import { motion, AnimatePresence } from "framer-motion";

const studentNav = [
  { href: "/dashboard",     label: "Dashboard",      icon: LayoutDashboard, color: "text-blue-400"    },
  { href: "/assignments",   label: "Assignments",     icon: ClipboardList,   color: "text-orange-400"  },
  { href: "/marks",         label: "Marks",           icon: BarChart2,       color: "text-green-400"   },
  { href: "/timetable",     label: "Timetable",       icon: Calendar,        color: "text-emerald-400" },
  { href: "/notifications", label: "Notifications",   icon: Bell,            color: "text-yellow-400"  },
  { href: "/notes",         label: "Notes",           icon: FileText,        color: "text-purple-400"  },
  { href: "/connections",   label: "Connections",     icon: Users,           color: "text-cyan-400"    },
  { href: "/learn",         label: "AI Study Tools",  icon: Brain,           color: "text-pink-400"    },
  { href: "/profile",       label: "Profile",         icon: Settings,        color: "text-gray-400"    },
];

const adminNav = [
  { href: "/admin/dashboard",     label: "Dashboard",     icon: LayoutDashboard, color: "text-blue-400"   },
  { href: "/admin/students",      label: "Students",      icon: UserCheck,       color: "text-cyan-400"   },
  { href: "/admin/assignments",   label: "Assignments",   icon: ClipboardList,   color: "text-orange-400" },
  { href: "/admin/submissions",   label: "Submissions",   icon: Send,            color: "text-green-400"  },
  { href: "/admin/marks",         label: "Marks",         icon: BarChart2,       color: "text-emerald-400"},
  { href: "/admin/timetable",     label: "Timetable",     icon: Calendar,        color: "text-yellow-400" },
  { href: "/admin/announcements", label: "Announcements", icon: Megaphone,       color: "text-purple-400" },
  { href: "/admin/classes",       label: "Classes",       icon: BookMarked,      color: "text-pink-400"   },
];

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();
  const { user, logout } = useAuth();

  // Close mobile drawer on route change
  useEffect(() => { setMobileOpen(false); }, [pathname]);

  const navItems = user?.role === "admin" ? adminNav : studentNav;

  const SidebarContent = () => (
    <div className="flex flex-col h-full">
      {/* ── Logo ── */}
      <div className="flex items-center gap-3 px-4 py-4 border-b border-gray-800">
        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center shrink-0 shadow-lg shadow-blue-900/40">
          <GraduationCap className="w-5 h-5 text-white" />
        </div>
        <AnimatePresence>
          {!collapsed && (
            <motion.span
              key="logo-text"
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: "auto" }}
              exit={{ opacity: 0, width: 0 }}
              transition={{ duration: 0.2 }}
              className="font-bold text-white text-sm whitespace-nowrap overflow-hidden"
            >
              Study Buddy AI
            </motion.span>
          )}
        </AnimatePresence>
      </div>

      {/* ── Role / user badge ── */}
      <AnimatePresence>
        {!collapsed && user && (
          <motion.div
            key="user-badge"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="px-4 py-2.5 border-b border-gray-800 overflow-hidden"
          >
            <div className="flex items-center gap-2">
              {user.role === "admin" ? (
                <Shield className="w-3.5 h-3.5 text-yellow-400" />
              ) : (
                <BookOpen className="w-3.5 h-3.5 text-blue-400" />
              )}
              <span className="text-xs text-gray-500 capitalize">{user.role}</span>
            </div>
            <p className="text-xs text-gray-300 truncate mt-0.5 font-semibold">{user.full_name}</p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Nav items ── */}
      <nav className="flex-1 overflow-y-auto py-3 space-y-0.5 px-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              title={collapsed ? item.label : undefined}
              className={clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-150 group relative",
                active
                  ? "bg-blue-600/15 border border-blue-600/20 text-white"
                  : "text-gray-400 hover:text-white hover:bg-gray-800/70"
              )}
            >
              {/* Active pill */}
              {active && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 rounded-r-full bg-blue-500" />
              )}
              <Icon
                className={clsx(
                  "w-4 h-4 shrink-0 transition-colors",
                  active ? item.color : "text-gray-500 group-hover:text-gray-300"
                )}
              />
              <AnimatePresence>
                {!collapsed && (
                  <motion.span
                    key={`label-${item.href}`}
                    initial={{ opacity: 0, width: 0 }}
                    animate={{ opacity: 1, width: "auto" }}
                    exit={{ opacity: 0, width: 0 }}
                    transition={{ duration: 0.18 }}
                    className="text-sm font-medium whitespace-nowrap overflow-hidden"
                  >
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>
            </Link>
          );
        })}
      </nav>

      {/* ── Footer: logout + collapse ── */}
      <div className="border-t border-gray-800 py-2 px-2 space-y-1">
        <button
          onClick={logout}
          title={collapsed ? "Logout" : undefined}
          className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition-all w-full group"
        >
          <LogOut className="w-4 h-4 shrink-0 group-hover:scale-105 transition-transform" />
          <AnimatePresence>
            {!collapsed && (
              <motion.span
                key="logout-text"
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: "auto" }}
                exit={{ opacity: 0, width: 0 }}
                transition={{ duration: 0.18 }}
                className="text-sm whitespace-nowrap overflow-hidden"
              >
                Logout
              </motion.span>
            )}
          </AnimatePresence>
        </button>

        {/* Collapse / expand button (desktop) */}
        <button
          onClick={() => setCollapsed((c) => !c)}
          className="flex items-center justify-center w-full py-1.5 text-gray-600 hover:text-gray-400 transition-colors rounded-lg hover:bg-gray-800/50"
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed
            ? <ChevronRight className="w-4 h-4" />
            : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>
    </div>
  );

  return (
    <>
      {/* ── Desktop sidebar ── */}
      <aside
        className={clsx(
          "hidden md:flex flex-col bg-gray-900 border-r border-gray-800 transition-all duration-300 shrink-0",
          collapsed ? "w-[60px]" : "w-56"
        )}
      >
        <SidebarContent />
      </aside>

      {/* ── Mobile: hamburger trigger ── */}
      <button
        onClick={() => setMobileOpen(true)}
        className="md:hidden fixed top-3.5 left-4 z-50 p-2 rounded-lg bg-gray-900 border border-gray-800 text-gray-400 hover:text-white transition-colors"
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* ── Mobile: slide-in drawer ── */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              key="backdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="md:hidden fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
              onClick={() => setMobileOpen(false)}
            />
            {/* Drawer */}
            <motion.aside
              key="drawer"
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", damping: 28, stiffness: 300 }}
              className="md:hidden fixed left-0 top-0 bottom-0 z-50 w-64 bg-gray-900 border-r border-gray-800 flex flex-col"
            >
              {/* Close button */}
              <button
                onClick={() => setMobileOpen(false)}
                className="absolute top-3.5 right-3.5 p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
              <SidebarContent />
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
