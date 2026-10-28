"use client";

import { useEffect, useState, useMemo } from "react";
import { api, broadcastNotification, fetchAdminContacts, AdminContactInquiry } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import {
  ShieldAlert,
  LogIn,
  LayoutDashboard,
  Users,
  ClipboardList,
  BarChart2,
  ArrowRight,
  Plus,
  Send,
  Mail,
  Bell,
  Inbox,
  CheckCircle2,
  Server,
  Database,
  Sparkles,
  RefreshCw,
  Search,
  Clock,
  X,
  Building2,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import toast from "react-hot-toast";

interface SystemHealth {
  status: string;
  provider: string;
  model: string;
  database: string;
  sentry: string;
  smtp?: string;
  indexed_documents: number;
  faiss_vectors: number;
  rate_limit: string;
}

interface ClassItem {
  id: string;
  name: string;
  course: string;
}

interface AssignmentItem {
  id: string;
  title: string;
  is_published: boolean;
}

interface SubmissionItem {
  id: string;
  student_name: string;
  status: string;
}

export default function AdminDashboard() {
  const { user, loading: authLoading } = useAuth();

  // ── States ──────────────────────────────────────────────────────────────────
  const [stats, setStats] = useState({ total: 0, active: 0 });
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [assignments, setAssignments] = useState<AssignmentItem[]>([]);
  const [submissions, setSubmissions] = useState<SubmissionItem[]>([]);
  const [inquiries, setInquiries] = useState<AdminContactInquiry[]>([]);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Active view tab
  const [activeTab, setActiveTab] = useState<"inquiries" | "overview">("overview");

  // Inquiries filter & search
  const [inquirySearch, setInquirySearch] = useState("");
  const [inquiryFilter, setInquiryFilter] = useState<"all" | "unread" | "read">("all");

  // Broadcast modal state
  const [showBroadcastModal, setShowBroadcastModal] = useState(false);
  const [broadcastTarget, setBroadcastTarget] = useState<"all" | "class" | "student">("all");
  const [broadcastTargetId, setBroadcastTargetId] = useState("");
  const [broadcastTitle, setBroadcastTitle] = useState("");
  const [broadcastMessage, setBroadcastMessage] = useState("");
  const [broadcastSendEmail, setBroadcastSendEmail] = useState(false);
  const [broadcasting, setBroadcasting] = useState(false);

  // ── Data Loader ─────────────────────────────────────────────────────────────
  const loadDashboardData = async (isManual = false) => {
    if (isManual) setRefreshing(true);
    else setLoading(true);

    try {
      const [statsRes, classesRes, assignRes, subsRes, inqRes, healthRes] = await Promise.allSettled([
        api.get("/api/admin/students/count", { withCredentials: true }),
        api.get("/api/admin/classes", { withCredentials: true }),
        api.get("/api/admin/assignments", { withCredentials: true }),
        api.get("/api/admin/submissions?page_size=10", { withCredentials: true }),
        fetchAdminContacts(),
        api.get("/health"),
      ]);

      if (statsRes.status === "fulfilled") setStats(statsRes.value.data);
      if (classesRes.status === "fulfilled") setClasses(classesRes.value.data);
      if (assignRes.status === "fulfilled") setAssignments(assignRes.value.data.slice(0, 8));
      if (subsRes.status === "fulfilled") setSubmissions(subsRes.value.data);
      if (inqRes.status === "fulfilled") setInquiries(inqRes.value);
      if (healthRes.status === "fulfilled") setHealth(healthRes.value.data);
    } catch {
      toast.error("Error loading dashboard metrics");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  // ── Mark Inquiry Read ───────────────────────────────────────────────────────
  const handleMarkInquiryRead = async (inqId: string) => {
    try {
      await api.patch(`/api/notifications/${inqId}/read`);
      setInquiries((prev) =>
        prev.map((item) => (item.id === inqId ? { ...item, is_read: true } : item))
      );
      toast.success("Inquiry marked as reviewed");
    } catch {
      toast.error("Failed to update status");
    }
  };

  // ── Send Broadcast ──────────────────────────────────────────────────────────
  const handleSendBroadcast = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!broadcastTitle.trim() || !broadcastMessage.trim()) {
      toast.error("Please provide both a title and message.");
      return;
    }
    if (broadcastTarget !== "all" && !broadcastTargetId.trim()) {
      toast.error("Please specify target class or student ID.");
      return;
    }

    setBroadcasting(true);
    try {
      const res = await broadcastNotification({
        title: broadcastTitle.trim(),
        message: broadcastMessage.trim(),
        target: broadcastTarget,
        target_id: broadcastTarget !== "all" ? broadcastTargetId.trim() : undefined,
        send_email: broadcastSendEmail,
      });

      toast.success(
        `Dispatched! ${res.in_app_count} in-app notification(s) created.${
          res.emails_sent > 0 ? ` ${res.emails_sent} email(s) sent via SMTP.` : ""
        }`
      );

      // Reset modal
      setShowBroadcastModal(false);
      setBroadcastTitle("");
      setBroadcastMessage("");
      setBroadcastTarget("all");
      setBroadcastTargetId("");
      setBroadcastSendEmail(false);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(msg || "Failed to dispatch broadcast");
    } finally {
      setBroadcasting(false);
    }
  };

  // Quick reply directly to an inquiry
  const handleQuickReply = (inquiry: AdminContactInquiry) => {
    setBroadcastTarget("student");
    setBroadcastTargetId(inquiry.sender_id || "");
    setBroadcastTitle(`Re: ${inquiry.title}`);
    setBroadcastMessage(`Hello ${inquiry.sender_name || "Student"},\n\nIn response to your query regarding "${inquiry.title}":\n\n`);
    setBroadcastSendEmail(true);
    setShowBroadcastModal(true);
  };

  // ── Filtered Inquiries ─────────────────────────────────────────────────────
  const filteredInquiries = useMemo(() => {
    return inquiries.filter((inq) => {
      const matchesSearch =
        inq.title.toLowerCase().includes(inquirySearch.toLowerCase()) ||
        inq.message.toLowerCase().includes(inquirySearch.toLowerCase()) ||
        (inq.sender_name || "").toLowerCase().includes(inquirySearch.toLowerCase()) ||
        (inq.student_id || "").toLowerCase().includes(inquirySearch.toLowerCase());

      if (!matchesSearch) return false;
      if (inquiryFilter === "unread") return !inq.is_read;
      if (inquiryFilter === "read") return inq.is_read;
      return true;
    });
  }, [inquiries, inquirySearch, inquiryFilter]);

  const unreadInquiriesCount = useMemo(() => {
    return inquiries.filter((i) => !i.is_read).length;
  }, [inquiries]);

  const pendingSubmissions = useMemo(() => {
    return submissions.filter((s) => s.status !== "evaluated").length;
  }, [submissions]);

  const publishedAssignments = useMemo(() => {
    return assignments.filter((a) => a.is_published).length;
  }, [assignments]);

  // ── Metrics ─────────────────────────────────────────────────────────────────
  const metricCards = [
    {
      label: "Total Students",
      value: stats.total,
      sub: `${stats.active} Active`,
      icon: Users,
      color: "text-blue-400",
      bg: "bg-blue-500/10",
      border: "border-blue-500/20",
      href: "/admin/students",
    },
    {
      label: "Classes & Batches",
      value: classes.length,
      sub: "Active streams",
      icon: Building2,
      color: "text-indigo-400",
      bg: "bg-indigo-500/10",
      border: "border-indigo-500/20",
      href: "/admin/classes",
    },
    {
      label: "Assignments",
      value: assignments.length,
      sub: `${publishedAssignments} Published`,
      icon: ClipboardList,
      color: "text-purple-400",
      bg: "bg-purple-500/10",
      border: "border-purple-500/20",
      href: "/admin/assignments",
    },
    {
      label: "Pending Submissions",
      value: pendingSubmissions,
      sub: `${submissions.length} Total`,
      icon: BarChart2,
      color: "text-amber-400",
      bg: "bg-amber-500/10",
      border: "border-amber-500/20",
      href: "/admin/submissions",
    },
    {
      label: "Student Inquiries",
      value: inquiries.length,
      sub: `${unreadInquiriesCount} Unread`,
      icon: Mail,
      color: "text-emerald-400",
      bg: "bg-emerald-500/10",
      border: "border-emerald-500/20",
      onClick: () => setActiveTab("inquiries"),
    },
    {
      label: "AI RAG Knowledge Base",
      value: health?.indexed_documents ?? 0,
      sub: `${health?.faiss_vectors ?? 0} vectors active`,
      icon: Sparkles,
      color: "text-cyan-400",
      bg: "bg-cyan-500/10",
      border: "border-cyan-500/20",
      href: "/admin/assignments",
    },
  ];

  const quickActions = [
    { href: "/admin/students", label: "Register / Manage Students", icon: Users },
    { href: "/admin/assignments", label: "Create Assignment", icon: ClipboardList },
    { href: "/admin/classes", label: "Manage Classes & Batches", icon: Building2 },
    { href: "/admin/marks", label: "Enter / Publish Marks", icon: BarChart2 },
    { href: "/admin/timetable", label: "Configure Timetable", icon: Clock },
    { href: "/admin/announcements", label: "Campus Announcements", icon: Bell },
  ];

  if (!authLoading && (!user || user.role !== "admin")) {
    return (
      <div className="max-w-md mx-auto my-12 p-8 bg-gray-900 border border-gray-800 rounded-3xl text-center shadow-2xl">
        <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center">
          <ShieldAlert className="w-7 h-7" />
        </div>
        <h2 className="text-xl font-bold text-white mb-2">Administrator Access Required</h2>
        <p className="text-xs text-gray-400 mb-6 leading-relaxed">
          The Admin Command Hub is restricted to verified staff and faculty administrators. Please sign in with your administrative credentials to continue.
        </p>
        <Link
          href="/login"
          className="inline-flex items-center justify-center gap-2 w-full py-3 px-4 rounded-xl bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-500 hover:to-yellow-500 text-black font-bold text-xs shadow-lg shadow-amber-600/20 transition-all"
        >
          <LogIn className="w-4 h-4" />
          Sign In as Administrator
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* ── Top Bar / Header ────────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-gray-900 via-gray-900 to-indigo-950/40 p-6 rounded-3xl border border-gray-800 shadow-xl">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-indigo-500/20 border border-indigo-500/30 text-indigo-400">
              <ShieldCheck className="w-7 h-7" />
            </div>
            <div>
              <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
                Administrator Hub
                <span className="text-[11px] font-bold uppercase tracking-widest px-2.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  Operations & Comms
                </span>
              </h1>
              <p className="text-gray-400 text-sm mt-0.5">
                Complete oversight over academic cohorts, communications, email dispatches, and student requests.
              </p>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={() => loadDashboardData(true)}
            disabled={refreshing}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-semibold border border-gray-700 transition-all disabled:opacity-50"
            title="Refresh metrics and health"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </button>

          <button
            onClick={() => setShowBroadcastModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 via-blue-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 text-white text-xs font-bold shadow-lg shadow-indigo-600/30 transition-all"
          >
            <Send className="w-3.5 h-3.5" />
            Broadcast Notification & Email
          </button>
        </div>
      </div>

      {/* ── System Diagnostics Bar ──────────────────────────────────────── */}
      {health && (
        <div className="bg-gray-900/80 border border-gray-800 rounded-2xl p-4 flex flex-wrap items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-3">
            <span className="relative flex h-2.5 w-2.5">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${health.status === "ok" ? "bg-green-400" : "bg-amber-400"}`}></span>
              <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${health.status === "ok" ? "bg-green-500" : "bg-amber-500"}`}></span>
            </span>
            <span className="text-gray-300 font-semibold flex items-center gap-1.5">
              <Server className="w-3.5 h-3.5 text-gray-400" />
              API: <strong className="text-white uppercase font-mono">{health.status}</strong>
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-gray-400">
            <Database className="w-3.5 h-3.5 text-indigo-400" />
            Database: <span className="text-gray-200 font-mono">{health.database}</span>
          </div>

          <div className="flex items-center gap-1.5 text-gray-400">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            AI Provider: <span className="text-gray-200 font-mono">{health.provider} ({health.model})</span>
          </div>

          <div className="flex items-center gap-1.5 text-gray-400">
            <Mail className="w-3.5 h-3.5 text-amber-400" />
            SMTP Relay:{" "}
            <span
              className={`font-mono px-2 py-0.5 rounded-md ${
                health.smtp === "configured"
                  ? "bg-green-500/20 text-green-300"
                  : "bg-gray-800 text-gray-400"
              }`}
            >
              {health.smtp === "configured" ? "Active" : "Simulation / Log Mode"}
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-gray-400">
            <Clock className="w-3.5 h-3.5 text-gray-400" />
            Rate Limit: <span className="text-gray-200 font-mono">{health.rate_limit}</span>
          </div>
        </div>
      )}

      {/* ── Key Metrics Grid ────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
        {metricCards.map((card) => {
          const Content = (
            <div
              className={`bg-gray-900 border ${card.border} rounded-2xl p-4 transition-all hover:border-gray-700 hover:shadow-lg hover:-translate-y-0.5 cursor-pointer flex flex-col justify-between h-full`}
              onClick={card.onClick}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs text-gray-400 font-medium">{card.label}</span>
                <div className={`w-8 h-8 ${card.bg} rounded-xl flex items-center justify-center shrink-0`}>
                  <card.icon className={`w-4 h-4 ${card.color}`} />
                </div>
              </div>
              <div>
                <p className="text-2xl font-black text-white">{card.value}</p>
                <p className="text-[11px] text-gray-500 mt-0.5 font-medium">{card.sub}</p>
              </div>
            </div>
          );

          return card.href ? (
            <Link key={card.label} href={card.href} className="block">
              {Content}
            </Link>
          ) : (
            <div key={card.label}>{Content}</div>
          );
        })}
      </div>

      {/* ── Tabs Navigation ─────────────────────────────────────────────── */}
      <div className="flex items-center gap-2 border-b border-gray-800 pb-2">
        <button
          onClick={() => setActiveTab("overview")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeTab === "overview"
              ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
              : "text-gray-400 hover:text-gray-200 hover:bg-gray-900"
          }`}
        >
          <LayoutDashboard className="w-4 h-4" />
          Academics & Quick Actions
        </button>

        <button
          onClick={() => setActiveTab("inquiries")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all relative ${
            activeTab === "inquiries"
              ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
              : "text-gray-400 hover:text-gray-200 hover:bg-gray-900"
          }`}
        >
          <Inbox className="w-4 h-4" />
          Student Contact Inquiries
          {unreadInquiriesCount > 0 && (
            <span className="ml-1 px-1.5 py-0.2 rounded-full bg-emerald-500 text-gray-950 font-black text-[10px]">
              {unreadInquiriesCount}
            </span>
          )}
        </button>
      </div>

      {/* ── Tab Content: Overview ───────────────────────────────────────── */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Recent Assignments */}
            <div className="bg-gray-900 border border-gray-800 rounded-3xl p-5 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="font-bold text-white text-sm flex items-center gap-2">
                    <ClipboardList className="w-4 h-4 text-purple-400" />
                    Recent Assignments
                  </h2>
                  <Link
                    href="/admin/assignments"
                    className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-semibold"
                  >
                    View all <ArrowRight className="w-3 h-3" />
                  </Link>
                </div>
                {assignments.length === 0 ? (
                  <p className="text-gray-500 text-xs text-center py-8">No assignments created yet</p>
                ) : (
                  <ul className="space-y-2">
                    {assignments.slice(0, 5).map((a) => (
                      <li
                        key={a.id}
                        className="flex items-center justify-between p-2.5 rounded-xl bg-gray-800/40 border border-gray-800/60"
                      >
                        <div className="min-w-0 pr-2">
                          <p className="text-xs font-medium text-gray-200 truncate">{a.title}</p>
                        </div>
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider shrink-0 ${
                            a.is_published
                              ? "bg-green-500/20 text-green-400 border border-green-500/30"
                              : "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                          }`}
                        >
                          {a.is_published ? "Published" : "Draft"}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <Link
                href="/admin/assignments"
                className="mt-4 block text-center py-2 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-semibold border border-gray-700 transition-colors"
              >
                + Create New Assignment
              </Link>
            </div>

            {/* Recent Submissions */}
            <div className="bg-gray-900 border border-gray-800 rounded-3xl p-5 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="font-bold text-white text-sm flex items-center gap-2">
                    <BarChart2 className="w-4 h-4 text-amber-400" />
                    Submissions To Review
                  </h2>
                  <Link
                    href="/admin/submissions"
                    className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-semibold"
                  >
                    View all <ArrowRight className="w-3 h-3" />
                  </Link>
                </div>
                {submissions.length === 0 ? (
                  <p className="text-gray-500 text-xs text-center py-8">No submissions recorded</p>
                ) : (
                  <ul className="space-y-2">
                    {submissions.slice(0, 5).map((s) => (
                      <li
                        key={s.id}
                        className="flex items-center justify-between p-2.5 rounded-xl bg-gray-800/40 border border-gray-800/60"
                      >
                        <div className="min-w-0 pr-2">
                          <p className="text-xs font-medium text-gray-200 truncate">{s.student_name || "Student"}</p>
                          <p className="text-[10px] text-gray-500">ID: {s.id.slice(0, 8)}</p>
                        </div>
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider shrink-0 ${
                            s.status === "evaluated"
                              ? "bg-green-500/20 text-green-400 border border-green-500/30"
                              : "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                          }`}
                        >
                          {s.status}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <Link
                href="/admin/submissions"
                className="mt-4 block text-center py-2 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-semibold border border-gray-700 transition-colors"
              >
                Grade All Submissions
              </Link>
            </div>

            {/* Quick Actions Hub */}
            <div className="bg-gray-900 border border-gray-800 rounded-3xl p-5">
              <h2 className="font-bold text-white text-sm mb-4 flex items-center gap-2">
                <Plus className="w-4 h-4 text-cyan-400" />
                Administrative Shortcuts
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 gap-2">
                {quickActions.map((action) => (
                  <Link
                    key={action.href}
                    href={action.href}
                    className="flex items-center gap-3 p-3 bg-gray-800/60 hover:bg-gray-800 border border-gray-800 hover:border-gray-700 rounded-xl transition-all group"
                  >
                    <div className="w-7 h-7 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center shrink-0 group-hover:bg-indigo-500/20">
                      <action.icon className="w-3.5 h-3.5" />
                    </div>
                    <span className="text-xs font-medium text-gray-300 group-hover:text-white">
                      {action.label}
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 text-gray-600 ml-auto group-hover:text-gray-300 transition-colors" />
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab Content: Inquiries ──────────────────────────────────────── */}
      {activeTab === "inquiries" && (
        <div className="space-y-4">
          {/* Controls: Search and Filter */}
          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-4 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="relative flex-1 w-full sm:w-auto">
              <Search className="w-4 h-4 text-gray-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search by student name, roll number, title, or keyword..."
                value={inquirySearch}
                onChange={(e) => setInquirySearch(e.target.value)}
                className="w-full bg-gray-800/80 border border-gray-700/80 rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="flex items-center gap-2 self-end sm:self-auto">
              {(["all", "unread", "read"] as const).map((filter) => (
                <button
                  key={filter}
                  onClick={() => setInquiryFilter(filter)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold capitalize transition-all ${
                    inquiryFilter === filter
                      ? "bg-indigo-600 text-white"
                      : "bg-gray-800 text-gray-400 hover:text-white"
                  }`}
                >
                  {filter}
                </button>
              ))}
            </div>
          </div>

          {/* Inquiries list */}
          {filteredInquiries.length === 0 ? (
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-12 text-center">
              <Inbox className="w-10 h-10 text-gray-600 mx-auto mb-3" />
              <p className="text-white font-semibold text-sm">No Student Inquiries Found</p>
              <p className="text-gray-500 text-xs mt-1">
                When students use the &quot;Contact Staff / Support&quot; channel, their queries will appear here.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredInquiries.map((inq) => (
                <div
                  key={inq.id}
                  className={`bg-gray-900 border rounded-2xl p-5 flex flex-col justify-between transition-all ${
                    inq.is_read
                      ? "border-gray-800/80 opacity-80"
                      : "border-indigo-500/30 bg-gradient-to-br from-gray-900 to-indigo-950/20 shadow-md"
                  }`}
                >
                  <div>
                    {/* Header info */}
                    <div className="flex items-start justify-between gap-2 mb-3">
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-bold text-white text-sm">{inq.sender_name || "Student"}</span>
                          {inq.student_id && (
                            <span className="font-mono text-[10px] bg-gray-800 border border-gray-700 px-2 py-0.5 rounded-md text-gray-300">
                              {inq.student_id}
                            </span>
                          )}
                          {!inq.is_read && (
                            <span className="flex items-center gap-1 text-[10px] font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                              New
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-gray-400 mt-0.5">{inq.sender_email}</p>
                      </div>

                      <span className="text-[10px] text-gray-500 whitespace-nowrap">
                        {new Date(inq.created_at).toLocaleString([], {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    </div>

                    {/* Subject & Message */}
                    <div className="mb-4">
                      <p className="text-xs font-bold text-indigo-300 mb-1">{inq.title}</p>
                      <p className="text-xs text-gray-300 whitespace-pre-wrap leading-relaxed bg-gray-950/50 p-3 rounded-xl border border-gray-800/80">
                        {inq.message}
                      </p>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center justify-end gap-2 pt-2 border-t border-gray-800/60">
                    {!inq.is_read && (
                      <button
                        onClick={() => handleMarkInquiryRead(inq.id)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-semibold border border-gray-700 transition-colors"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />
                        Mark Reviewed
                      </button>
                    )}

                    <button
                      onClick={() => handleQuickReply(inq)}
                      className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-all shadow-md shadow-indigo-600/30"
                    >
                      <Send className="w-3 h-3" />
                      Reply via Email / Notification
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Broadcast & Email Dispatch Modal ────────────────────────────── */}
      {showBroadcastModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
          <div className="bg-gray-900 border border-gray-700 rounded-3xl p-6 w-full max-w-xl shadow-2xl space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-gray-800">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-indigo-500/20 text-indigo-400">
                  <Send className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-white text-base">Broadcast Notification & Email</h3>
                  <p className="text-xs text-gray-400">Dispatch in-app notifications and SMTP emails directly to students</p>
                </div>
              </div>
              <button
                onClick={() => setShowBroadcastModal(false)}
                className="text-gray-500 hover:text-white p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSendBroadcast} className="space-y-4">
              {/* Target selector */}
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1.5">
                  Target Audience
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { id: "all", label: "All Students" },
                    { id: "class", label: "Specific Class" },
                    { id: "student", label: "Single Student" },
                  ].map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => {
                        setBroadcastTarget(t.id as "all" | "class" | "student");
                        setBroadcastTargetId("");
                      }}
                      className={`py-2 px-3 rounded-xl text-xs font-bold border transition-all ${
                        broadcastTarget === t.id
                          ? "bg-indigo-600 border-indigo-500 text-white shadow-md shadow-indigo-600/30"
                          : "bg-gray-800 border-gray-700 text-gray-400 hover:text-white"
                      }`}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Class selector */}
              {broadcastTarget === "class" && (
                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1.5">
                    Select Class / Batch
                  </label>
                  <select
                    value={broadcastTargetId}
                    onChange={(e) => setBroadcastTargetId(e.target.value)}
                    required
                    className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="">-- Choose Class --</option>
                    {classes.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name} {c.course ? `(${c.course})` : ""}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Student ID / User ID */}
              {broadcastTarget === "student" && (
                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1.5">
                    Recipient Student User ID
                  </label>
                  <input
                    type="text"
                    required
                    value={broadcastTargetId}
                    onChange={(e) => setBroadcastTargetId(e.target.value)}
                    placeholder="Enter student user account UUID"
                    className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
                  />
                </div>
              )}

              {/* Title */}
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1.5">
                  Notification Title / Subject
                </label>
                <input
                  type="text"
                  required
                  value={broadcastTitle}
                  onChange={(e) => setBroadcastTitle(e.target.value)}
                  placeholder="e.g. Midterm Examination Timetable Released"
                  className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              {/* Message */}
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1.5">
                  Message Body
                </label>
                <textarea
                  required
                  rows={4}
                  value={broadcastMessage}
                  onChange={(e) => setBroadcastMessage(e.target.value)}
                  placeholder="Write message details for in-app alert and email..."
                  className="w-full bg-gray-800 border border-gray-700 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-indigo-500 resize-none leading-relaxed"
                />
              </div>

              {/* Email dispatch toggle */}
              <label className="flex items-center gap-3 p-3 rounded-xl bg-gray-800/60 border border-gray-700/60 cursor-pointer hover:bg-gray-800 transition-colors">
                <input
                  type="checkbox"
                  checked={broadcastSendEmail}
                  onChange={(e) => setBroadcastSendEmail(e.target.checked)}
                  className="w-4 h-4 rounded text-indigo-600 bg-gray-900 border-gray-700 focus:ring-indigo-500 focus:ring-offset-gray-900"
                />
                <div className="text-xs">
                  <p className="font-bold text-white flex items-center gap-1.5">
                    <Mail className="w-3.5 h-3.5 text-amber-400" />
                    Also send via SMTP Email
                  </p>
                  <p className="text-gray-400 text-[11px]">
                    Dispatches formatted email to the registered email addresses of all selected students.
                  </p>
                </div>
              </label>

              {/* Modal buttons */}
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-800">
                <button
                  type="button"
                  onClick={() => setShowBroadcastModal(false)}
                  className="px-4 py-2 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-semibold transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={broadcasting}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 text-white text-xs font-bold shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50"
                >
                  <Send className={`w-3.5 h-3.5 ${broadcasting ? "animate-spin" : ""}`} />
                  {broadcasting ? "Dispatching..." : "Send Broadcast Now"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
