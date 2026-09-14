"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Users, Search, UserPlus, UserCheck, X } from "lucide-react";
import toast from "react-hot-toast";

interface Student { user_id: string; full_name: string; student_id: string; course: string; semester: string; profile_photo_url?: string; }
interface ConnectionReq { id: string; from_user_id: string; from_user_name: string; created_at: string; }
interface Connection { connection_id: string; user_id: string; full_name: string; student_id: string; course: string; }

export default function ConnectionsPage() {
  const [connections, setConnections] = useState<Connection[]>([]);
  const [incoming, setIncoming] = useState<ConnectionReq[]>([]);
  const [search, setSearch] = useState("");
  const [results, setResults] = useState<Student[]>([]);
  const [tab, setTab] = useState<"connections" | "search" | "requests">("connections");

  const load = () => {
    api.get("/api/connections", { withCredentials: true }).then(r => setConnections(r.data)).catch(() => {});
    api.get("/api/connections/requests/incoming", { withCredentials: true }).then(r => setIncoming(r.data)).catch(() => {});
  };

  useEffect(() => { load(); }, []);

  const doSearch = () => {
    if (!search.trim()) return;
    api.get(`/api/students/search?q=${encodeURIComponent(search)}`, { withCredentials: true })
      .then(r => setResults(r.data))
      .catch(() => toast.error("Search failed"));
  };

  const sendRequest = async (userId: string) => {
    try {
      await api.post(`/api/connections/request?to_user_id=${userId}`, {}, { withCredentials: true });
      toast.success("Connection request sent!");
      setResults(r => r.filter(s => s.user_id !== userId));
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed");
    }
  };

  const respond = async (reqId: string, accept: boolean) => {
    try {
      await api.patch(`/api/connections/${reqId}/respond?accept=${accept}`, {}, { withCredentials: true });
      setIncoming(i => i.filter(r => r.id !== reqId));
      if (accept) { load(); toast.success("Connected!"); } else toast.success("Request rejected");
    } catch { toast.error("Failed"); }
  };

  const remove = async (connId: string) => {
    if (!confirm("Remove this connection?")) return;
    try {
      await api.delete(`/api/connections/${connId}`, { withCredentials: true });
      setConnections(c => c.filter(x => x.connection_id !== connId));
      toast.success("Connection removed");
    } catch { toast.error("Failed"); }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white flex items-center gap-2"><Users className="w-6 h-6 text-blue-400" />Connections</h1>

      {/* Tabs */}
      <div className="flex gap-2">
        {(["connections", "search", "requests"] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium capitalize transition-colors relative ${tab === t ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-400 hover:text-white"}`}>
            {t}
            {t === "requests" && incoming.length > 0 && (
              <span className="ml-1.5 bg-red-500 text-white text-xs rounded-full px-1.5 py-0.5">{incoming.length}</span>
            )}
          </button>
        ))}
      </div>

      {tab === "connections" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {connections.length === 0 ? (
            <div className="col-span-2 bg-gray-900 border border-gray-800 rounded-2xl p-12 text-center">
              <Users className="w-12 h-12 text-gray-700 mx-auto mb-4" />
              <p className="text-gray-400">No connections yet</p>
              <button onClick={() => setTab("search")} className="mt-3 text-blue-400 text-sm hover:text-blue-300">Find students →</button>
            </div>
          ) : connections.map(c => (
            <div key={c.connection_id} className="bg-gray-900 border border-gray-800 rounded-2xl p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-600/20 rounded-full flex items-center justify-center text-blue-400 font-bold">
                  {c.full_name.charAt(0)}
                </div>
                <div>
                  <p className="font-semibold text-white text-sm">{c.full_name}</p>
                  <p className="text-xs text-gray-500">{c.student_id} • {c.course}</p>
                </div>
              </div>
              <button onClick={() => remove(c.connection_id)} className="text-gray-600 hover:text-red-400"><X className="w-4 h-4" /></button>
            </div>
          ))}
        </div>
      )}

      {tab === "search" && (
        <div className="space-y-4">
          <div className="flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-500" />
              <input value={search} onChange={e => setSearch(e.target.value)} onKeyDown={e => e.key === "Enter" && doSearch()}
                placeholder="Search by name, student ID, course..." className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-xl text-white text-sm focus:outline-none focus:border-blue-500" />
            </div>
            <button onClick={doSearch} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-xl">Search</button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {results.map(s => (
              <div key={s.user_id} className="bg-gray-900 border border-gray-800 rounded-2xl p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-purple-600/20 rounded-full flex items-center justify-center text-purple-400 font-bold">
                    {s.full_name.charAt(0)}
                  </div>
                  <div>
                    <p className="font-semibold text-white text-sm">{s.full_name}</p>
                    <p className="text-xs text-gray-500">{s.student_id} • {s.course}</p>
                  </div>
                </div>
                <button onClick={() => sendRequest(s.user_id)} className="flex items-center gap-1 text-xs bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg">
                  <UserPlus className="w-3 h-3" />Connect
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === "requests" && (
        <div className="space-y-3">
          {incoming.length === 0 ? (
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-12 text-center">
              <UserCheck className="w-12 h-12 text-gray-700 mx-auto mb-4" />
              <p className="text-gray-400">No pending requests</p>
            </div>
          ) : incoming.map(r => (
            <div key={r.id} className="bg-gray-900 border border-gray-800 rounded-2xl p-4 flex items-center justify-between">
              <div>
                <p className="font-semibold text-white">{r.from_user_name}</p>
                <p className="text-xs text-gray-500">{new Date(r.created_at).toLocaleDateString()}</p>
              </div>
              <div className="flex gap-2">
                <button onClick={() => respond(r.id, true)} className="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white text-xs rounded-lg">Accept</button>
                <button onClick={() => respond(r.id, false)} className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white text-xs rounded-lg">Reject</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
