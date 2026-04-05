"use client";

import { useState } from "react";
import { Lock, Eye, EyeOff } from "lucide-react";
import { fetchVerifyAdminKey } from "@/lib/session-auth";

type Props = {
  onSuccess: (key: string) => void;
  variant?: "fullscreen" | "overlay";
  onCancel?: () => void;
};

export default function AdminLoginModal({
  onSuccess,
  variant = "fullscreen",
  onCancel,
}: Props) {
  const [key, setKey] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await fetchVerifyAdminKey(key);
      if (res.ok) {
        onSuccess(key);
      } else {
        setError("Incorrect admin key. Try again.");
      }
    } catch {
      setError("Could not connect to server.");
    } finally {
      setLoading(false);
    }
  };

  const shellCls =
    variant === "overlay"
      ? "fixed inset-0 z-[100] flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
      : "flex h-screen w-full items-center justify-center bg-[var(--surface)]";

  return (
    <div className={shellCls}>
      <div className="relative w-full max-w-sm rounded-2xl border-2 border-[var(--border)] bg-[var(--background)] p-8 shadow-sm">
        {onCancel ? (
          <button
            type="button"
            onClick={onCancel}
            className="absolute right-4 top-4 text-sm font-medium text-[var(--foreground-muted)] hover:text-[var(--foreground)]"
          >
            Cancel
          </button>
        ) : null}
        <div className="mb-6 flex flex-col items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-full border-2 border-[var(--primary)] bg-[var(--primary)]/10">
            <Lock className="h-5 w-5 text-[var(--primary)]" />
          </div>
          <div className="text-center">
            <h1 className="font-body text-xl font-bold text-[var(--foreground)]">
              Admin Access
            </h1>
            <p className="mt-1 text-sm text-[var(--foreground-muted)]">
              Enter your admin API key to save changes
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="relative">
            <input
              type={show ? "text" : "password"}
              value={key}
              onChange={(e) => setKey(e.target.value)}
              placeholder="Admin API key"
              className="w-full rounded-lg border-2 border-[var(--border)] bg-[var(--background)] px-3 py-2.5 pr-10 text-sm outline-none transition-colors focus:border-[var(--primary)]"
              autoFocus
            />
            <button
              type="button"
              onClick={() => setShow((s) => !s)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--foreground-muted)] hover:text-[var(--foreground)]"
              tabIndex={-1}
            >
              {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>

          {error && <p className="text-xs text-red-500">{error}</p>}

          <button
            type="submit"
            disabled={loading || (!key && variant === "fullscreen")}
            className="w-full rounded-lg bg-[var(--primary)] py-2.5 font-body text-sm font-bold text-[#000000] transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {loading ? "Verifying…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
