"use client";
import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import Link from "next/link";
import toast from "react-hot-toast";
import { BookOpen } from "lucide-react";

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    full_name: "", email: "", password: "", student_id: "",
    phone: "", course: "", branch: "", semester: "", section: "",
    academic_year: "", dob: "",
  });

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (form.password.length < 8) { toast.error("Password must be at least 8 characters"); return; }
    setLoading(true);
    try {
      await register(form);
      toast.success("Account created successfully!");
      router.push("/dashboard");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Registration failed";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const inputClass = "w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors";
  const labelClass = "block text-sm font-medium text-gray-300 mb-1.5";

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center">
              <BookOpen className="w-6 h-6 text-white" />
            </div>
            <span className="text-2xl font-bold text-white">Study Buddy</span>
          </div>
          <p className="text-gray-400 mt-2">Create your student account</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-gray-900 rounded-2xl p-8 border border-gray-800">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label className={labelClass}>Full Name *</label>
              <input className={inputClass} required placeholder="John Doe" value={form.full_name} onChange={set("full_name")} />
            </div>
            <div>
              <label className={labelClass}>Email *</label>
              <input className={inputClass} type="email" required placeholder="you@example.com" value={form.email} onChange={set("email")} />
            </div>
            <div>
              <label className={labelClass}>Password *</label>
              <input className={inputClass} type="password" required placeholder="Min 8 characters" value={form.password} onChange={set("password")} />
            </div>
            <div>
              <label className={labelClass}>Student ID / Roll Number *</label>
              <input className={inputClass} required placeholder="CS2024001" value={form.student_id} onChange={set("student_id")} />
            </div>
            <div>
              <label className={labelClass}>Phone</label>
              <input className={inputClass} placeholder="+91 9876543210" value={form.phone} onChange={set("phone")} />
            </div>
            <div>
              <label className={labelClass}>Course</label>
              <input className={inputClass} placeholder="B.Tech, MCA, etc." value={form.course} onChange={set("course")} />
            </div>
            <div>
              <label className={labelClass}>Branch</label>
              <input className={inputClass} placeholder="Computer Science" value={form.branch} onChange={set("branch")} />
            </div>
            <div>
              <label className={labelClass}>Semester</label>
              <input className={inputClass} placeholder="3rd Semester" value={form.semester} onChange={set("semester")} />
            </div>
            <div>
              <label className={labelClass}>Section</label>
              <input className={inputClass} placeholder="A" value={form.section} onChange={set("section")} />
            </div>
            <div>
              <label className={labelClass}>Academic Year</label>
              <input className={inputClass} placeholder="2024-25" value={form.academic_year} onChange={set("academic_year")} />
            </div>
            <div>
              <label className={labelClass}>Date of Birth</label>
              <input className={inputClass} type="date" value={form.dob} onChange={set("dob")} />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="mt-6 w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold rounded-xl transition-colors"
          >
            {loading ? "Creating Account..." : "Create Account"}
          </button>

          <p className="text-center text-gray-400 text-sm mt-4">
            Already have an account?{" "}
            <Link href="/login" className="text-blue-400 hover:text-blue-300">Sign in</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
