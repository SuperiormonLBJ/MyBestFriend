"use client";

import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { Database, Settings, ScrollText, FlaskConical } from "lucide-react";
import { SpotlightCard } from "@/components/ui/spotlight-card";

const ADMIN_LINKS: {
  href: string;
  title: string;
  description: string;
  icon: LucideIcon;
  spotlightColor?: string;
  iconWrapClass: string;
  iconClass: string;
}[] = [
  {
    href: "/admin/knowledge",
    title: "Knowledge Base",
    description: "View, add, and delete documents in the vector store",
    icon: Database,
    iconWrapClass:
      "h-14 w-14 flex items-center justify-center rounded-xl bg-neutral-800 border border-neutral-700",
    iconClass: "text-neutral-200 h-7 w-7",
  },
  {
    href: "/admin/settings",
    title: "Settings",
    description: "Configure display options, models, and notifications",
    icon: Settings,
    spotlightColor: "rgba(14, 165, 233, 0.25)",
    iconWrapClass:
      "h-14 w-14 flex items-center justify-center rounded-xl bg-sky-900/20 border border-sky-800/50",
    iconClass: "text-sky-300 h-7 w-7",
  },
  {
    href: "/admin/prompts",
    title: "Prompts",
    description: "Edit LLM system prompts stored in Supabase",
    icon: ScrollText,
    spotlightColor: "rgba(168, 85, 247, 0.25)",
    iconWrapClass:
      "h-14 w-14 flex items-center justify-center rounded-xl bg-purple-900/20 border border-purple-800/50",
    iconClass: "text-purple-300 h-7 w-7",
  },
  {
    href: "/admin/eval",
    title: "Evaluation",
    description: "Run RAG evaluation and visualize results",
    icon: FlaskConical,
    spotlightColor: "rgba(13, 148, 136, 0.25)",
    iconWrapClass:
      "h-14 w-14 flex items-center justify-center rounded-xl bg-teal-900/20 border border-teal-800/50",
    iconClass: "text-teal-300 h-7 w-7",
  },
];

export default function AdminPage() {
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <header className="shrink-0 border-b-2 border-[var(--border)] bg-[var(--primary)] px-6 py-4 header-texture">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <h2 className="font-heading text-3xl text-[#000000] uppercase tracking-wide">
              ADMIN PANEL
            </h2>
            <p className="mt-1 font-body text-base font-bold text-[#000000]/75 uppercase tracking-widest">
              Manage knowledge base and configuration
            </p>
          </div>
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-6 py-8">
        <div className="mx-auto flex max-w-2xl flex-col gap-6">
          {ADMIN_LINKS.map(
            ({
              href,
              title,
              description,
              icon: Icon,
              spotlightColor,
              iconWrapClass,
              iconClass,
            }) => (
              <Link key={href} href={href} className="block">
                <SpotlightCard
                  className="p-8 flex flex-col gap-5 cursor-pointer"
                  {...(spotlightColor ? { spotlightColor } : {})}
                >
                  <div className={iconWrapClass}>
                    <Icon className={iconClass} strokeWidth={2} />
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-white mb-2">
                      {title}
                    </h3>
                    <p className="text-base text-neutral-400">{description}</p>
                  </div>
                </SpotlightCard>
              </Link>
            ),
          )}
        </div>
      </div>
    </div>
  );
}
