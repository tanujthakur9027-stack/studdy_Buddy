"use client";
import { createContext, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  role: "admin" | "student";
  is_active: boolean;
  student_id?: string;
  phone?: string;
  course?: string;
  branch?: string;
  semester?: string;
  section?: string;
  academic_year?: string;
  dob?: string | null;
  profile_photo_url?: string | null;
  class_id?: string | null;
  class_name?: string | null;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (_email: string, _password: string) => Promise<void>;
  logout: () => Promise<void>;
  register: (_data: Record<string, string>) => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = async () => {
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("sb_token") : null;
      const headers: Record<string, string> = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
      const { data } = await api.get("/api/auth/me", { withCredentials: true, headers });
      setUser(data);
      if (typeof window !== "undefined") {
        localStorage.setItem("sb_user", JSON.stringify(data));
      }
    } catch {
      setUser(null);
      if (typeof window !== "undefined") {
        localStorage.removeItem("sb_user");
        localStorage.removeItem("sb_token");
      }
      delete api.defaults.headers.common["Authorization"];
    }
  };

  useEffect(() => {
    // Restore session and auth token on mount
    const token = typeof window !== "undefined" ? localStorage.getItem("sb_token") : null;
    const saved = typeof window !== "undefined" ? localStorage.getItem("sb_user") : null;

    if (token) {
      api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    }

    if (saved) {
      try {
        setUser(JSON.parse(saved));
      } catch {
        /* ignore parsing error */
      }
    }

    if (token) {
      refreshUser().finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  // Response interceptor to catch 401s and clean up
  useEffect(() => {
    const id = api.interceptors.response.use(
      (res) => res,
      (err) => {
        if (err.response?.status === 401) {
          setUser(null);
          if (typeof window !== "undefined") {
            localStorage.removeItem("sb_user");
            localStorage.removeItem("sb_token");
          }
          delete api.defaults.headers.common["Authorization"];
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
    if (typeof window !== "undefined") {
      localStorage.setItem("sb_token", data.access_token);
      localStorage.setItem("sb_user", JSON.stringify(data.user));
    }
    api.defaults.headers.common["Authorization"] = `Bearer ${data.access_token}`;
  };

  const logout = async () => {
    try {
      await api.post("/api/auth/logout", {}, { withCredentials: true });
    } catch {
      /* ignore */
    }
    setUser(null);
    if (typeof window !== "undefined") {
      localStorage.removeItem("sb_token");
      localStorage.removeItem("sb_user");
    }
    delete api.defaults.headers.common["Authorization"];
  };

  const register = async (formData: Record<string, string>) => {
    const { data } = await api.post(
      "/api/auth/register",
      formData,
      { withCredentials: true }
    );
    setUser(data.user);
    if (typeof window !== "undefined") {
      localStorage.setItem("sb_token", data.access_token);
      localStorage.setItem("sb_user", JSON.stringify(data.user));
    }
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
