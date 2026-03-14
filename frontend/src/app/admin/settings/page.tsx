"use client";

import { useConfig } from "@/components/config-provider";
import type { FullConfig } from "@/components/config-provider";
import {
  RefreshCw,
  Save,
  AlertCircle,
  CheckCircle2,
  Palette,
  Bell,
  Cpu,
  Search,
  Shield,
} from "lucide-react";
import { useState, useEffect } from "react";
import { AdminPageHeader } from "@/components/admin-page-header";
import { SectionCard } from "@/components/ui/section-card";
import { getStoredAdminKey } from "@/lib/session-auth";

const EMBEDDING_MODELS = [
  "text-embedding-3-large",
  "text-embedding-3-small",
  "text-embedding-ada-002",
];

const CHAT_MODELS = [
  "gpt-4.1",
  "gpt-4.1-mini",
  "gpt-4o",
  "gpt-4o-mini",
  "gpt-4-turbo",
  "gpt-4-turbo-preview",
  "gpt-3.5-turbo",
];

const EMPTY_FORM: FullConfig = {
  app_name: "",
  owner_name: "",
  embedding_model: "",
  generator_model: "",
  llm_model: "",
  rewrite_model: "",
  reranker_model: "",
  evaluator_model: "",
  recipient_email: "",
  hybrid_search_enabled: true,
  lexical_weight: 0.3,
  metadata_filter_enabled: true,
  self_check_enabled: false,
  multi_step_enabled: false,
  use_graph: false,
  admin_api_key: "",
};

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1">
      <label className="block text-sm font-medium text-[var(--foreground)]">
        {label}
      </label>
      {hint && (
        <p className="text-xs text-[var(--foreground-muted)]">{hint}</p>
      )}
      {children}
    </div>
  );
}

const inputCls =
  "w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--foreground-muted)]/50 focus:border-[var(--primary)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)] transition-colors";

const selectCls =
  "w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-[var(--primary)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)] transition-colors cursor-pointer";

export default function SettingsPage() {
  const { config, isLoading, refetch } = useConfig();
  const [form, setForm] = useState<FullConfig>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  useEffect(() => {
    setForm((prev) => ({ ...prev, ...config }));
  }, [config]);

  const set = (key: keyof FullConfig, value: string) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const payload = Object.fromEntries(
        Object.entries(form).filter(([k, v]) => {
          if (k === "admin_api_key") return v != null;
          return v != null && v !== "";
        })
      ) as Record<string, string>;
      const res = await fetch("/api/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-Admin-Key": getStoredAdminKey() },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || `HTTP ${res.status}`);
      }
      await refetch();
      setMessage({ type: "success", text: "Settings saved to Supabase." });
    } catch (err) {
      setMessage({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to save settings.",
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <AdminPageHeader
        title="SETTINGS"
        subtitle="Changes are saved to Supabase and take effect immediately."
        actions={
          <button
            type="button"
            onClick={() => refetch()}
            disabled={isLoading}
            className="flex items-center gap-2 border-2 border-[#000000]/50 px-3 py-1.5 font-body text-sm font-bold text-[#000000]/80 hover:border-[#000000] hover:bg-[#000000]/10 disabled:opacity-50 transition-colors cursor-pointer"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        }
      />

      {/* Content */}
      <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-6 py-8">
        <div className="mx-auto max-w-2xl space-y-6">
          {/* Alert */}
          {message && (
            <div
              className={`flex items-center gap-2.5 border-2 px-4 py-3 font-body text-sm font-semibold ${
                message.type === "success"
                  ? "border-[var(--border)] bg-[var(--primary)]/20 text-[var(--foreground)]"
                  : "border-red-500 bg-red-500/10 text-red-500"
              }`}
            >
              {message.type === "success" ? (
                <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
              ) : (
                <AlertCircle className="h-4 w-4 shrink-0 text-red-400" />
              )}
              <span>{message.text}</span>
            </div>
          )}

          {/* Section 1 — Identity */}
          <SectionCard
            icon={<Palette className="h-4 w-4 text-amber-400" />}
            title="Identity"
            description="Basic info used throughout the app and chat interface."
          >
            <div className="space-y-4">
              <Field label="App name">
                <input
                  type="text"
                  value={form.app_name ?? ""}
                  onChange={(e) => set("app_name", e.target.value)}
                  placeholder="MyBestFriend"
                  className={inputCls}
                />
              </Field>
              <Field label="Owner name" hint="Your name — used in chat prompts and greetings. Default: Beiji">
                <input
                  type="text"
                  value={form.owner_name ?? ""}
                  onChange={(e) => set("owner_name", e.target.value)}
                  placeholder="Beiji"
                  className={inputCls}
                />
              </Field>
            </div>
          </SectionCard>

          {/* Section 2 — Notifications */}
          <SectionCard
            icon={<Bell className="h-4 w-4 text-sky-400" />}
            title="Notifications"
            description="Email address used for contact form submissions and system alerts."
          >
            <Field label="Recipient email">
              <input
                type="email"
                value={form.recipient_email ?? ""}
                onChange={(e) => set("recipient_email", e.target.value)}
                placeholder="you@example.com"
                className={inputCls}
              />
            </Field>
          </SectionCard>

          {/* Section 3 — AI Models */}
          <SectionCard
            icon={<Cpu className="h-4 w-4 text-violet-400" />}
            title="AI models"
            description="Model changes take effect after restarting the backend server."
          >
            <div className="space-y-4">
              <Field
                label="Embedding model"
                hint="Used to convert documents and queries into vectors."
              >
                <select
                  value={form.embedding_model ?? ""}
                  onChange={(e) => set("embedding_model", e.target.value)}
                  className={selectCls}
                >
                  {form.embedding_model &&
                    !EMBEDDING_MODELS.includes(form.embedding_model) && (
                      <option value={form.embedding_model}>
                        {form.embedding_model}
                      </option>
                    )}
                  {EMBEDDING_MODELS.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </Field>
              <div className="grid grid-cols-2 gap-4">
                <Field
                  label="Generator / LLM model"
                  hint="Used for chat responses and RAG."
                >
                  <select
                    value={form.generator_model ?? ""}
                    onChange={(e) => {
                      set("generator_model", e.target.value);
                      set("llm_model", e.target.value);
                    }}
                    className={selectCls}
                  >
                    {form.generator_model &&
                      !CHAT_MODELS.includes(form.generator_model) && (
                        <option value={form.generator_model}>
                          {form.generator_model}
                        </option>
                      )}
                    {CHAT_MODELS.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field
                  label="Evaluator model"
                  hint="Used for answer quality scoring."
                >
                  <select
                    value={form.evaluator_model ?? ""}
                    onChange={(e) => set("evaluator_model", e.target.value)}
                    className={selectCls}
                  >
                    {form.evaluator_model &&
                      !CHAT_MODELS.includes(form.evaluator_model) && (
                        <option value={form.evaluator_model}>
                          {form.evaluator_model}
                        </option>
                      )}
                    {CHAT_MODELS.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                </Field>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <Field
                  label="Query rewrite model"
                  hint="Used to rephrase user questions for better retrieval."
                >
                  <select
                    value={form.rewrite_model ?? ""}
                    onChange={(e) => set("rewrite_model", e.target.value)}
                    className={selectCls}
                  >
                    {form.rewrite_model &&
                      !CHAT_MODELS.includes(form.rewrite_model) && (
                        <option value={form.rewrite_model}>
                          {form.rewrite_model}
                        </option>
                      )}
                    {CHAT_MODELS.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field
                  label="Reranker model"
                  hint="Used to reorder retrieved chunks by relevance."
                >
                  <select
                    value={form.reranker_model ?? ""}
                    onChange={(e) => set("reranker_model", e.target.value)}
                    className={selectCls}
                  >
                    {form.reranker_model &&
                      !CHAT_MODELS.includes(form.reranker_model) && (
                        <option value={form.reranker_model}>
                          {form.reranker_model}
                        </option>
                      )}
                    {CHAT_MODELS.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                </Field>
              </div>
            </div>
          </SectionCard>

          {/* Section 4 — Retrieval */}
          <SectionCard
            icon={<Search className="h-4 w-4 text-teal-400" />}
            title="Retrieval"
            description="Fine-tune hybrid search, metadata boosting, self-check, and multi-step reasoning."
          >
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-[var(--foreground)]">Hybrid search</p>
                  <p className="text-xs text-[var(--foreground-muted)]">Combine vector similarity with keyword (ILIKE) search</p>
                </div>
                <button
                  type="button"
                  onClick={() => setForm((p) => ({ ...p, hybrid_search_enabled: !p.hybrid_search_enabled }))}
                  className={`relative h-6 w-11 rounded-full border-2 border-[var(--border)] transition-colors cursor-pointer ${form.hybrid_search_enabled ? "bg-[var(--primary)]" : "bg-[var(--background)]"}`}
                  aria-label="Toggle hybrid search"
                >
                  <span className={`absolute top-0.5 left-0 h-4 w-4 rounded-full bg-[var(--border)] transition-transform ${form.hybrid_search_enabled ? "translate-x-5" : "translate-x-0.5"}`} />
                </button>
              </div>
              {form.hybrid_search_enabled && (
                <Field label="Lexical weight" hint="0.0 = vector only · 1.0 = keyword only. Default: 0.3">
                  <input
                    type="number"
                    step="0.05"
                    min="0"
                    max="1"
                    value={form.lexical_weight ?? 0.3}
                    onChange={(e) => setForm((p) => ({ ...p, lexical_weight: parseFloat(e.target.value) || 0.3 }))}
                    className={inputCls}
                  />
                </Field>
              )}
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-[var(--foreground)]">Metadata filter boost</p>
                  <p className="text-xs text-[var(--foreground-muted)]">Softly boost results matching detected year or doc_type</p>
                </div>
                <button
                  type="button"
                  onClick={() => setForm((p) => ({ ...p, metadata_filter_enabled: !p.metadata_filter_enabled }))}
                  className={`relative h-6 w-11 rounded-full border-2 border-[var(--border)] transition-colors cursor-pointer ${form.metadata_filter_enabled ? "bg-[var(--primary)]" : "bg-[var(--background)]"}`}
                  aria-label="Toggle metadata filter"
                >
                  <span className={`absolute top-0.5 left-0 h-4 w-4 rounded-full bg-[var(--border)] transition-transform ${form.metadata_filter_enabled ? "translate-x-5" : "translate-x-0.5"}`} />
                </button>
              </div>
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-[var(--foreground)]">Answer self-check</p>
                  <p className="text-xs text-[var(--foreground-muted)]">Verify all claims are grounded in retrieved context (adds latency)</p>
                </div>
                <button
                  type="button"
                  onClick={() => setForm((p) => ({ ...p, self_check_enabled: !p.self_check_enabled }))}
                  className={`relative h-6 w-11 rounded-full border-2 border-[var(--border)] transition-colors cursor-pointer ${form.self_check_enabled ? "bg-[var(--primary)]" : "bg-[var(--background)]"}`}
                  aria-label="Toggle self-check"
                >
                  <span className={`absolute top-0.5 left-0 h-4 w-4 rounded-full bg-[var(--border)] transition-transform ${form.self_check_enabled ? "translate-x-5" : "translate-x-0.5"}`} />
                </button>
              </div>
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-[var(--foreground)]">Multi-step retrieval</p>
                  <p className="text-xs text-[var(--foreground-muted)]">Run follow-up queries for complex questions (adds latency)</p>
                </div>
                <button
                  type="button"
                  onClick={() => setForm((p) => ({ ...p, multi_step_enabled: !p.multi_step_enabled }))}
                  className={`relative h-6 w-11 rounded-full border-2 border-[var(--border)] transition-colors cursor-pointer ${form.multi_step_enabled ? "bg-[var(--primary)]" : "bg-[var(--background)]"}`}
                  aria-label="Toggle multi-step"
                >
                  <span className={`absolute top-0.5 left-0 h-4 w-4 rounded-full bg-[var(--border)] transition-transform ${form.multi_step_enabled ? "translate-x-5" : "translate-x-0.5"}`} />
                </button>
              </div>
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-[var(--foreground)]">LangGraph orchestrator</p>
                  <p className="text-xs text-[var(--foreground-muted)]">Route non-streaming /api/chat through the graph controller</p>
                </div>
                <button
                  type="button"
                  onClick={() => setForm((p) => ({ ...p, use_graph: !p.use_graph }))}
                  className={`relative h-6 w-11 rounded-full border-2 border-[var(--border)] transition-colors cursor-pointer ${form.use_graph ? "bg-[var(--primary)]" : "bg-[var(--background)]"}`}
                  aria-label="Toggle LangGraph"
                >
                  <span className={`absolute top-0.5 left-0 h-4 w-4 rounded-full bg-[var(--border)] transition-transform ${form.use_graph ? "translate-x-5" : "translate-x-0.5"}`} />
                </button>
              </div>
            </div>
          </SectionCard>

          {/* Section 5 — Security */}
          <SectionCard
            icon={<Shield className="h-4 w-4 text-emerald-500" />}
            title="Security"
            description="Protect admin endpoints with an API key. Leave empty to disable (local dev)."
          >
            <Field label="Admin API key" hint="Set the X-Admin-Key header to this value in admin requests. Leave blank to allow all.">
              <input
                type="password"
                value={form.admin_api_key ?? ""}
                onChange={(e) => set("admin_api_key", e.target.value)}
                placeholder="Leave blank to disable auth"
                className={inputCls}
                autoComplete="new-password"
              />
            </Field>
          </SectionCard>

          {/* Save */}
          <div className="flex justify-end pb-8">
            <button
              type="button"
              onClick={handleSave}
              disabled={saving || isLoading}
              className="flex items-center gap-2 border-2 border-[var(--border)] bg-[var(--primary)] px-6 py-2.5 font-body text-sm font-bold text-[#000000] hover:bg-[var(--primary-hover)] disabled:opacity-50 transition-colors cursor-pointer"
            >
              <Save className="h-4 w-4" />
              {saving ? "Saving…" : "Save changes"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
