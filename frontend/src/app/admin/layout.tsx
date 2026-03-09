"use client";

import { useState, useEffect } from "react";
import AdminLoginModal from "@/components/admin-login";
import { ADMIN_SESSION_KEY, storeAdminKey } from "@/lib/session-auth";

type AuthStatus = "loading" | "authenticated" | "needs_key";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");

  useEffect(() => {
    const stored = sessionStorage.getItem(ADMIN_SESSION_KEY) ?? "";

    // Always validate current session key with backend.
    // If backend has no key configured, empty string will be accepted.
    fetch("/api/auth/admin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: stored }),
    })
      .then((r) => {
        if (r.ok) {
          storeAdminKey(stored);
          setStatus("authenticated");
        } else {
          sessionStorage.removeItem(ADMIN_SESSION_KEY);
          setStatus("needs_key");
        }
      })
      .catch(() => {
        sessionStorage.removeItem(ADMIN_SESSION_KEY);
        setStatus("needs_key");
      });
  }, []);

  if (status === "loading") {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-[var(--surface)]">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--primary)] border-t-transparent" />
      </div>
    );
  }

  if (status === "needs_key") {
    return (
      <AdminLoginModal
        onSuccess={(key) => {
          storeAdminKey(key);
          setStatus("authenticated");
        }}
      />
    );
  }

  return <>{children}</>;
}
