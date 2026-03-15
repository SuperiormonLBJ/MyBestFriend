"use client";

import { useState } from "react";
import { Copy, Loader2 } from "lucide-react";

const DEFAULT_WORD_LIMIT = 400;

export default function JobPreparationPage() {
  const [jobDescription, setJobDescription] = useState("");
  const [wordLimit, setWordLimit] = useState(DEFAULT_WORD_LIMIT);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ cover_letter: string; word_limit: number } | null>(null);
  const [copied, setCopied] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    if (!jobDescription.trim()) {
      setError("Please paste a job description.");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch("/api/job/cover-letter", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_description: jobDescription.trim(),
          word_limit: wordLimit > 0 ? wordLimit : DEFAULT_WORD_LIMIT,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || data.error || "Failed to generate cover letter");
        return;
      }
      setResult({ cover_letter: data.cover_letter, word_limit: data.word_limit });
    } catch (err) {
      setError("Request failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!result?.cover_letter) return;
    try {
      await navigator.clipboard.writeText(result.cover_letter);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Copy failed");
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <header className="shrink-0 border-b-2 border-[var(--border)] bg-[var(--primary)] px-6 py-4 header-texture">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <h2 className="font-heading text-3xl text-[#000000] uppercase tracking-wide">
              JOB PREPARATION
            </h2>
            <p className="mt-1 font-body text-base font-bold text-[#000000]/75 uppercase tracking-widest">
              Generate tailored cover letters from job descriptions
            </p>
          </div>
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-6 py-8">
        <div className="mx-auto max-w-2xl space-y-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="jd"
                className="block font-body text-sm font-semibold uppercase tracking-wide text-[var(--foreground)]"
              >
                Job description
              </label>
              <textarea
                id="jd"
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder="Paste the full job description here…"
                rows={10}
                disabled={loading}
                className="mt-2 w-full resize-y rounded-md border-2 border-[var(--border)] bg-[var(--background)] px-3 py-2 font-body text-sm text-[var(--foreground)] placeholder:text-[var(--foreground-muted)] focus:border-[var(--primary)] focus:outline-none disabled:opacity-60"
              />
            </div>
            <div>
              <label
                htmlFor="word-limit"
                className="block font-body text-sm font-semibold uppercase tracking-wide text-[var(--foreground)]"
              >
                Word limit
              </label>
              <input
                id="word-limit"
                type="number"
                min={100}
                max={1500}
                value={wordLimit}
                onChange={(e) => setWordLimit(parseInt(e.target.value, 10) || DEFAULT_WORD_LIMIT)}
                disabled={loading}
                className="mt-2 w-32 rounded-md border-2 border-[var(--border)] bg-[var(--background)] px-3 py-2 font-body text-sm text-[var(--foreground)] focus:border-[var(--primary)] focus:outline-none disabled:opacity-60"
              />
              <p className="mt-1 font-body text-xs text-[var(--foreground-muted)]">
                e.g. 400 words. The model will be instructed to stay under this limit.
              </p>
            </div>
            {error && (
              <p className="font-body text-sm font-semibold text-red-500" role="alert">
                {error}
              </p>
            )}
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 border-2 border-[#000000] bg-[var(--primary)] px-4 py-3 font-heading text-sm uppercase tracking-wide text-[#000000] transition-colors duration-150 hover:bg-[#000000] hover:text-[var(--primary)] disabled:opacity-60 cursor-pointer"
              style={{ boxShadow: "3px 3px 0 0 rgba(0,0,0,0.35)" }}
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
                  Generating…
                </>
              ) : (
                "Generate cover letter"
              )}
            </button>
          </form>

          {result && (
            <div
              className="rounded-xl border-2 border-[var(--border)] bg-[var(--surface)] p-6"
              style={{ boxShadow: "4px 4px 0 0 var(--border)" }}
            >
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] pb-3 mb-4">
                <span className="font-body text-xs uppercase tracking-wider text-[var(--foreground-muted)]">
                  Under {result.word_limit} words
                </span>
                <button
                  type="button"
                  onClick={handleCopy}
                  className="flex items-center gap-2 border-2 border-[var(--border)] px-3 py-2 font-body text-sm font-semibold uppercase tracking-wide text-[var(--foreground)] transition-colors hover:bg-[var(--border)] cursor-pointer"
                >
                  <Copy className="h-4 w-4 shrink-0" />
                  {copied ? "Copied" : "Copy"}
                </button>
              </div>
              <div className="font-body text-sm leading-relaxed text-[var(--foreground)] whitespace-pre-wrap">
                {result.cover_letter}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
