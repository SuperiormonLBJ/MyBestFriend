"use client";

import Link from "next/link";
import { Database, Settings } from "lucide-react";

export default function AdminPage() {
  return (
    <div className="flex min-h-full flex-1 flex-col">
      <header className="shrink-0 border-b border-[var(--border)] px-6 py-4">
        <h2 className="font-heading text-xl font-bold tracking-wider text-[var(--primary)]">
          ADMIN PANEL
        </h2>
        <p className="mt-1 text-sm text-[var(--foreground-muted)] font-body">
          Manage knowledge base and configuration
        </p>
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-8">
        <div className="mx-auto grid max-w-4xl gap-6 sm:grid-cols-2">
          <Link
            href="/admin/knowledge"
            className="group block rounded-lg border border-[var(--border)] bg-[var(--background-elevated)] p-6 transition-all duration-200 hover:border-[var(--primary)] hover:shadow-[0_0_16px_var(--primary-glow)] cursor-pointer"
          >
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[var(--primary)]/10 text-[var(--primary)]">
                <Database className="h-6 w-6" strokeWidth={2} />
              </div>
              <div>
                <h3 className="font-semibold text-[var(--foreground)]">Knowledge Base</h3>
                <p className="text-sm text-[var(--foreground-muted)]">
                  View, add, and delete documents in the vector store
                </p>
              </div>
            </div>
          </Link>

          <Link
            href="/admin/settings"
            className="group block rounded-lg border border-[var(--border)] bg-[var(--background-elevated)] p-6 transition-all duration-200 hover:border-[var(--primary)] hover:shadow-[0_0_16px_var(--primary-glow)] cursor-pointer"
          >
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[var(--primary)]/10 text-[var(--primary)]">
                <Settings className="h-6 w-6" strokeWidth={2} />
              </div>
              <div>
                <h3 className="font-semibold text-[var(--foreground)]">Settings</h3>
                <p className="text-sm text-[var(--foreground-muted)]">
                  View and configure frontend display options
                </p>
              </div>
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
}
