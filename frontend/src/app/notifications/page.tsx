"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Bell, Check, CheckCheck } from "lucide-react";
import toast from "react-hot-toast";

interface Notification {
  id: string;
  title: string;
  message: string;
  notif_type: string;
  is_read: boolean;
  created_at: string;
}

const typeIcon: Record<string, string> = {
  assignment: "📋",
  submission: "✅",
  marks: "📊",
  timetable: "📅",
  announcement: "📢",
  note: "📝",
  connection: "🤝",
  registration: "🎓",
  general: "🔔",
};

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    api.get("/api/notifications?page_size=50", { withCredentials: true })
      .then(r => setNotifications(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const markRead = async (id: string) => {
    try {
      await api.patch(`/api/notifications/${id}/read`, {}, { withCredentials: true });
      setNotifications(n => n.map(x => x.id === id ? { ...x, is_read: true } : x));
    } catch { /* ignore */ }
  };

  const markAllRead = async () => {
    try {
      await api.patch("/api/notifications/read-all", {}, { withCredentials: true });
      setNotifications(n => n.map(x => ({ ...x, is_read: true })));
      toast.success("All marked as read");
    } catch { /* ignore */ }
  };

  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Bell className="w-6 h-6 text-purple-400" />Notifications
          {unreadCount > 0 && <span className="text-sm font-normal text-purple-400 bg-purple-500/20 px-2 py-0.5 rounded-full">{unreadCount} unread</span>}
        </h1>
        {unreadCount > 0 && (
          <button onClick={markAllRead} className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300">
            <CheckCheck className="w-4 h-4" />Mark all read
          </button>
        )}
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" /></div>
      ) : notifications.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-12 text-center">
          <Bell className="w-12 h-12 text-gray-700 mx-auto mb-4" />
          <p className="text-gray-400">No notifications yet</p>
        </div>
      ) : (
        <div className="space-y-2">
          {notifications.map((n) => (
            <div
              key={n.id}
              className={`bg-gray-900 border rounded-2xl p-4 flex items-start gap-4 transition-colors ${!n.is_read ? "border-blue-600/30 bg-blue-500/5" : "border-gray-800"}`}
            >
              <div className="text-2xl shrink-0 mt-0.5">{typeIcon[n.notif_type] || "🔔"}</div>
              <div className="flex-1 min-w-0">
                <p className={`font-semibold text-sm ${n.is_read ? "text-gray-300" : "text-white"}`}>{n.title}</p>
                <p className="text-sm text-gray-400 mt-0.5">{n.message}</p>
                <p className="text-xs text-gray-600 mt-1">{new Date(n.created_at).toLocaleString()}</p>
              </div>
              {!n.is_read && (
                <button onClick={() => markRead(n.id)} className="shrink-0 p-1.5 text-gray-500 hover:text-blue-400 rounded-lg hover:bg-blue-500/10 transition-colors" title="Mark as read">
                  <Check className="w-4 h-4" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
