"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import AdminLoginModal from "@/components/admin-login";
import { ADMIN_SESSION_KEY, clearAdminKey, storeAdminKey } from "@/lib/session-auth";

type AdminWriteContextValue = {
  canModify: boolean;
  ensureCanModify: () => Promise<boolean>;
  markWriteUnauthenticated: () => void;
};

const AdminWriteContext = createContext<AdminWriteContextValue | null>(null);

export function useAdminWrite() {
  const v = useContext(AdminWriteContext);
  if (!v) {
    throw new Error("useAdminWrite must be used within AdminWriteProvider");
  }
  return v;
}

export function AdminWriteProvider({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [canModify, setCanModify] = useState(false);
  const [showLogin, setShowLogin] = useState(false);
  const resolveRef = useRef<((ok: boolean) => void) | null>(null);

  useEffect(() => {
    const stored = sessionStorage.getItem(ADMIN_SESSION_KEY) ?? "";
    fetch("/api/auth/admin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: stored }),
    })
      .then((r) => {
        if (r.ok) {
          storeAdminKey(stored);
          setCanModify(true);
        } else {
          clearAdminKey();
          setCanModify(false);
        }
      })
      .catch(() => {
        clearAdminKey();
        setCanModify(false);
      })
      .finally(() => setLoading(false));
  }, []);

  const markWriteUnauthenticated = useCallback(() => {
    clearAdminKey();
    setCanModify(false);
  }, []);

  const ensureCanModify = useCallback((): Promise<boolean> => {
    if (canModify) return Promise.resolve(true);
    return new Promise((resolve) => {
      resolveRef.current = resolve;
      setShowLogin(true);
    });
  }, [canModify]);

  const onLoginSuccess = (key: string) => {
    storeAdminKey(key);
    setCanModify(true);
    setShowLogin(false);
    resolveRef.current?.(true);
    resolveRef.current = null;
  };

  const onLoginCancel = () => {
    setShowLogin(false);
    resolveRef.current?.(false);
    resolveRef.current = null;
  };

  const value: AdminWriteContextValue = {
    canModify,
    ensureCanModify,
    markWriteUnauthenticated,
  };

  if (loading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-[var(--surface)]">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--primary)] border-t-transparent" />
      </div>
    );
  }

  return (
    <AdminWriteContext.Provider value={value}>
      {children}
      {showLogin ? (
        <AdminLoginModal
          variant="overlay"
          onSuccess={onLoginSuccess}
          onCancel={onLoginCancel}
        />
      ) : null}
    </AdminWriteContext.Provider>
  );
}
