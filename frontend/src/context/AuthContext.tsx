"use client";
import { createContext, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  role: "admin" | "student";
  is_active: boolean;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  register: (data: Record<string, string>) => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = async () => {
    try {
      const { data } = await api.get("/api/auth/me", { withCredentials: true });
      setUser(data);
      localStorage.setItem("sb_user", JSON.stringify(data));
    } catch {
      setUser(null);
      localStorage.removeItem("sb_user");
    }
  };

  useEffect(() => {
    // Try to restore user from cookie/localStorage
    const saved = localStorage.getItem("sb_user");
    if (saved) {
      try {
        setUser(JSON.parse(saved));
      } catch { /* ignore */ }
    }
    refreshUser().finally(() => setLoading(false));
  }, []);

  // Add auth header interceptor
  useEffect(() => {
    const id = api.interceptors.response.use(
      (res) => res,
      (err) => {
        if (err.response?.status === 401) {
          setUser(null);
          localStorage.removeItem("sb_user");
          if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
            window.location.href = "/login";
          }
        }
        return Promise.reject(err);
      }
    );
    return () => api.interceptors.response.eject(id);
  }, []);

  const login = async (email: string, password: string) => {
    const { data } = await api.post(
      "/api/auth/login",
      { email, password },
      { withCredentials: true }
    );
    setUser(data.user);
    localStorage.setItem("sb_user", JSON.stringify(data.user));
    // Set token for future requests
    api.defaults.headers.common["Authorization"] = `Bearer ${data.access_token}`;
  };

  const logout = async () => {
    try {
      await api.post("/api/auth/logout", {}, { withCredentials: true });
    } catch { /* ignore */ }
    setUser(null);
    localStorage.removeItem("sb_user");
    delete api.defaults.headers.common["Authorization"];
  };

  const register = async (formData: Record<string, string>) => {
    const { data } = await api.post(
      "/api/auth/register",
      formData,
      { withCredentials: true }
    );
    setUser(data.user);
    localStorage.setItem("sb_user", JSON.stringify(data.user));
    api.defaults.headers.common["Authorization"] = `Bearer ${data.access_token}`;
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, register, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
