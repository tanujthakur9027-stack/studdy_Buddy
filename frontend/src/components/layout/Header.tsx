"use client";
import { useEffect, useState } from "react";
import { Bell, X } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import Link from "next/link";

interface Notification {
  id: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
  notif_type: string;
}

export default function Header() {
  const { user } = useAuth();
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const fetchCount = async () => {
    try {
      const { data } = await api.get("/api/notifications/unread-count", { withCredentials: true });
      setUnread(data.count);
    } catch { /* ignore */ }
  };

  const fetchNotifs = async () => {
    try {
      const { data } = await api.get("/api/notifications?page_size=10", { withCredentials: true });
      setNotifications(data);
    } catch { /* ignore */ }
  };

  const markAllRead = async () => {
    try {
      await api.patch("/api/notifications/read-all", {}, { withCredentials: true });
      setUnread(0);
      setNotifications((n) => n.map((x) => ({ ...x, is_read: true })));
    } catch { /* ignore */ }
  };

  useEffect(() => {
    if (!user) return;
    fetchCount();
    const interval = setInterval(fetchCount, 30_000);
    return () => clearInterval(interval);
  }, [user]);

  return (
    <header className="h-14 bg-gray-900 border-b border-gray-800 flex items-center justify-between px-6 shrink-0">
      <div className="text-sm text-gray-400">
        Welcome back, <span className="text-white font-medium">{user?.full_name}</span>
      </div>

      <div className="flex items-center gap-3">
        {/* Notification bell */}
        <div className="relative">
          <button
            onClick={() => { setOpen((o) => !o); if (!open) fetchNotifs(); }}
            className="relative p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
          >
            <Bell className="w-5 h-5" />
            {unread > 0 && (
              <span className="absolute top-1 right-1 w-4 h-4 bg-red-500 rounded-full text-[10px] font-bold text-white flex items-center justify-center">
                {unread > 9 ? "9+" : unread}
              </span>
            )}
          </button>

          {open && (
            <div className="absolute right-0 top-full mt-2 w-80 bg-gray-900 border border-gray-700 rounded-xl shadow-xl z-50">
              <div className="flex items-center justify-between p-3 border-b border-gray-800">
                <span className="text-sm font-semibold text-white">Notifications</span>
                <div className="flex items-center gap-2">
                  {unread > 0 && (
                    <button onClick={markAllRead} className="text-xs text-blue-400 hover:text-blue-300">
                      Mark all read
                    </button>
                  )}
                  <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-white">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <div className="max-h-80 overflow-y-auto">
                {notifications.length === 0 ? (
                  <p className="text-center text-gray-500 text-sm py-8">No notifications</p>
                ) : (
                  notifications.map((n) => (
                    <div
                      key={n.id}
                      className={`p-3 border-b border-gray-800 last:border-0 ${!n.is_read ? "bg-blue-500/5" : ""}`}
                    >
                      <p className={`text-sm font-medium ${n.is_read ? "text-gray-300" : "text-white"}`}>
                        {n.title}
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{n.message}</p>
                      <p className="text-[10px] text-gray-600 mt-1">{new Date(n.created_at).toLocaleDateString()}</p>
                    </div>
                  ))
                )}
              </div>
              <div className="p-2 border-t border-gray-800">
                <Link href="/notifications" onClick={() => setOpen(false)} className="block text-center text-xs text-blue-400 hover:text-blue-300 py-1">
                  View all notifications
                </Link>
              </div>
            </div>
          )}
        </div>

        {/* User avatar */}
        <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white text-sm font-semibold">
          {user?.full_name?.charAt(0).toUpperCase() || "U"}
        </div>
      </div>
    </header>
  );
}
