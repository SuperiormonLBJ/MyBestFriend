"use client";

import {
  RefreshCw,
  Save,
  RotateCcw,
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { useState, useEffect, useCallback } from "react";
import { AdminPageHeader } from "@/components/admin-page-header";
import { getStoredAdminKey } from "@/lib/session-auth";

type Prompt = {
  key: string;
  content: string;
  description: string;
};

type PromptState = {
  draft: string;
  saving: boolean;
  resetting: boolean;
  message: { type: "success" | "error"; text: string } | null;
  expanded: boolean;
};

const KEY_LABELS: Record<string, string> = {
  SYSTEM_PROMPT_GENERATOR: "Answer Generator",
  SYSTEM_PROMPT_RERANKER: "Document Re-ranker",
  REWRITE_PROMPT: "Query Rewriter",
  RESTRUCTURE_TO_MD_PROMPT: "Document Structurer",
  LINKEDIN_PROMPT: "LinkedIn Cleaner",
};

export default function PromptsPage() {
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [states, setStates] = useState<Record<string, PromptState>>({});
  const [loading, setLoading] = useState(true);

  const loadPrompts = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/prompts", { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const list: Prompt[] = data.prompts || [];
      setPrompts(list);
      setStates((prev) => {
        const next: Record<string, PromptState> = {};
        for (const p of list) {
          next[p.key] = {
            draft: p.content,
            saving: false,
            resetting: false,
            message: prev[p.key]?.message ?? null,
            expanded: prev[p.key]?.expanded ?? false,
          };
        }
        return next;
      });
    } catch (err) {
      console.error("Failed to load prompts", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPrompts();
  }, [loadPrompts]);

  const setDraft = (key: string, value: string) =>
    setStates((prev) => ({
      ...prev,
      [key]: { ...prev[key], draft: value, message: null },
    }));

  const toggleExpand = (key: string) =>
    setStates((prev) => ({
      ...prev,
      [key]: { ...prev[key], expanded: !prev[key].expanded },
    }));

  const setMsg = (key: string, message: PromptState["message"]) =>
    setStates((prev) => ({ ...prev, [key]: { ...prev[key], message } }));

  const handleSave = async (key: string) => {
    const draft = states[key]?.draft;
    if (!draft?.trim()) return;
    setStates((prev) => ({ ...prev, [key]: { ...prev[key], saving: true, message: null } }));
    try {
      const res = await fetch(`/api/prompts/${key}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-Admin-Key": getStoredAdminKey() },
        body: JSON.stringify({ content: draft }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.error || `HTTP ${res.status}`);
      }
      setMsg(key, { type: "success", text: "Saved to Supabase." });
    } catch (err) {
      setMsg(key, {
        type: "error",
        text: err instanceof Error ? err.message : "Save failed.",
      });
    } finally {
      setStates((prev) => ({ ...prev, [key]: { ...prev[key], saving: false } }));
    }
  };

  const handleReset = async (key: string) => {
    setStates((prev) => ({
      ...prev,
      [key]: { ...prev[key], resetting: true, message: null },
    }));
    try {
      const res = await fetch(`/api/prompts/${key}`, { method: "POST", headers: { "X-Admin-Key": getStoredAdminKey() } });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.error || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setStates((prev) => ({
        ...prev,
        [key]: {
          ...prev[key],
          draft: data.content,
          message: { type: "success", text: "Reset to default." },
        },
      }));
    } catch (err) {
      setMsg(key, {
        type: "error",
        text: err instanceof Error ? err.message : "Reset failed.",
      });
    } finally {
      setStates((prev) => ({ ...prev, [key]: { ...prev[key], resetting: false } }));
    }
  };

  const isDirty = (p: Prompt) =>
    states[p.key] && states[p.key].draft !== p.content;

  return (
    <div className="flex min-h-full flex-1 flex-col">
      <AdminPageHeader
        title="PROMPTS"
        subtitle="Edit LLM system prompts. Changes are saved to Supabase and take effect immediately."
        actions={
          <button
            type="button"
            onClick={loadPrompts}
            disabled={loading}
            className="flex items-center gap-2 border-2 border-[#000000]/50 px-3 py-1.5 font-body text-sm font-bold text-[#000000]/80 hover:border-[#000000] hover:bg-[#000000]/10 disabled:opacity-50 transition-colors cursor-pointer"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        }
      />

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-8">
        <div className="mx-auto max-w-3xl space-y-4">
          {loading && (
            <div className="py-12 text-center text-sm text-[var(--foreground-muted)]">
              Loading prompts…
            </div>
          )}

          {!loading &&
            prompts.map((p) => {
              const s = states[p.key];
              if (!s) return null;
              const label = KEY_LABELS[p.key] ?? p.key;
              const dirty = isDirty(p);
              const charCount = s.draft.length;

              return (
                <div
                  key={p.key}
                  className="rounded-xl border border-[var(--border)] bg-[var(--background-elevated)] overflow-hidden"
                >
                  {/* Card header — always visible */}
                  <button
                    type="button"
                    onClick={() => toggleExpand(p.key)}
                    className="w-full flex items-center justify-between gap-4 px-6 py-4 text-left hover:bg-[var(--primary)]/5 transition-colors cursor-pointer"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <code className="shrink-0 border border-[var(--border)] bg-[var(--surface)] px-2 py-0.5 text-xs font-mono text-[var(--foreground)]">
                        {p.key}
                      </code>
                      <div className="min-w-0">
                        <span className="block text-sm font-semibold text-[var(--foreground)]">
                          {label}
                        </span>
                        <span className="block truncate text-xs text-[var(--foreground-muted)]">
                          {p.description}
                        </span>
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      {dirty && (
                        <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-xs font-medium text-amber-500">
                          unsaved
                        </span>
                      )}
                      {s.expanded ? (
                        <ChevronUp className="h-4 w-4 text-neutral-400" />
                      ) : (
                        <ChevronDown className="h-4 w-4 text-neutral-400" />
                      )}
                    </div>
                  </button>

                  {/* Expanded editor */}
                  {s.expanded && (
                    <div className="border-t border-[var(--border)] px-6 py-5 space-y-3">
                      {/* Status message */}
                      {s.message && (
                        <div
                          className={`flex items-center gap-2 border-2 px-3 py-2 font-body text-xs font-semibold ${
                            s.message.type === "success"
                              ? "border-[var(--border)] bg-[var(--primary)]/20 text-[var(--foreground)]"
                              : "border-red-500 bg-red-500/10 text-red-500"
                          }`}
                        >
                          {s.message.type === "success" ? (
                            <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-500" />
                          ) : (
                            <AlertCircle className="h-3.5 w-3.5 shrink-0 text-red-400" />
                          )}
                          {s.message.text}
                        </div>
                      )}

                      {/* Textarea */}
                      <textarea
                        rows={14}
                        value={s.draft}
                        onChange={(e) => setDraft(p.key, e.target.value)}
                        spellCheck={false}
                        className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2.5 font-mono text-xs text-[var(--foreground)] leading-relaxed placeholder:text-[var(--foreground-muted)]/50 focus:border-[var(--primary)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)] resize-y transition-colors"
                      />

                      {/* Footer: char count + actions */}
                      <div className="flex items-center justify-between gap-4">
                        <span className="text-xs text-[var(--foreground-muted)]">
                          {charCount.toLocaleString()} characters
                        </span>
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => handleReset(p.key)}
                            disabled={s.resetting || s.saving}
                            title="Reset to default"
                            className="flex items-center gap-1.5 rounded-md border border-[var(--border)] px-3 py-1.5 text-xs text-[var(--foreground-muted)] hover:border-[var(--primary)]/50 hover:text-[var(--primary)] disabled:opacity-50 transition-colors cursor-pointer"
                          >
                            <RotateCcw className={`h-3.5 w-3.5 ${s.resetting ? "animate-spin" : ""}`} />
                            {s.resetting ? "Resetting…" : "Reset to default"}
                          </button>
                          <button
                            type="button"
                            onClick={() => handleSave(p.key)}
                            disabled={s.saving || s.resetting || !s.draft.trim()}
                            className="flex items-center gap-1.5 border-2 border-[var(--border)] bg-[var(--primary)] px-4 py-1.5 font-body text-xs font-bold text-[#000000] hover:bg-[var(--primary-hover)] disabled:opacity-50 transition-colors cursor-pointer"
                          >
                            <Save className="h-3.5 w-3.5" />
                            {s.saving ? "Saving…" : "Save"}
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
        </div>
      </div>
    </div>
  );
}
