"use client";

import { useConfig } from "@/components/config-provider";
import type { FullConfig } from "@/components/config-provider";
import {
  RefreshCw,
  Save,
  AlertCircle,
  CheckCircle2,
  Palette,
  MessageSquare,
  Bell,
  Cpu,
} from "lucide-react";
import { useState, useEffect } from "react";
import Link from "next/link";

const EMBEDDING_MODELS = [
  "text-embedding-3-large",
  "text-embedding-3-small",
  "text-embedding-ada-002",
];

const CHAT_MODELS = [
  "gpt-4o",
  "gpt-4o-mini",
  "gpt-4-turbo",
  "gpt-4-turbo-preview",
  "gpt-3.5-turbo",
];

const EMPTY_FORM: FullConfig = {
  app_name: "",
  chat_title: "",
  chat_subtitle: "",
  input_placeholder: "",
  empty_state_hint: "",
  empty_state_examples: "",
  embedding_model: "",
  generator_model: "",
  llm_model: "",
  evaluator_model: "",
  recipient_email: "",
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

function SectionCard({
  icon,
  title,
  description,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--background-elevated)]">
      <div className="flex items-start gap-3 border-b border-[var(--border)] px-6 py-4">
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--primary)]/10 text-[var(--primary)]">
          {icon}
        </div>
        <div>
          <h3 className="text-sm font-semibold text-[var(--foreground)]">{title}</h3>
          <p className="mt-0.5 text-xs text-[var(--foreground-muted)]">{description}</p>
        </div>
      </div>
      <div className="p-6">{children}</div>
    </div>
  );
}

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
        Object.entries(form).filter(([, v]) => v != null && v !== "")
      ) as Record<string, string>;
      const res = await fetch("/api/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
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
    <div className="flex min-h-full flex-1 flex-col">
      {/* Header */}
      <header className="shrink-0 border-b border-[var(--border)] px-6 py-4">
        <Link
          href="/admin"
          className="mb-2 inline-block text-sm text-[var(--foreground-muted)] hover:text-[var(--primary)] transition-colors"
        >
          ← Admin Panel
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-heading text-xl font-bold tracking-wider text-[var(--primary)]">
              SETTINGS
            </h2>
            <p className="mt-0.5 text-sm text-[var(--foreground-muted)]">
              Changes are saved to Supabase and take effect immediately.
            </p>
          </div>
          <button
            type="button"
            onClick={() => refetch()}
            disabled={isLoading}
            className="flex items-center gap-2 rounded-md px-3 py-1.5 text-sm text-[var(--foreground-muted)] hover:bg-[var(--primary)]/10 hover:text-[var(--primary)] disabled:opacity-50 transition-colors cursor-pointer"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-8">
        <div className="mx-auto max-w-2xl space-y-6">
          {/* Alert */}
          {message && (
            <div
              className={`flex items-center gap-2.5 rounded-lg border px-4 py-3 text-sm ${
                message.type === "success"
                  ? "border-[var(--primary)]/40 bg-[var(--primary)]/10 text-[var(--primary)]"
                  : "border-red-500/40 bg-red-500/10 text-red-400"
              }`}
            >
              {message.type === "success" ? (
                <CheckCircle2 className="h-4 w-4 shrink-0" />
              ) : (
                <AlertCircle className="h-4 w-4 shrink-0" />
              )}
              <span>{message.text}</span>
            </div>
          )}

          {/* Section 1 — Identity */}
          <SectionCard
            icon={<Palette className="h-4 w-4" />}
            title="Identity"
            description="The app name shown in the browser tab and sidebar."
          >
            <Field label="App name">
              <input
                type="text"
                value={form.app_name ?? ""}
                onChange={(e) => set("app_name", e.target.value)}
                placeholder="MyBestFriend"
                className={inputCls}
              />
            </Field>
          </SectionCard>

          {/* Section 2 — Chat Display */}
          <SectionCard
            icon={<MessageSquare className="h-4 w-4" />}
            title="Chat display"
            description="Controls the text users see in the chat interface."
          >
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <Field label="Chat title">
                  <input
                    type="text"
                    value={form.chat_title ?? ""}
                    onChange={(e) => set("chat_title", e.target.value)}
                    placeholder="Digital Twin"
                    className={inputCls}
                  />
                </Field>
                <Field label="Chat subtitle">
                  <input
                    type="text"
                    value={form.chat_subtitle ?? ""}
                    onChange={(e) => set("chat_subtitle", e.target.value)}
                    placeholder="Ask anything about me…"
                    className={inputCls}
                  />
                </Field>
              </div>
              <Field label="Input placeholder">
                <input
                  type="text"
                  value={form.input_placeholder ?? ""}
                  onChange={(e) => set("input_placeholder", e.target.value)}
                  placeholder="Ask anything about me..."
                  className={inputCls}
                />
              </Field>
              <Field label="Empty state hint">
                <input
                  type="text"
                  value={form.empty_state_hint ?? ""}
                  onChange={(e) => set("empty_state_hint", e.target.value)}
                  placeholder="Type a question or use the microphone…"
                  className={inputCls}
                />
              </Field>
              <Field
                label="Empty state examples"
                hint="Example prompts shown when the chat is empty."
              >
                <textarea
                  rows={3}
                  value={form.empty_state_examples ?? ""}
                  onChange={(e) => set("empty_state_examples", e.target.value)}
                  placeholder='Try: "What is your experience at UOB?" or "Tell me about your hobbies"'
                  className={`${inputCls} resize-none`}
                />
              </Field>
            </div>
          </SectionCard>

          {/* Section 3 — Notifications */}
          <SectionCard
            icon={<Bell className="h-4 w-4" />}
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

          {/* Section 4 — AI Models */}
          <SectionCard
            icon={<Cpu className="h-4 w-4" />}
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
            </div>
          </SectionCard>

          {/* Save */}
          <div className="flex justify-end pb-8">
            <button
              type="button"
              onClick={handleSave}
              disabled={saving || isLoading}
              className="flex items-center gap-2 rounded-md bg-[var(--primary)] px-6 py-2.5 text-sm font-medium text-[var(--background)] hover:bg-[var(--primary-hover)] disabled:opacity-50 transition-colors cursor-pointer"
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
