"use client";

import { useState, Suspense } from "react";
import { useAuth } from "@/context/AuthContext";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import toast from "react-hot-toast";
import {
  GraduationCap,
  Shield,
  KeyRound,
  Eye,
  EyeOff,
  User,
  Mail,
  Lock,
  Building2,
  FileBadge,
} from "lucide-react";

function RegisterContent() {
  const { register } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  // Active portal tab: "student" | "admin"
  const initialRole = searchParams.get("role") === "admin" ? "admin" : "student";
  const [portal, setPortal] = useState<"student" | "admin">(initialRole);

  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // Common and Role-specific form fields
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    phone: "",
    // Student specific
    student_id: "",
    course: "",
    branch: "",
    semester: "",
    section: "",
    academic_year: "",
    dob: "",
    // Admin specific
    admin_key: "",
    designation: "",
    department: "",
  });

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const handlePortalSwitch = (role: "student" | "admin") => {
    setPortal(role);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (form.password.length < 8) {
      toast.error("Password must be at least 8 characters long.");
      return;
    }

    if (portal === "admin" && !form.admin_key.trim()) {
      toast.error("Please enter the Administrator Setup Key.");
      return;
    }

    setLoading(true);
    try {
      const payload: Record<string, string> = {
        role: portal,
        email: form.email.trim().toLowerCase(),
        password: form.password,
        full_name: form.full_name.trim(),
        phone: form.phone.trim(),
      };

      if (portal === "admin") {
        payload.admin_key = form.admin_key.trim();
        payload.student_id = form.designation.trim() || form.student_id.trim();
        payload.branch = form.department.trim() || "Academic Staff";
      } else {
        payload.student_id = form.student_id.trim();
        payload.course = form.course.trim();
        payload.branch = form.branch.trim();
        payload.semester = form.semester.trim();
        payload.section = form.section.trim();
        payload.academic_year = form.academic_year.trim();
        payload.dob = form.dob.trim();
      }

      await register(payload);

      toast.success(`Account created successfully as ${portal === "admin" ? "Administrator" : "Student"}!`);
      if (portal === "admin") {
        router.push("/admin/dashboard");
      } else {
        router.push("/dashboard");
      }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Registration failed. Please check your inputs.";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const inputClass =
    "w-full px-4 py-3 bg-gray-900/90 border border-gray-700/80 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors text-sm";
  const labelClass = "block text-xs font-semibold text-gray-300 mb-1.5";

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col items-center justify-center p-4 py-12 relative overflow-hidden">
      {/* Background radial gradient glow */}
      <div
        className={`absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[650px] h-[450px] rounded-full blur-[140px] pointer-events-none transition-colors duration-700 opacity-20 ${
          portal === "admin" ? "bg-amber-500" : "bg-blue-600"
        }`}
      />

      <div className="w-full max-w-2xl relative z-10 space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center gap-3">
            <div
              className={`w-12 h-12 rounded-2xl flex items-center justify-center shadow-lg transition-all ${
                portal === "admin"
                  ? "bg-gradient-to-tr from-amber-600 to-yellow-500 text-black shadow-amber-500/20"
                  : "bg-gradient-to-tr from-blue-600 to-indigo-600 text-white shadow-blue-500/20"
              }`}
            >
              {portal === "admin" ? (
                <Shield className="w-6 h-6" />
              ) : (
                <GraduationCap className="w-6 h-6" />
              )}
            </div>
            <div className="text-left">
              <h1 className="text-2xl font-black text-white tracking-tight">StudyBuddy AI</h1>
              <span
                className={`text-[10px] font-extrabold uppercase px-2 py-0.5 rounded-full tracking-wider border ${
                  portal === "admin"
                    ? "bg-amber-500/10 text-amber-300 border-amber-500/30"
                    : "bg-blue-500/10 text-blue-300 border-blue-500/30"
                }`}
              >
                {portal === "admin" ? "Faculty & Administrator Portal" : "Student Learning Portal"}
              </span>
            </div>
          </div>
          <p className="text-gray-400 text-sm">
            {`Register a new ${portal === "admin" ? "Administrator" : "Student"} account`}
          </p>
        </div>

        {/* Portal Switcher Tabs */}
        <div className="bg-gray-900/90 p-1.5 rounded-2xl border border-gray-800 grid grid-cols-2 gap-1 shadow-inner backdrop-blur-xl">
            <button
              type="button"
              onClick={() => handlePortalSwitch("student")}
              className={`flex items-center justify-center gap-2 py-3 px-3 rounded-xl text-xs font-bold transition-all ${
                portal === "student"
                  ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-600/25 border border-blue-500/40"
                  : "text-gray-400 hover:text-white hover:bg-gray-800/60"
              }`}
            >
              <GraduationCap className={`w-4 h-4 ${portal === "student" ? "text-white" : "text-blue-400"}`} />
              Student Registration
            </button>

            <button
              type="button"
              onClick={() => handlePortalSwitch("admin")}
              className={`flex items-center justify-center gap-2 py-3 px-3 rounded-xl text-xs font-bold transition-all ${
                portal === "admin"
                  ? "bg-gradient-to-r from-amber-600 to-yellow-600 text-black shadow-lg shadow-amber-600/25 border border-amber-500/40"
                  : "text-gray-400 hover:text-white hover:bg-gray-800/60"
              }`}
            >
              <Shield className={`w-4 h-4 ${portal === "admin" ? "text-black" : "text-amber-400"}`} />
              Admin / Faculty Registration
            </button>
          </div>

        {/* Main Card */}
        <div
          className={`bg-gray-900/90 rounded-3xl p-7 border transition-all shadow-2xl backdrop-blur-xl ${
            portal === "admin"
              ? "border-amber-500/30 shadow-amber-500/5"
              : "border-blue-500/30 shadow-blue-500/5"
          }`}
        >
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Admin Setup Key Helper Card (Shown only on Admin Tab) */}
            {portal === "admin" && (
              <div className="bg-amber-950/40 border border-amber-500/30 rounded-2xl p-4 text-xs space-y-2">
                <div className="flex items-center justify-between text-amber-300 font-bold">
                  <span className="flex items-center gap-1.5">
                    <Shield className="w-4 h-4 text-amber-400" />
                    Faculty & Staff Verification Required
                  </span>
                </div>
                <p className="text-gray-400 text-[11px] leading-relaxed">
                  Administrator registration requires a valid administrative setup key provided by your system administrator.
                </p>
              </div>
            )}

              {/* Form Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Full Name */}
                <div>
                  <label className={labelClass}>
                    <User className="w-3.5 h-3.5 inline mr-1 text-gray-400" />
                    Full Name *
                  </label>
                  <input
                    className={inputClass}
                    required
                    placeholder={portal === "admin" ? "Prof. Alan Turing" : "John Doe"}
                    value={form.full_name}
                    onChange={set("full_name")}
                  />
                </div>

                {/* Email Address */}
                <div>
                  <label className={labelClass}>
                    <Mail className="w-3.5 h-3.5 inline mr-1 text-gray-400" />
                    {portal === "admin" ? "Official / University Email *" : "Student Email *"}
                  </label>
                  <input
                    className={inputClass}
                    type="email"
                    required
                    placeholder={portal === "admin" ? "faculty@university.edu" : "student@university.edu"}
                    value={form.email}
                    onChange={set("email")}
                  />
                </div>

                {/* Password */}
                <div>
                  <label className={labelClass}>
                    <Lock className="w-3.5 h-3.5 inline mr-1 text-gray-400" />
                    Password *
                  </label>
                  <div className="relative">
                    <input
                      className={inputClass}
                      type={showPassword ? "text" : "password"}
                      required
                      placeholder="Min 8 characters"
                      value={form.password}
                      onChange={set("password")}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* Phone */}
                <div>
                  <label className={labelClass}>Phone Number</label>
                  <input
                    className={inputClass}
                    placeholder="+91 9876543210"
                    value={form.phone}
                    onChange={set("phone")}
                  />
                </div>

                {/* ── ADMIN SPECIFIC FIELDS ── */}
                {portal === "admin" ? (
                  <>
                    <div>
                      <label className={labelClass}>
                        <KeyRound className="w-3.5 h-3.5 inline mr-1 text-amber-400" />
                        Administrator Setup Key *
                      </label>
                      <input
                        className={inputClass}
                        required
                        type="password"
                        placeholder="Enter administrator setup key"
                        value={form.admin_key}
                        onChange={set("admin_key")}
                      />
                    </div>

                    <div>
                      <label className={labelClass}>
                        <FileBadge className="w-3.5 h-3.5 inline mr-1 text-amber-400" />
                        Faculty / Employee ID
                      </label>
                      <input
                        className={inputClass}
                        placeholder="EMP-1042 or ADMIN-CS"
                        value={form.designation}
                        onChange={set("designation")}
                      />
                    </div>

                    <div className="md:col-span-2">
                      <label className={labelClass}>
                        <Building2 className="w-3.5 h-3.5 inline mr-1 text-amber-400" />
                        Department / Administrative Office
                      </label>
                      <input
                        className={inputClass}
                        placeholder="Department of Computer Science & Engineering"
                        value={form.department}
                        onChange={set("department")}
                      />
                    </div>
                  </>
                ) : (
                  /* ── STUDENT SPECIFIC FIELDS ── */
                  <>
                    <div>
                      <label className={labelClass}>Student ID / Roll Number *</label>
                      <input
                        className={inputClass}
                        required
                        placeholder="CS2024001"
                        value={form.student_id}
                        onChange={set("student_id")}
                      />
                    </div>

                    <div>
                      <label className={labelClass}>Course / Degree</label>
                      <input
                        className={inputClass}
                        placeholder="B.Tech, BCA, MCA, M.Tech"
                        value={form.course}
                        onChange={set("course")}
                      />
                    </div>

                    <div>
                      <label className={labelClass}>Branch / Specialization</label>
                      <input
                        className={inputClass}
                        placeholder="Computer Science, AI & ML"
                        value={form.branch}
                        onChange={set("branch")}
                      />
                    </div>

                    <div>
                      <label className={labelClass}>Semester</label>
                      <input
                        className={inputClass}
                        placeholder="4th Semester"
                        value={form.semester}
                        onChange={set("semester")}
                      />
                    </div>

                    <div>
                      <label className={labelClass}>Section</label>
                      <input
                        className={inputClass}
                        placeholder="A"
                        value={form.section}
                        onChange={set("section")}
                      />
                    </div>

                    <div>
                      <label className={labelClass}>Academic Year</label>
                      <input
                        className={inputClass}
                        placeholder="2024-25"
                        value={form.academic_year}
                        onChange={set("academic_year")}
                      />
                    </div>

                    <div className="md:col-span-2">
                      <label className={labelClass}>Date of Birth</label>
                      <input
                        className={inputClass}
                        type="date"
                        value={form.dob}
                        onChange={set("dob")}
                      />
                    </div>
                  </>
                )}
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading}
                className={`w-full py-3.5 text-white font-bold rounded-xl transition-all shadow-lg flex items-center justify-center gap-2 mt-2 ${
                  portal === "admin"
                    ? "bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-500 hover:to-yellow-500 text-black shadow-amber-600/25"
                    : "bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 shadow-blue-600/25"
                }`}
              >
                {loading ? (
                  <>
                    <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                    Creating Account & Signing In...
                  </>
                ) : (
                  <>
                    {portal === "admin" ? <Shield className="w-4 h-4" /> : <GraduationCap className="w-4 h-4" />}
                    Create {portal === "admin" ? "Administrator" : "Student"} Account →
                  </>
                )}
              </button>

              {/* Footer Switch Links */}
              <div className="pt-4 border-t border-gray-800/80 text-center space-y-2">
                <p className="text-xs text-gray-400">
                  Already have an account?{" "}
                  <Link
                    href={`/login`}
                    className={`font-bold hover:underline ${
                      portal === "admin" ? "text-amber-400 hover:text-amber-300" : "text-blue-400 hover:text-blue-300"
                    }`}
                  >
                    Sign In
                  </Link>
                </p>
              </div>
            </form>
        </div>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-gray-950 flex items-center justify-center text-gray-400 text-sm">
          Loading registration portal...
        </div>
      }
    >
      <RegisterContent />
    </Suspense>
  );
}
