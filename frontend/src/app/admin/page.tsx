"use client";

import Link from "next/link";
import { Database, Settings, ScrollText, FlaskConical } from "lucide-react";
import { SpotlightCard } from "@/components/ui/spotlight-card";

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
        <div className="mx-auto flex max-w-2xl flex-col gap-6">
          <Link href="/admin/knowledge" className="block">
            <SpotlightCard className="p-8 flex flex-col gap-5 cursor-pointer">
              <div className="h-14 w-14 flex items-center justify-center rounded-xl bg-neutral-800 border border-neutral-700">
                <Database className="text-neutral-200 h-7 w-7" strokeWidth={2} />
              </div>
              <div>
                <h3 className="text-xl font-semibold text-white mb-2">Knowledge Base</h3>
                <p className="text-base text-neutral-400">
                  View, add, and delete documents in the vector store
                </p>
              </div>
            </SpotlightCard>
          </Link>

          <Link href="/admin/settings" className="block">
            <SpotlightCard
              className="p-8 flex flex-col gap-5 cursor-pointer"
              spotlightColor="rgba(14, 165, 233, 0.25)"
            >
              <div className="h-14 w-14 flex items-center justify-center rounded-xl bg-sky-900/20 border border-sky-800/50">
                <Settings className="text-sky-300 h-7 w-7" strokeWidth={2} />
              </div>
              <div>
                <h3 className="text-xl font-semibold text-white mb-2">Settings</h3>
                <p className="text-base text-neutral-400">
                  Configure display options, models, and notifications
                </p>
              </div>
            </SpotlightCard>
          </Link>

          <Link href="/admin/prompts" className="block">
            <SpotlightCard
              className="p-8 flex flex-col gap-5 cursor-pointer"
              spotlightColor="rgba(168, 85, 247, 0.25)"
            >
              <div className="h-14 w-14 flex items-center justify-center rounded-xl bg-purple-900/20 border border-purple-800/50">
                <ScrollText className="text-purple-300 h-7 w-7" strokeWidth={2} />
              </div>
              <div>
                <h3 className="text-xl font-semibold text-white mb-2">Prompts</h3>
                <p className="text-base text-neutral-400">
                  Edit LLM system prompts stored in Supabase
                </p>
              </div>
            </SpotlightCard>
          </Link>

          <Link href="/admin/eval" className="block">
            <SpotlightCard
              className="p-8 flex flex-col gap-5 cursor-pointer"
              spotlightColor="rgba(13, 148, 136, 0.25)"
            >
              <div className="h-14 w-14 flex items-center justify-center rounded-xl bg-teal-900/20 border border-teal-800/50">
                <FlaskConical className="text-teal-300 h-7 w-7" strokeWidth={2} />
              </div>
              <div>
                <h3 className="text-xl font-semibold text-white mb-2">Evaluation</h3>
                <p className="text-base text-neutral-400">
                  Run RAG evaluation and visualize results
                </p>
              </div>
            </SpotlightCard>
          </Link>
        </div>
      </div>
    </div>
  );
}
