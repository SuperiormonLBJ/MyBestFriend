"use client";

import { useState, useEffect } from "react";
import AdminLoginModal from "@/components/admin-login";
import { EtherealShadow } from "@/components/ui/ethereal-shadow";
import { CHAT_BG, ETHEREAL_DEFAULT_COLOR, ETHEREAL_ANIMATION, ETHEREAL_NOISE } from "@/lib/constants";
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

  return (
    <div className="relative min-h-screen w-full" style={{ backgroundColor: CHAT_BG }}>
      <div className="pointer-events-none absolute inset-0 flex w-full h-full justify-center items-center">
        <EtherealShadow
          color={ETHEREAL_DEFAULT_COLOR}
          animation={ETHEREAL_ANIMATION}
          noise={ETHEREAL_NOISE}
          sizing="fill"
        />
      </div>
      <div className="relative z-10">{children}</div>
    </div>
  );
}
