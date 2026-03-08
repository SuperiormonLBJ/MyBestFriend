"use client";

import Link from "next/link";
import { Database, Settings, ScrollText, FlaskConical } from "lucide-react";

export default function AdminPage() {
  return (
    <div className="flex min-h-full flex-1 flex-col">
      <header className="shrink-0 border-b-2 border-[var(--border)] bg-[var(--primary)] px-6 py-4 header-texture">
        <h2 className="font-heading text-3xl text-[#000000] uppercase tracking-wide">
          ADMIN PANEL
        </h2>
        <p className="mt-1 font-body text-base font-bold text-[#000000]/75 uppercase tracking-widest">
          Manage knowledge base and configuration
        </p>
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-8">
        <div className="mx-auto grid max-w-4xl gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <Link
            href="/admin/knowledge"
            className="group block border-2 border-[var(--border)] bg-[var(--background-elevated)] p-6 transition-colors duration-200 hover:bg-[var(--surface)] cursor-pointer"
            style={{ boxShadow: "4px 4px 0 var(--border)" }}
          >
            <div className="flex flex-col gap-3">
              <div className="flex h-12 w-12 items-center justify-center border-2 border-[var(--border)] bg-[var(--border)] text-[var(--background)]">
                <Database className="h-6 w-6" strokeWidth={2} />
              </div>
              <div>
                <h3 className="font-heading text-base uppercase tracking-wide text-[var(--foreground)]">Knowledge Base</h3>
                <p className="mt-1 font-body text-sm text-[var(--foreground-muted)]">
                  View, add, and delete documents in the vector store
                </p>
              </div>
            </div>
          </Link>

          <Link
            href="/admin/settings"
            className="group block border-2 border-[var(--border)] bg-[var(--background-elevated)] p-6 transition-colors duration-200 hover:bg-[var(--surface)] cursor-pointer"
            style={{ boxShadow: "4px 4px 0 var(--border)" }}
          >
            <div className="flex flex-col gap-3">
              <div className="flex h-12 w-12 items-center justify-center border-2 border-[var(--border)] bg-[var(--border)] text-[var(--background)]">
                <Settings className="h-6 w-6" strokeWidth={2} />
              </div>
              <div>
                <h3 className="font-heading text-base uppercase tracking-wide text-[var(--foreground)]">Settings</h3>
                <p className="mt-1 font-body text-sm text-[var(--foreground-muted)]">
                  Configure display options, models, and notifications
                </p>
              </div>
            </div>
          </Link>

          <Link
            href="/admin/prompts"
            className="group block border-2 border-[var(--border)] bg-[var(--background-elevated)] p-6 transition-colors duration-200 hover:bg-[var(--surface)] cursor-pointer"
            style={{ boxShadow: "4px 4px 0 var(--border)" }}
          >
            <div className="flex flex-col gap-3">
              <div className="flex h-12 w-12 items-center justify-center border-2 border-[var(--border)] bg-[var(--border)] text-[var(--background)]">
                <ScrollText className="h-6 w-6" strokeWidth={2} />
              </div>
              <div>
                <h3 className="font-heading text-base uppercase tracking-wide text-[var(--foreground)]">Prompts</h3>
                <p className="mt-1 font-body text-sm text-[var(--foreground-muted)]">
                  Edit LLM system prompts stored in Supabase
                </p>
              </div>
            </div>
          </Link>

          <Link
            href="/admin/eval"
            className="group block border-2 border-[var(--border)] bg-[var(--background-elevated)] p-6 transition-colors duration-200 hover:bg-[var(--surface)] cursor-pointer"
            style={{ boxShadow: "4px 4px 0 var(--border)" }}
          >
            <div className="flex flex-col gap-3">
              <div className="flex h-12 w-12 items-center justify-center border-2 border-[var(--border)] bg-[var(--border)] text-[var(--background)]">
                <FlaskConical className="h-6 w-6" strokeWidth={2} />
              </div>
              <div>
                <h3 className="font-heading text-base uppercase tracking-wide text-[var(--foreground)]">Evaluation</h3>
                <p className="mt-1 font-body text-sm text-[var(--foreground-muted)]">
                  Run RAG evaluation and visualize results
                </p>
              </div>
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
}
