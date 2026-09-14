"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Settings, Camera } from "lucide-react";
import toast from "react-hot-toast";

interface Profile {
  user_id: string; email: string; full_name: string;
  student_id: string; phone: string; course: string;
  branch: string; semester: string; section: string;
  academic_year: string; dob?: string; profile_photo_url?: string;
}

export default function ProfilePage() {
  const { user, refreshUser } = useAuth();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [form, setForm] = useState({ full_name: "", phone: "", section: "", dob: "" });
  const [saving, setSaving] = useState(false);
  const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    api.get("/api/students/profile", { withCredentials: true })
      .then(r => { setProfile(r.data); setForm({ full_name: r.data.full_name, phone: r.data.phone, section: r.data.section, dob: r.data.dob || "" }); })
      .catch(() => {});
  }, []);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.patch("/api/students/profile", form, { withCredentials: true });
      toast.success("Profile updated!");
      await refreshUser();
    } catch { toast.error("Update failed"); }
    finally { setSaving(false); }
  };

  const uploadPhoto = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      const r = await api.post("/api/students/profile/photo", fd, { withCredentials: true, headers: { "Content-Type": "multipart/form-data" } });
      setProfile(p => p ? { ...p, profile_photo_url: r.data.profile_photo_url } : p);
      toast.success("Photo updated!");
    } catch { toast.error("Photo upload failed"); }
  };

  const inp = "w-full px-3 py-2.5 bg-gray-800 border border-gray-700 rounded-xl text-white text-sm focus:outline-none focus:border-blue-500";

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold text-white flex items-center gap-2"><Settings className="w-6 h-6 text-gray-400" />Profile</h1>

      {/* Avatar */}
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 flex items-center gap-6">
        <div className="relative">
          <div className="w-20 h-20 rounded-full bg-blue-600 flex items-center justify-center text-white text-3xl font-bold overflow-hidden">
            {profile?.profile_photo_url ? (
              <img src={`${BASE}${profile.profile_photo_url}`} alt="avatar" className="w-full h-full object-cover" />
            ) : (
              user?.full_name?.charAt(0).toUpperCase() || "U"
            )}
          </div>
          <label className="absolute bottom-0 right-0 w-7 h-7 bg-blue-600 rounded-full flex items-center justify-center cursor-pointer hover:bg-blue-700">
            <Camera className="w-3.5 h-3.5 text-white" />
            <input type="file" accept="image/*" className="hidden" onChange={uploadPhoto} />
          </label>
        </div>
        <div>
          <p className="text-xl font-bold text-white">{profile?.full_name}</p>
          <p className="text-gray-400 text-sm">{profile?.email}</p>
          <p className="text-gray-500 text-xs mt-1">ID: {profile?.student_id}</p>
        </div>
      </div>

      {/* Read-only info */}
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
        <h2 className="font-semibold text-white mb-4">Academic Information</h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          {[
            ["Course", profile?.course], ["Branch", profile?.branch],
            ["Semester", profile?.semester], ["Academic Year", profile?.academic_year],
            ["Student ID", profile?.student_id],
          ].map(([label, value]) => (
            <div key={label as string}>
              <p className="text-gray-500 text-xs">{label}</p>
              <p className="text-white mt-0.5">{value || "—"}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Editable info */}
      <form onSubmit={save} className="bg-gray-900 border border-gray-800 rounded-2xl p-6 space-y-4">
        <h2 className="font-semibold text-white mb-2">Edit Profile</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Full Name</label>
            <input value={form.full_name} onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))} className={inp} />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Phone</label>
            <input value={form.phone} onChange={e => setForm(f => ({ ...f, phone: e.target.value }))} className={inp} />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Section</label>
            <input value={form.section} onChange={e => setForm(f => ({ ...f, section: e.target.value }))} className={inp} />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Date of Birth</label>
            <input type="date" value={form.dob} onChange={e => setForm(f => ({ ...f, dob: e.target.value }))} className={inp} />
          </div>
        </div>
        <button type="submit" disabled={saving} className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm rounded-xl">
          {saving ? "Saving..." : "Save Changes"}
        </button>
      </form>
    </div>
  );
}
