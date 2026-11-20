"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import Link from "next/link";
import toast from "react-hot-toast";
import {
  BookOpen,
  Eye,
  EyeOff,
  GraduationCap,
  Shield,
  Sparkles,
  Lock,
  Mail,
  ArrowRight,
  KeyRound,
  RefreshCw,
  ArrowLeft,
  ShieldCheck,
} from "lucide-react";

export default function LoginPage() {
  const { login, verifyOtp, resendOtp } = useAuth();
  const router = useRouter();

  // Active portal tab: "student" | "admin"
  const [portal, setPortal] = useState<"student" | "admin">("student");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      if (params.get("role") === "admin" || params.get("portal") === "admin") {
        setPortal("admin");
      }
    }
  }, []);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);

  // OTP Verification States
  const [showOtp, setShowOtp] = useState(false);
  const [otpCode, setOtpCode] = useState("");
  const [otpEmail, setOtpEmail] = useState("");
  const [simOtp, setSimOtp] = useState<string | null>(null);
  const [otpMessage, setOtpMessage] = useState("");
  const [verifying, setVerifying] = useState(false);
  const [resending, setResending] = useState(false);
  const [countdown, setCountdown] = useState(0);

  // Read URL query params on mount (e.g. ?role=admin)
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      if (params.get("role") === "admin") {
        setPortal("admin");
      }
    }
  }, []);

  // Resend cooldown timer
  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setInterval(() => {
      setCountdown((c) => c - 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [countdown]);

  // Quick fill default admin credentials
  const fillAdminCredentials = () => {
    setEmail("admin@studybuddy.com");
    setPassword("Admin@StudyBuddy2024");
    toast.success("Default admin credentials filled!");
  };

  const handlePortalSwitch = (type: "student" | "admin") => {
    setPortal(type);
    setShowOtp(false);
    setOtpCode("");
    setSimOtp(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      toast.error("Please enter both email and password.");
      return;
    }

    setLoading(true);
    try {
      const trimmedEmail = email.trim().toLowerCase();
      const res = await login(trimmedEmail, password);

      if (res.otp_required) {
        setShowOtp(true);
        setOtpEmail(res.email || trimmedEmail);
        setSimOtp(res.simulation_otp || null);
        setOtpMessage(res.message || "Please enter the 6-digit verification code sent to your email.");
        setCountdown(30);
        toast.success("Security verification code generated!");
      } else {
        toast.success("Welcome back!");
        if (res.user?.role === "admin") {
          router.push("/admin/dashboard");
        } else {
          router.push("/dashboard");
        }
      }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Login failed. Please check your credentials.";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!otpCode || otpCode.trim().length < 4) {
      toast.error("Please enter the 6-digit OTP verification code.");
      return;
    }

    setVerifying(true);
    try {
      const verifiedUser = await verifyOtp(otpEmail, otpCode.trim());
      toast.success(`Welcome back, ${verifiedUser.full_name || "User"}!`);
      if (verifiedUser.role === "admin") {
        router.push("/admin/dashboard");
      } else {
        router.push("/dashboard");
      }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err as Error)?.message ||
        "Invalid or expired OTP code.";
      toast.error(msg);
    } finally {
      setVerifying(false);
    }
  };

  const handleResendOtp = async () => {
    if (countdown > 0 || resending) return;
    setResending(true);
    try {
      const res = await resendOtp(otpEmail);
      if (res.simulation_otp) {
        setSimOtp(res.simulation_otp);
      }
      setCountdown(45);
      toast.success(res.message || "New OTP dispatched to your registered email.");
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Failed to resend OTP.";
      toast.error(msg);
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col justify-center items-center p-4 py-12 relative overflow-hidden">
      {/* Background radial glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-gradient-to-tr from-blue-600/10 via-indigo-600/15 to-purple-600/10 blur-3xl pointer-events-none rounded-full" />

      <div className="w-full max-w-md relative z-10 space-y-6">
        {/* Top Logo & App Title */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center gap-3">
            <div className="w-11 h-11 bg-gradient-to-tr from-blue-600 via-indigo-600 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg shadow-indigo-600/30">
              <BookOpen className="w-6 h-6 text-white" />
            </div>
            <span className="text-2xl font-black text-white tracking-tight">
              StudyBuddy <span className="text-indigo-400">AI</span>
            </span>
          </div>
          <p className="text-gray-400 text-xs font-medium">
            Personalized AI Learning & Campus Management Platform
          </p>
        </div>

        {/* ── Role Portal Selector Tabs ── */}
        {!showOtp && (
          <div className="bg-gray-900/90 border border-gray-800 p-1.5 rounded-2xl grid grid-cols-2 gap-1.5 shadow-xl">
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
              Student Login
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
              Admin Login
            </button>
          </div>
        )}

        {/* ── Main Form Card ── */}
        <div
          className={`bg-gray-900/90 rounded-3xl p-7 border transition-all shadow-2xl backdrop-blur-xl ${
            portal === "admin"
              ? "border-amber-500/30 shadow-amber-500/5"
              : "border-blue-500/30 shadow-blue-500/5"
          }`}
        >
          {showOtp ? (
            /* ── STEP 2: OTP Verification Screen ── */
            <div className="space-y-5">
              <div className="text-center space-y-1.5">
                <div
                  className={`w-12 h-12 mx-auto rounded-2xl flex items-center justify-center mb-2 border ${
                    portal === "admin"
                      ? "bg-amber-500/10 border-amber-500/30 text-amber-400"
                      : "bg-blue-500/10 border-blue-500/30 text-blue-400"
                  }`}
                >
                  <KeyRound className="w-6 h-6" />
                </div>
                <h2 className="text-xl font-black text-white">2-Factor Security Verification</h2>
                <p className="text-gray-400 text-xs">
                  {otpMessage || "A 6-digit one-time code has been dispatched to:"}
                </p>
                <p className="text-indigo-400 font-mono text-xs font-bold">{otpEmail}</p>
              </div>

              {/* Dev Simulation OTP Banner (when SMTP is not configured) */}
              {simOtp && (
                <div className="bg-indigo-950/70 border border-indigo-500/40 rounded-2xl p-4 text-xs space-y-2">
                  <div className="flex items-center justify-between text-indigo-300 font-bold">
                    <span className="flex items-center gap-1.5">
                      <Sparkles className="w-4 h-4 text-indigo-400" />
                      Development Mode Simulation
                    </span>
                    <button
                      type="button"
                      onClick={() => setOtpCode(simOtp)}
                      className="text-[11px] text-amber-400 hover:underline font-extrabold"
                    >
                      ⚡ Auto-fill
                    </button>
                  </div>
                  <p className="text-gray-400 text-[11px]">
                    Your temporary security verification code is:
                  </p>
                  <div className="text-center font-mono font-black text-2xl tracking-[0.25em] text-white bg-black/40 py-2 rounded-xl border border-indigo-500/30">
                    {simOtp}
                  </div>
                </div>
              )}

              <form onSubmit={handleVerifyOtp} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1.5 text-center">
                    Enter 6-Digit OTP Code
                  </label>
                  <input
                    type="text"
                    maxLength={10}
                    value={otpCode}
                    onChange={(e) => setOtpCode(e.target.value.replace(/\s+/g, ""))}
                    required
                    autoFocus
                    placeholder="123456"
                    className="w-full text-center font-mono text-2xl tracking-[0.3em] font-bold py-3.5 bg-gray-800/90 border border-gray-700 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500 transition-colors"
                  />
                </div>

                <button
                  type="submit"
                  disabled={verifying}
                  className={`w-full py-3 px-4 font-bold text-xs rounded-xl shadow-lg transition-all flex items-center justify-center gap-2 ${
                    portal === "admin"
                      ? "bg-gradient-to-r from-amber-600 via-amber-500 to-yellow-500 hover:from-amber-500 hover:to-yellow-400 text-black shadow-amber-600/30"
                      : "bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white shadow-blue-600/30"
                  } disabled:opacity-50`}
                >
                  {verifying ? (
                    <>
                      <span className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                      Verifying Security Code...
                    </>
                  ) : (
                    <>
                      <ShieldCheck className="w-4 h-4" />
                      Verify & Access {portal === "admin" ? "Admin Hub" : "Learning Hub"}
                    </>
                  )}
                </button>
              </form>

              <div className="pt-2 flex items-center justify-between text-xs text-gray-400 border-t border-gray-800/80">
                <button
                  type="button"
                  onClick={() => setShowOtp(false)}
                  className="flex items-center gap-1 hover:text-white transition-colors"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  Change Credentials
                </button>

                <button
                  type="button"
                  onClick={handleResendOtp}
                  disabled={countdown > 0 || resending}
                  className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 disabled:text-gray-600 font-semibold transition-colors"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${resending ? "animate-spin" : ""}`} />
                  {countdown > 0 ? `Resend code (${countdown}s)` : "Resend Code"}
                </button>
              </div>
            </div>
          ) : (
            /* ── STEP 1: Email & Password Form ── */
            <>
              {/* Card Header Info */}
              <div className="mb-6">
                <div className="flex items-center justify-between mb-1.5">
                  <span
                    className={`text-[10px] font-extrabold uppercase tracking-widest px-2.5 py-0.5 rounded-full inline-flex items-center gap-1.5 border ${
                      portal === "admin"
                        ? "bg-amber-500/10 text-amber-300 border-amber-500/30"
                        : "bg-blue-500/10 text-blue-300 border-blue-500/30"
                    }`}
                  >
                    {portal === "admin" ? <Shield className="w-3 h-3" /> : <GraduationCap className="w-3 h-3" />}
                    {portal === "admin" ? "Faculty & Staff Portal" : "Student Learning Portal"}
                  </span>

                  {portal === "admin" && (
                    <button
                      type="button"
                      onClick={fillAdminCredentials}
                      className="text-[11px] text-amber-400 hover:text-amber-300 font-bold underline flex items-center gap-1"
                    >
                      ⚡ Auto-fill Demo
                    </button>
                  )}
                </div>

                <h2 className="text-xl font-black text-white">
                  {portal === "admin" ? "Administrator Sign In" : "Student Sign In"}
                </h2>
                <p className="text-gray-400 text-xs mt-1 leading-relaxed">
                  {portal === "admin"
                    ? "Manage classes, student enrollments, exam marks, timetables & broadcasts."
                    : "Access your AI study assistant, assignments, grades, notes & timetables."}
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Email Field */}
                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1.5">
                    {portal === "admin" ? "Admin Staff Email" : "Student Email Address"}
                  </label>
                  <div className="relative">
                    <Mail className="w-4 h-4 text-gray-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      placeholder={portal === "admin" ? "admin@studybuddy.com" : "student@example.com"}
                      className="w-full pl-10 pr-4 py-3 bg-gray-800/80 border border-gray-700/80 rounded-xl text-white text-xs placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
                    />
                  </div>
                </div>

                {/* Password Field */}
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="block text-xs font-semibold text-gray-300">Password</label>
                  </div>
                  <div className="relative">
                    <Lock className="w-4 h-4 text-gray-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                    <input
                      type={showPw ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      placeholder="••••••••••••"
                      className="w-full pl-10 pr-11 py-3 bg-gray-800/80 border border-gray-700/80 rounded-xl text-white text-xs placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPw((s) => !s)}
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                    >
                      {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* Submit Button */}
                <button
                  type="submit"
                  disabled={loading}
                  className={`w-full py-3 px-4 font-bold text-xs rounded-xl shadow-lg transition-all flex items-center justify-center gap-2 ${
                    portal === "admin"
                      ? "bg-gradient-to-r from-amber-600 via-amber-500 to-yellow-500 hover:from-amber-500 hover:to-yellow-400 text-black shadow-amber-600/30"
                      : "bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white shadow-blue-600/30"
                  } disabled:opacity-50`}
                >
                  {loading ? (
                    <>
                      <span className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                      Authenticating...
                    </>
                  ) : (
                    <>
                      {portal === "admin" ? "Access Admin Command Hub" : "Enter Student Learning Hub"}
                      <ArrowRight className="w-3.5 h-3.5" />
                    </>
                  )}
                </button>
              </form>

              {/* Bottom Card Footer */}
              <div className="mt-6 pt-5 border-t border-gray-800/80">
                {portal === "student" ? (
                  <div className="text-center space-y-2">
                    <p className="text-xs text-gray-400">
                      New student joining StudyBuddy?{" "}
                      <Link href="/register" className="text-blue-400 hover:text-blue-300 font-bold">
                        Create Student Account
                      </Link>
                    </p>
                    <button
                      type="button"
                      onClick={() => handlePortalSwitch("admin")}
                      className="text-[11px] text-gray-500 hover:text-amber-400 transition-colors inline-flex items-center gap-1 font-medium"
                    >
                      <Shield className="w-3 h-3 text-amber-500" />
                      Are you faculty or staff? Switch to Admin Login →
                    </button>
                  </div>
                ) : (
                  <div className="bg-gray-950/60 p-3.5 rounded-2xl border border-gray-800 space-y-2 text-xs">
                    <div className="flex items-center justify-between text-amber-400 font-bold text-[11px]">
                      <span className="flex items-center gap-1">
                        <Sparkles className="w-3 h-3" />
                        Default Admin Credentials
                      </span>
                      <button
                        type="button"
                        onClick={fillAdminCredentials}
                        className="text-[10px] text-amber-300 hover:underline uppercase tracking-wider font-extrabold"
                      >
                        Click to Use
                      </button>
                    </div>
                    <div className="font-mono text-[11px] text-gray-300 space-y-0.5">
                      <p>Email: <span className="text-white">admin@studybuddy.com</span></p>
                      <p>Password: <span className="text-white">Admin@StudyBuddy2024</span></p>
                    </div>
                    <div className="pt-2 text-center space-y-1.5 border-t border-gray-800/60">
                      <p className="text-xs text-gray-400">
                        Need a new administrator account?{" "}
                        <Link href="/register?role=admin" className="text-amber-400 hover:text-amber-300 font-bold">
                          Register Admin Account →
                        </Link>
                      </p>
                      <button
                        type="button"
                        onClick={() => handlePortalSwitch("student")}
                        className="text-[11px] text-gray-500 hover:text-blue-400 transition-colors inline-flex items-center gap-1 font-medium"
                      >
                        <GraduationCap className="w-3 h-3 text-blue-500" />
                        Are you a student? Switch to Student Login →
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* Bottom subtle note */}
        <p className="text-center text-gray-600 text-[11px]">
          Secure multi-role authentication with 2-Factor OTP verification & role-based access control.
        </p>
      </div>
    </div>
  );
}
