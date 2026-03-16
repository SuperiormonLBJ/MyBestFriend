"use client";

import { useState } from "react";

export default function ResumePage() {
  const [jobDescription, setJobDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [markdown, setMarkdown] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!jobDescription.trim()) {
      setError("Job description is required.");
      return;
    }
    if (!file) {
      setError("Please upload your resume PDF.");
      return;
    }

    const formData = new FormData();
    formData.append("job_description", jobDescription);
    formData.append("resume_pdf", file);

    setLoading(true);
    try {
      const res = await fetch("/api/resume/rewrite", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to rewrite resume.");
      }
      const data = await res.json();
      setMarkdown(data.markdown_resume || "");
    } catch (err: any) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadDocx = async () => {
    setError("");
    if (!markdown.trim()) {
      setError("Generate a resume first before downloading.");
      return;
    }
    try {
      const res = await fetch("/api/resume/docx", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ markdown_resume: markdown }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || data.error || "Failed to generate Word file.");
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "rewritten_resume.docx";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err.message || "Something went wrong while downloading.");
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-[var(--background)]">
      <header className="border-b-2 border-[var(--border)] bg-[var(--primary)] px-6 py-4">
        <h2 className="font-heading text-2xl uppercase tracking-wide text-black">
          Resume Rewriter
        </h2>
        <p className="mt-1 text-sm font-body text-black/80">
          Upload your PDF resume and paste a job description to get a tailored Markdown resume.
        </p>
      </header>

      <main className="flex flex-1 flex-col gap-6 p-6 lg:flex-row">
        <form
          onSubmit={handleSubmit}
          className="w-full max-w-xl space-y-4 border-2 border-[var(--border)] bg-[var(--surface)] p-4"
        >
          <label className="block text-sm font-semibold uppercase tracking-wide text-[var(--foreground-muted)]">
            Job Description
            <textarea
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              rows={10}
              className="mt-1 w-full border border-[var(--border)] bg-[var(--background)] p-2 text-sm text-[var(--foreground)]"
            />
          </label>

          <label className="block text-sm font-semibold uppercase tracking-wide text-[var(--foreground-muted)]">
            Resume PDF
            <input
              type="file"
              accept="application/pdf"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="mt-1 block w-full text-sm text-[var(--foreground)]"
            />
          </label>

          {error && (
            <p className="text-xs font-semibold uppercase text-[var(--secondary)]">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="border-2 border-[var(--border)] bg-[var(--primary)] px-4 py-2 text-sm font-bold uppercase tracking-wide text-black disabled:opacity-60"
          >
            {loading ? "Rewriting…" : "Rewrite Resume"}
          </button>
        </form>

        <section className="flex-1 border-2 border-[var(--border)] bg-[var(--background-elevated)] p-4">
          <h3 className="mb-2 text-sm font-heading uppercase tracking-wide text-[var(--foreground-muted)]">
            Markdown Resume Output
          </h3>
          {markdown ? (
            <>
              <pre className="max-h-[70vh] overflow-auto whitespace-pre-wrap rounded border border-[var(--border)] bg-[var(--surface)] p-3 text-sm text-[var(--foreground)]">
                {markdown}
              </pre>
              <div className="mt-3">
                <button
                  type="button"
                  onClick={handleDownloadDocx}
                  className="border-2 border-[var(--border)] bg-[var(--primary)] px-4 py-2 text-xs font-bold uppercase tracking-wide text-black"
                >
                  Download as Word (.docx)
                </button>
              </div>
            </>
          ) : (
            <p className="text-sm text-[var(--foreground-muted)]">
              The generated Markdown resume will appear here.
            </p>
          )}
        </section>
      </main>
    </div>
  );
}