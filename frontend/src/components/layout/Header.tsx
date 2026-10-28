"use client";
import { useEffect, useState, useRef } from "react";
import {
  Bell, X, Shield, GraduationCap, User, LogOut, Send,
  ChevronDown, AlertCircle, LogIn
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { api, contactAdmin } from "@/lib/api";
import Link from "next/link";
import toast from "react-hot-toast";

interface Notification {
  id: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
  notif_type: string;
}

export default function Header() {
  const { user, logout } = useAuth();
  const [unread, setUnread] = useState(0);
  const [notifOpen, setNotifOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);

  // Contact Admin modal state
  const [contactOpen, setContactOpen] = useState(false);
  const [contactTitle, setContactTitle] = useState("");
  const [contactMessage, setContactMessage] = useState("");
  const [contactCategory, setContactCategory] = useState("academic");
  const [contactSending, setContactSending] = useState(false);

  const profileRef = useRef<HTMLDivElement>(null);
  const notifRef = useRef<HTMLDivElement>(null);

  const fetchCount = async () => {
    try {
      const { data } = await api.get("/api/notifications/unread-count", { withCredentials: true });
      setUnread(data.count);
    } catch {
      /* ignore */
    }
  };

  const fetchNotifs = async () => {
    try {
      const { data } = await api.get("/api/notifications?page_size=10", { withCredentials: true });
      setNotifications(data);
    } catch {
      /* ignore */
    }
  };

  const markAllRead = async () => {
    try {
      await api.patch("/api/notifications/read-all", {}, { withCredentials: true });
      setUnread(0);
      setNotifications((n) => n.map((x) => ({ ...x, is_read: true })));
      toast.success("All notifications marked as read");
    } catch {
      /* ignore */
    }
  };

  const handleContactSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!contactTitle.trim() || !contactMessage.trim()) {
      toast.error("Please fill in both a title and your message.");
      return;
    }
    setContactSending(true);
    try {
      await contactAdmin({
        title: contactTitle.trim(),
        message: contactMessage.trim(),
        category: contactCategory,
      });
      toast.success("Your message has been sent to the administration!");
      setContactOpen(false);
      setContactTitle("");
      setContactMessage("");
    } catch (err: unknown) {
      toast.error(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          "Could not send contact request. Please try again."
      );
    } finally {
      setContactSending(false);
    }
  };

  // Close popovers on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotifOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (!user) return;
    fetchCount();
    const interval = setInterval(fetchCount, 30_000);
    return () => clearInterval(interval);
  }, [user]);

  const isAdmin = user?.role === "admin";

  return (
    <header className="h-16 bg-gray-900 border-b border-gray-800 flex items-center justify-between px-6 shrink-0 relative z-40">
      {/* ── Left: Identity Identification Banner ── */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2.5">
          <div
            className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold text-sm shadow-md ${
              isAdmin
                ? "bg-gradient-to-tr from-amber-600 to-yellow-500 text-black shadow-amber-500/20"
                : "bg-gradient-to-tr from-blue-600 to-indigo-500 text-white shadow-blue-500/20"
            }`}
          >
            {user?.full_name?.charAt(0).toUpperCase() || "U"}
          </div>

          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-white tracking-tight">
                {user?.full_name || "Guest User"}
              </span>

              {/* Role badge */}
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded-full inline-flex items-center gap-1 border ${
                  isAdmin
                    ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                    : "bg-blue-500/10 text-blue-400 border-blue-500/30"
                }`}
              >
                {isAdmin ? <Shield className="w-3 h-3" /> : <GraduationCap className="w-3 h-3" />}
                {isAdmin ? "ADMIN" : "STUDENT"}
              </span>

              {/* Student ID badge */}
              {user?.student_id && (
                <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded-md bg-gray-800 text-gray-300 border border-gray-700/60 hidden sm:inline-block">
                  ID: {user.student_id}
                </span>
              )}
            </div>

            <p className="text-[11px] text-gray-400 flex items-center gap-1.5 mt-0.5">
              <span>{user?.email || "Not signed in"}</span>
              {user?.class_name && (
                <>
                  <span className="text-gray-600">•</span>
                  <span className="text-indigo-400 font-medium">{user.class_name}</span>
                </>
              )}
            </p>
          </div>
        </div>
      </div>

      {/* ── Right: Action Buttons & Navigation Dropdowns ── */}
      <div className="flex items-center gap-3">
        {/* If user is not logged in: prominent Student Login and Admin Login buttons */}
        {!user && (
          <div className="flex items-center gap-2">
            <Link
              href="/login?role=student"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-bold shadow-md shadow-blue-600/30 transition-all"
            >
              <GraduationCap className="w-3.5 h-3.5" />
              Student Login
            </Link>
            <Link
              href="/login?role=admin"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-bold transition-all shadow-sm"
            >
              <Shield className="w-3.5 h-3.5 text-amber-400" />
              Admin Login
            </Link>
          </div>
        )}

        {/* If logged in as student: option to switch to Admin Portal */}
        {user && !isAdmin && (
          <Link
            href="/login?role=admin"
            className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gray-800/80 hover:bg-amber-500/10 text-gray-400 hover:text-amber-300 border border-gray-700/80 hover:border-amber-500/30 text-xs font-semibold transition-all"
          >
            <Shield className="w-3.5 h-3.5 text-amber-400" />
            Admin Portal
          </Link>
        )}

        {/* Admin Quick Hub button for logged-in admins */}
        {isAdmin && (
          <Link
            href="/admin/dashboard"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-bold transition-all shadow-sm"
          >
            <Shield className="w-3.5 h-3.5 text-amber-400" />
            Admin Hub
          </Link>
        )}

        {/* Contact Admin quick button (students only) */}
        {!isAdmin && (
          <button
            onClick={() => setContactOpen(true)}
            className="hidden md:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-200 hover:text-white transition-all shadow-sm"
          >
            <Send className="w-3.5 h-3.5 text-blue-400" />
            Contact Staff
          </button>
        )}

        {/* Notification Bell with Dropdown */}
        <div className="relative" ref={notifRef}>
          <button
            onClick={() => {
              setNotifOpen((o) => !o);
              if (!notifOpen) fetchNotifs();
            }}
            className="relative p-2.5 rounded-xl text-gray-400 hover:text-white hover:bg-gray-800 border border-transparent hover:border-gray-700 transition-all"
            title="Notifications"
          >
            <Bell className="w-5 h-5" />
            {unread > 0 && (
              <span className="absolute top-1.5 right-1.5 w-4 h-4 bg-red-500 rounded-full text-[10px] font-bold text-white flex items-center justify-center animate-pulse">
                {unread > 9 ? "9+" : unread}
              </span>
            )}
          </button>

          {notifOpen && (
            <div className="absolute right-0 top-full mt-2 w-84 bg-gray-900 border border-gray-700/80 rounded-2xl shadow-2xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2">
              <div className="flex items-center justify-between p-3.5 border-b border-gray-800 bg-gray-900/90">
                <div className="flex items-center gap-2">
                  <Bell className="w-4 h-4 text-blue-400" />
                  <span className="text-sm font-bold text-white">Notifications</span>
                  {unread > 0 && (
                    <span className="text-[10px] bg-blue-500/20 text-blue-400 px-1.5 py-0.5 rounded-full font-bold">
                      {unread} new
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {unread > 0 && (
                    <button onClick={markAllRead} className="text-xs text-blue-400 hover:text-blue-300 font-medium">
                      Mark all read
                    </button>
                  )}
                  <button onClick={() => setNotifOpen(false)} className="text-gray-400 hover:text-white">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <div className="max-h-80 overflow-y-auto divide-y divide-gray-800/60">
                {notifications.length === 0 ? (
                  <div className="text-center text-gray-500 text-xs py-8 px-4">
                    <p className="font-medium">No recent notifications</p>
                    <p className="text-[10px] text-gray-600 mt-1">
                      You are all caught up on assignments and announcements.
                    </p>
                  </div>
                ) : (
                  notifications.map((n) => (
                    <div
                      key={n.id}
                      className={`p-3.5 transition-colors ${
                        !n.is_read ? "bg-blue-600/10 border-l-2 border-blue-500" : "hover:bg-gray-800/40"
                      }`}
                    >
                      <p className={`text-xs font-semibold ${n.is_read ? "text-gray-300" : "text-white"}`}>
                        {n.title}
                      </p>
                      <p className="text-[11px] text-gray-400 mt-1 line-clamp-2 leading-relaxed">{n.message}</p>
                      <p className="text-[9px] text-gray-500 mt-1.5">
                        {new Date(n.created_at).toLocaleDateString(undefined, {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </p>
                    </div>
                  ))
                )}
              </div>

              <div className="p-2.5 border-t border-gray-800 bg-gray-950/40 text-center">
                <Link
                  href="/notifications"
                  onClick={() => setNotifOpen(false)}
                  className="text-xs text-blue-400 hover:text-blue-300 font-semibold"
                >
                  Open Notification Center →
                </Link>
              </div>
            </div>
          )}
        </div>

        {/* ── User Identity Dropdown Menu ── */}
        <div className="relative" ref={profileRef}>
          <button
            onClick={() => setProfileOpen((o) => !o)}
            className="flex items-center gap-2 p-1.5 pl-2.5 rounded-xl hover:bg-gray-800 border border-gray-800 hover:border-gray-700 transition-all"
          >
            <div
              className={`w-7 h-7 rounded-lg flex items-center justify-center font-bold text-xs ${
                isAdmin
                  ? "bg-gradient-to-tr from-amber-600 to-yellow-500 text-black"
                  : "bg-gradient-to-tr from-blue-600 to-indigo-500 text-white"
              }`}
            >
              {user?.full_name?.charAt(0).toUpperCase() || "U"}
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
          </button>

          {profileOpen && (
            <div className="absolute right-0 top-full mt-2 w-72 bg-gray-900 border border-gray-700/80 rounded-2xl shadow-2xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2">
              {/* Identity Header Card */}
              <div className="p-4 border-b border-gray-800 bg-gradient-to-br from-gray-850 to-gray-900">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-12 h-12 rounded-2xl flex items-center justify-center font-bold text-lg shadow-lg ${
                      isAdmin
                        ? "bg-gradient-to-tr from-amber-600 to-yellow-500 text-black shadow-amber-500/20"
                        : "bg-gradient-to-tr from-blue-600 to-indigo-500 text-white shadow-blue-500/20"
                    }`}
                  >
                    {user?.full_name?.charAt(0).toUpperCase() || "U"}
                  </div>
                  <div className="overflow-hidden">
                    <p className="text-sm font-bold text-white truncate">{user?.full_name}</p>
                    <p className="text-xs text-gray-400 truncate">{user?.email}</p>
                    <span
                      className={`inline-block mt-1 text-[9px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded-md ${
                        isAdmin ? "bg-amber-500/20 text-amber-300" : "bg-blue-500/20 text-blue-300"
                      }`}
                    >
                      {isAdmin ? "Administrator" : "Enrolled Student"}
                    </span>
                  </div>
                </div>

                {/* Additional identity specifics */}
                {!isAdmin && (
                  <div className="mt-3 pt-3 border-t border-gray-800/80 grid grid-cols-2 gap-2 text-[11px]">
                    <div className="bg-gray-800/50 p-1.5 rounded-lg">
                      <span className="text-gray-500 block text-[9px]">Student ID</span>
                      <span className="font-mono font-semibold text-gray-200 truncate block">
                        {user?.student_id || "Unassigned"}
                      </span>
                    </div>
                    <div className="bg-gray-800/50 p-1.5 rounded-lg">
                      <span className="text-gray-500 block text-[9px]">Course / Class</span>
                      <span className="font-semibold text-gray-200 truncate block">
                        {user?.class_name || user?.course || "General"}
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* Navigation links */}
              <div className="p-2 space-y-1">
                <Link
                  href="/profile"
                  onClick={() => setProfileOpen(false)}
                  className="flex items-center gap-2.5 px-3 py-2 text-xs font-medium text-gray-300 hover:text-white hover:bg-gray-800/80 rounded-xl transition-colors"
                >
                  <User className="w-4 h-4 text-blue-400" />
                  My Identity & Profile
                </Link>

                {isAdmin && (
                  <Link
                    href="/admin/dashboard"
                    onClick={() => setProfileOpen(false)}
                    className="flex items-center gap-2.5 px-3 py-2 text-xs font-medium text-amber-300 hover:text-amber-200 hover:bg-amber-500/10 rounded-xl transition-colors"
                  >
                    <Shield className="w-4 h-4 text-amber-400" />
                    Admin Command Hub
                  </Link>
                )}

                {!isAdmin && (
                  <button
                    onClick={() => {
                      setProfileOpen(false);
                      setContactOpen(true);
                    }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 text-xs font-medium text-gray-300 hover:text-white hover:bg-gray-800/80 rounded-xl transition-colors text-left"
                  >
                    <Send className="w-4 h-4 text-indigo-400" />
                    Contact Staff / Administration
                  </button>
                )}
              </div>

              {/* Logout button */}
              <div className="p-2 border-t border-gray-800 bg-gray-950/30">
                <button
                  onClick={() => {
                    setProfileOpen(false);
                    logout();
                    toast.success("Successfully signed out");
                  }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 text-xs font-semibold text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-xl transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  Sign Out from StudyBuddy
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Contact Staff Modal (Student -> Admin) ── */}
      {contactOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between p-5 border-b border-gray-800 bg-gray-900/90">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-blue-500/20 text-blue-400 flex items-center justify-center font-bold">
                  <Send className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Contact Staff & Administration</h3>
                  <p className="text-xs text-gray-400">Direct message to teachers and administration</p>
                </div>
              </div>
              <button
                onClick={() => setContactOpen(false)}
                className="text-gray-400 hover:text-white p-1 rounded-lg hover:bg-gray-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleContactSubmit} className="p-5 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Inquiry Category</label>
                <select
                  value={contactCategory}
                  onChange={(e) => setContactCategory(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 text-white rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-blue-500"
                >
                  <option value="academic">Academic & Subject Question</option>
                  <option value="assignment">Assignment / Grade Issue</option>
                  <option value="technical">Technical Support</option>
                  <option value="general">Administrative Inquiry</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Subject / Title</label>
                <input
                  type="text"
                  placeholder="e.g. Question regarding Assignment 2 deadline"
                  value={contactTitle}
                  onChange={(e) => setContactTitle(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 text-white rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Message</label>
                <textarea
                  rows={4}
                  placeholder="Describe your inquiry, question, or issue in detail..."
                  value={contactMessage}
                  onChange={(e) => setContactMessage(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 text-white rounded-xl p-3 text-xs focus:outline-none focus:border-blue-500 resize-none leading-relaxed"
                  required
                />
              </div>

              <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-3 text-[11px] text-blue-300 flex items-start gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-blue-400 mt-0.5" />
                <span>
                  This notification will be delivered to the administration inbox and dispatched to staff email
                  notification accounts.
                </span>
              </div>

              <div className="flex justify-end gap-2.5 pt-2">
                <button
                  type="button"
                  onClick={() => setContactOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-750 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={contactSending}
                  className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-blue-600 hover:bg-blue-500 transition-colors flex items-center gap-1.5 disabled:opacity-50"
                >
                  {contactSending ? "Delivering..." : "Send Message →"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </header>
  );
}
