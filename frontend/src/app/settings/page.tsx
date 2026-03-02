"use client";

import { useConfig } from "@/components/config-provider";
import type { FullConfig } from "@/components/config-provider";
import { RefreshCw, Save, AlertCircle } from "lucide-react";
import { useState, useEffect } from "react";

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

export default function SettingsPage() {
  const { config, isLoading, refetch } = useConfig();
  const [form, setForm] = useState<FullConfig>({
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
  });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    setForm((prev) => ({ ...prev, ...config }));
  }, [config]);

  const handleChange = (key: keyof FullConfig, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const payload = Object.fromEntries(
        Object.entries(form).filter(([_, v]) => v != null && v !== "")
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
      setMessage({ type: "success", text: "Settings saved successfully." });
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
      <header className="shrink-0 border-b border-[var(--border)] px-6 py-4">
        <h2 className="font-heading text-xl font-bold tracking-wider text-[var(--primary)]">
          SETTINGS
        </h2>
        <p className="mt-1 text-sm text-[var(--foreground-muted)] font-body">
          Edit display options and model selection. Changes are saved to backend/config.yaml.
        </p>
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-8">
        <div className="mx-auto max-w-2xl space-y-8">
          {message && (
            <div
              className={`flex items-center gap-2 rounded-lg border px-4 py-3 ${
                message.type === "success"
                  ? "border-[var(--primary)]/50 bg-[var(--primary)]/10 text-[var(--primary)]"
                  : "border-red-500/50 bg-red-500/10 text-red-400"
              }`}
            >
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{message.text}</span>
            </div>
          )}

          <div className="rounded-lg border border-[var(--border)] bg-[var(--background-elevated)] p-6">
            <div className="mb-6 flex items-center justify-between">
              <h3 className="font-semibold text-[var(--foreground)]">
                Display options
              </h3>
              <button
                type="button"
                onClick={() => refetch()}
                disabled={isLoading}
                className="flex items-center gap-2 rounded-md px-3 py-1.5 text-sm text-[var(--foreground-muted)] hover:bg-[var(--primary)]/10 hover:text-[var(--primary)] transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
                Refresh
              </button>
            </div>
            <div className="space-y-4">
              {(
                [
                  ["app_name", "App name", "text"],
                  ["chat_title", "Chat title", "text"],
                  ["chat_subtitle", "Chat subtitle", "text"],
                  ["input_placeholder", "Input placeholder", "text"],
                  ["empty_state_hint", "Empty state hint", "text"],
                  ["empty_state_examples", "Empty state examples", "text"],
                ] as const
              ).map(([key, label]) => (
                <div key={key}>
                  <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-1">
                    {label}
                  </label>
                  <input
                    type="text"
                    value={form[key] ?? ""}
                    onChange={(e) => handleChange(key, e.target.value)}
                    className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-[var(--foreground)] placeholder:text-[var(--foreground-muted)]/60 focus:border-[var(--primary)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
                  />
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-[var(--border)] bg-[var(--background-elevated)] p-6">
            <h3 className="mb-4 font-semibold text-[var(--foreground)]">
              Model selection
            </h3>
            <p className="mb-4 text-sm text-[var(--foreground-muted)]">
              Model changes take effect after restarting the backend server.
            </p>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-1">
                  Embedding model
                </label>
                <select
                  value={form.embedding_model ?? ""}
                  onChange={(e) => handleChange("embedding_model", e.target.value)}
                  className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-[var(--foreground)] focus:border-[var(--primary)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
                >
                  {form.embedding_model && !EMBEDDING_MODELS.includes(form.embedding_model) && (
                    <option value={form.embedding_model}>{form.embedding_model}</option>
                  )}
                  {EMBEDDING_MODELS.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-1">
                  Generator / LLM model (chat & RAG)
                </label>
                <select
                  value={form.generator_model ?? ""}
                  onChange={(e) => {
                    const v = e.target.value;
                    handleChange("generator_model", v);
                    handleChange("llm_model", v);
                  }}
                  className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-[var(--foreground)] focus:border-[var(--primary)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
                >
                  {form.generator_model && !CHAT_MODELS.includes(form.generator_model) && (
                    <option value={form.generator_model}>{form.generator_model}</option>
                  )}
                  {CHAT_MODELS.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-1">
                  Evaluator model
                </label>
                <select
                  value={form.evaluator_model ?? ""}
                  onChange={(e) => handleChange("evaluator_model", e.target.value)}
                  className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-[var(--foreground)] focus:border-[var(--primary)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
                >
                  {form.evaluator_model && !CHAT_MODELS.includes(form.evaluator_model) && (
                    <option value={form.evaluator_model}>{form.evaluator_model}</option>
                  )}
                  {CHAT_MODELS.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="button"
              onClick={handleSave}
              disabled={saving || isLoading}
              className="flex items-center gap-2 rounded-md bg-[var(--primary)] px-6 py-2.5 font-medium text-[var(--background)] hover:bg-[var(--primary-hover)] disabled:opacity-50 transition-colors"
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
