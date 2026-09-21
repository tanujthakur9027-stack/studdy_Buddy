"use client";
import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { usePathname } from "next/navigation";
import Sidebar from "./Sidebar";
import Header from "./Header";
import SplashScreen from "./SplashScreen";

const PUBLIC_PATHS = ["/login", "/register", "/share"];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const pathname = usePathname();
  const [splashDone, setSplashDone] = useState(false);

  const isPublic = PUBLIC_PATHS.some((p) => pathname.startsWith(p));

  // ── Splash screen on every cold load (auth hasn't resolved yet) ────────────
  // Show splash while loading auth; once auth resolves AND splash animation has
  // completed, render the real UI.
  if (!splashDone) {
    return <SplashScreen onDone={() => setSplashDone(true)} />;
  }

  // ── Public routes (login / register / share) ────────────────────────────────
  // Render bare page — no sidebar, no header.
  if (isPublic) {
    return <>{children}</>;
  }

  // ── Auth loading spinner (edge case: splash done but auth still resolving) ──
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  // ── Unauthenticated on a protected route ─────────────────────────────────
  // Show nothing — AuthGuard / page-level useEffect will redirect to /login.
  if (!user) {
    return null;
  }

  // ── Authenticated: render app shell with sidebar ──────────────────────────
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto bg-gray-950 p-6">{children}</main>
      </div>
    </div>
  );
}
