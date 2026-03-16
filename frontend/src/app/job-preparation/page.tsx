"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Copy, Loader2 } from "lucide-react";

const DEFAULT_WORD_LIMIT = 400;

export default function JobPreparationPage() {
  const [jobDescription, setJobDescription] = useState("");
  const [wordLimit, setWordLimit] = useState(DEFAULT_WORD_LIMIT);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{
    cover_letter: string;
    word_limit: number;
    technical_requirements: string[];
    culture: string[];
    keywords: string[];
    resume_suggestions: string;
    interview_questions: string;
  } | null>(null);
  const [copied, setCopied] = useState(false);
  const [showTech, setShowTech] = useState(false);
  const [activeView, setActiveView] = useState<"cover" | "resume" | "interview">("cover");

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
      const res = await fetch("/api/job/prepare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_description: jobDescription.trim(),
          word_limit: wordLimit > 0 ? wordLimit : DEFAULT_WORD_LIMIT,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || data.error || "Failed to generate preparation");
        return;
      }
      setResult({
        cover_letter: data.cover_letter,
        word_limit: data.word_limit,
        technical_requirements: data.technical_requirements ?? [],
        culture: data.culture ?? [],
        keywords: data.keywords ?? [],
        resume_suggestions: data.resume_suggestions ?? "",
        interview_questions: data.interview_questions ?? "",
      });
      setActiveView("cover");
    } catch (err) {
      setError("Request failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!result) return;
    try {
      const text =
        activeView === "cover"
          ? result.cover_letter
          : activeView === "resume"
          ? result.resume_suggestions
          : result.interview_questions;
      if (!text) return;
      await navigator.clipboard.writeText(text);
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
              Generate tailored preparation from job descriptions
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
                "Generate preparation"
              )}
            </button>
          </form>

          {result && (
            <div className="space-y-4">
              {(result.technical_requirements.length > 0 ||
                result.culture.length > 0 ||
                result.keywords.length > 0) && (
                <div
                  className="rounded-xl border-2 border-[var(--border)] bg-[var(--surface)] p-6"
                  style={{ boxShadow: "4px 4px 0 0 var(--border)" }}
                >
                  <h3 className="mb-3 font-heading text-sm uppercase tracking-wide text-[var(--foreground-muted)]">
                    Job analysis
                  </h3>
                  <div className="space-y-4">
                    {result.technical_requirements.length > 0 && (
                      <div>
                        <button
                          type="button"
                          onClick={() => setShowTech((v) => !v)}
                          className="flex w-full items-center justify-between border border-[var(--border)] bg-[var(--surface)] px-3 py-2 font-body text-xs font-semibold uppercase tracking-wide text-[var(--foreground)] cursor-pointer"
                        >
                          <span>Technical requirements ({result.technical_requirements.length})</span>
                          <span>{showTech ? "−" : "+"}</span>
                        </button>
                        {showTech && (
                          <ul className="mt-2 list-disc space-y-1 pl-5 font-body text-sm text-[var(--foreground)]">
                            {result.technical_requirements.map((item, idx) => (
                              <li key={idx}>{item}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    )}
                    {result.culture.length > 0 && (
                      <div>
                        <h4 className="mb-1 font-body text-xs font-semibold uppercase tracking-wide text-[var(--foreground-muted)]">
                          Culture
                        </h4>
                        <ul className="list-disc space-y-1 pl-5 font-body text-sm text-[var(--foreground)]">
                          {result.culture.map((item, idx) => (
                            <li key={idx}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {result.keywords.length > 0 && (
                      <div>
                        <h4 className="mb-1 font-body text-xs font-semibold uppercase tracking-wide text-[var(--foreground-muted)]">
                          Keywords
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {result.keywords.map((kw, idx) => (
                            <span
                              key={idx}
                              className="rounded-full border border-[var(--border)] bg-[var(--background)] px-2 py-1 font-body text-xs text-[var(--foreground)]"
                            >
                              {kw}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
              <div
                className="rounded-xl border-2 border-[var(--border)] bg-[var(--surface)] p-6"
                style={{ boxShadow: "4px 4px 0 0 var(--border)" }}
              >
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] pb-3 mb-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setActiveView("cover")}
                      className={`px-3 py-1 text-xs font-body font-semibold uppercase tracking-wide border-2 cursor-pointer ${
                        activeView === "cover"
                          ? "bg-[var(--primary)] text-[#000000] border-[var(--border)]"
                          : "bg-[var(--surface)] text-[var(--foreground)] border-[var(--border)]"
                      }`}
                    >
                      Cover letter
                    </button>
                    <button
                      type="button"
                      onClick={() => setActiveView("resume")}
                      className={`px-3 py-1 text-xs font-body font-semibold uppercase tracking-wide border-2 cursor-pointer ${
                        activeView === "resume"
                          ? "bg-[var(--primary)] text-[#000000] border-[var(--border)]"
                          : "bg-[var(--surface)] text-[var(--foreground)] border-[var(--border)]"
                      }`}
                    >
                      Resume suggestions
                    </button>
                    <button
                      type="button"
                      onClick={() => setActiveView("interview")}
                      className={`px-3 py-1 text-xs font-body font-semibold uppercase tracking-wide border-2 cursor-pointer ${
                        activeView === "interview"
                          ? "bg-[var(--primary)] text-[#000000] border-[var(--border)]"
                          : "bg-[var(--surface)] text-[var(--foreground)] border-[var(--border)]"
                      }`}
                    >
                      Interview questions
                    </button>
                  </div>
                  <button
                    type="button"
                    onClick={handleCopy}
                    className="flex items-center gap-2 border-2 border-[var(--border)] px-3 py-2 font-body text-sm font-semibold uppercase tracking-wide text-[var(--foreground)] transition-colors hover:bg-[var(--border)] cursor-pointer"
                  >
                    <Copy className="h-4 w-4 shrink-0" />
                    {copied ? "Copied" : "Copy"}
                  </button>
                </div>
                <div className="font-body text-sm leading-relaxed text-[var(--foreground)]">
                  <div className="prose max-w-none font-body text-[var(--foreground)] prose-headings:font-heading prose-headings:text-[var(--foreground)] prose-strong:text-[var(--foreground)] prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-p:my-2 prose-p:leading-relaxed">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {activeView === "cover"
                        ? result.cover_letter
                        : activeView === "resume"
                        ? result.resume_suggestions || "No resume suggestions available."
                        : result.interview_questions || "No interview questions available."}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
