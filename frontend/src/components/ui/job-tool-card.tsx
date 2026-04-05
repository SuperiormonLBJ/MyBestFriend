"use client";

import { CheckCircle, XCircle, Loader2, Briefcase, Search, Star, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Shared types ────────────────────────────────────────────────────────────

export type JobToolStatus = "loading" | "done" | "error";

export type JobFetchResult = {
  url: string;
  text: string;
  char_count: number;
  success: boolean;
};

export type JobScoreResult = {
  score: number;
  matched_requirements: string[];
  missing_requirements: string[];
  keywords: string[];
  culture_signals: string[];
  doc_count: number;
};

export type JobSearchResult = {
  jobs: {
    title: string;
    company: string;
    location: string;
    url: string;
    posted_at: string;
    tags: string[];
    source: string;
  }[];
  count: number;
};

export type JobToolCardData =
  | { tool: "fetch"; status: JobToolStatus; result?: JobFetchResult }
  | { tool: "score"; status: JobToolStatus; result?: JobScoreResult }
  | { tool: "search"; status: JobToolStatus; result?: JobSearchResult; keywords?: string[] };

// ─── ScoreRing ────────────────────────────────────────────────────────────────

function ScoreRing({ score }: { score: number }) {
  const r = 28;
  const circ = 2 * Math.PI * r;
  const filled = (score / 100) * circ;
  const color =
    score >= 70 ? "#00E6D8" : score >= 45 ? "#F59E0B" : "#EF4444";

  return (
    <div className="relative flex items-center justify-center w-16 h-16 shrink-0">
      <svg width="64" height="64" className="-rotate-90">
        <circle cx="32" cy="32" r={r} fill="none" stroke="#27272a" strokeWidth="5" />
        <circle
          cx="32"
          cy="32"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="5"
          strokeDasharray={`${filled} ${circ - filled}`}
          strokeLinecap="round"
        />
      </svg>
      <span
        className="absolute text-sm font-bold"
        style={{ color }}
      >
        {score}%
      </span>
    </div>
  );
}

// ─── FetchCard ────────────────────────────────────────────────────────────────

function FetchCard({ status, result }: { status: JobToolStatus; result?: JobFetchResult }) {
  const hostname = (() => {
    try { return new URL(result?.url ?? "").hostname.replace("www.", ""); }
    catch { return result?.url ?? ""; }
  })();

  return (
    <div className="flex items-start gap-3">
      <div className="mt-0.5 shrink-0">
        {status === "loading" ? (
          <Loader2 className="h-4 w-4 animate-spin text-[#00E6D8]" />
        ) : status === "error" || (result && !result.success) ? (
          <XCircle className="h-4 w-4 text-red-400" />
        ) : (
          <CheckCircle className="h-4 w-4 text-[#00E6D8]" />
        )}
      </div>
      <div className="min-w-0">
        <p className="font-heading text-xs uppercase tracking-widest text-[#a1a1aa]">
          {status === "loading" ? "Fetching job description…" : status === "error" ? "Fetch failed" : "Job description fetched"}
        </p>
        {hostname && (
          <p className="mt-0.5 font-body text-sm text-[#e4e4e7] truncate">{hostname}</p>
        )}
        {result && result.success && (
          <p className="mt-0.5 font-body text-xs text-[#71717a]">
            {(result.char_count / 1000).toFixed(1)}k chars extracted
          </p>
        )}
        {result && !result.success && (
          <p className="mt-0.5 font-body text-xs text-red-400">
            Page may require login — try pasting the JD text directly
          </p>
        )}
      </div>
    </div>
  );
}

// ─── ScoreCard ────────────────────────────────────────────────────────────────

function ScoreCard({ status, result }: { status: JobToolStatus; result?: JobScoreResult }) {
  return (
    <div>
      <div className="flex items-start gap-3">
        <div className="mt-0.5 shrink-0">
          {status === "loading" ? (
            <Loader2 className="h-4 w-4 animate-spin text-[#00E6D8]" />
          ) : status === "error" ? (
            <XCircle className="h-4 w-4 text-red-400" />
          ) : (
            <Star className="h-4 w-4 text-[#00E6D8]" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-heading text-xs uppercase tracking-widest text-[#a1a1aa]">
            {status === "loading" ? "Scoring job fit…" : status === "error" ? "Score failed" : "Fit score"}
          </p>
        </div>
        {result && <ScoreRing score={result.score} />}
      </div>

      {result && (
        <div className="mt-3 space-y-2">
          {/* Keywords */}
          {result.keywords.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {result.keywords.slice(0, 8).map((kw) => (
                <span
                  key={kw}
                  className="border border-[#3f3f46] bg-[#27272a] px-2 py-0.5 font-body text-xs text-[#a1a1aa] uppercase tracking-wider"
                >
                  {kw}
                </span>
              ))}
            </div>
          )}

          {/* Matched */}
          {result.matched_requirements.length > 0 && (
            <div>
              <p className="font-heading text-[10px] uppercase tracking-widest text-[#52525b] mb-1">Matched</p>
              <ul className="space-y-0.5">
                {result.matched_requirements.slice(0, 5).map((r, i) => (
                  <li key={i} className="flex items-start gap-1.5 font-body text-xs text-[#d4d4d8]">
                    <CheckCircle className="h-3 w-3 shrink-0 mt-0.5 text-[#00E6D8]" />
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Missing */}
          {result.missing_requirements.length > 0 && (
            <div>
              <p className="font-heading text-[10px] uppercase tracking-widest text-[#52525b] mb-1">Gap</p>
              <ul className="space-y-0.5">
                {result.missing_requirements.slice(0, 4).map((r, i) => (
                  <li key={i} className="flex items-start gap-1.5 font-body text-xs text-[#71717a]">
                    <XCircle className="h-3 w-3 shrink-0 mt-0.5 text-[#52525b]" />
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── SearchCard ───────────────────────────────────────────────────────────────

function SearchCard({
  status,
  result,
  keywords,
}: {
  status: JobToolStatus;
  result?: JobSearchResult;
  keywords?: string[];
}) {
  return (
    <div>
      <div className="flex items-start gap-3">
        <div className="mt-0.5 shrink-0">
          {status === "loading" ? (
            <Loader2 className="h-4 w-4 animate-spin text-[#00E6D8]" />
          ) : status === "error" ? (
            <XCircle className="h-4 w-4 text-red-400" />
          ) : (
            <Search className="h-4 w-4 text-[#00E6D8]" />
          )}
        </div>
        <div className="min-w-0">
          <p className="font-heading text-xs uppercase tracking-widest text-[#a1a1aa]">
            {status === "loading"
              ? `Searching similar roles…`
              : status === "error"
              ? "Search failed"
              : `${result?.count ?? 0} similar role${result?.count !== 1 ? "s" : ""} found`}
          </p>
          {keywords && keywords.length > 0 && (
            <p className="mt-0.5 font-body text-xs text-[#71717a]">
              {keywords.slice(0, 4).join(" · ")}
            </p>
          )}
        </div>
      </div>

      {result && result.jobs.length > 0 && (
        <ul className="mt-3 space-y-2">
          {result.jobs.slice(0, 5).map((job, i) => (
            <li key={i} className="border border-[#3f3f46] bg-[#1c1c1f] p-2.5">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="font-body text-sm font-semibold text-[#e4e4e7] truncate">{job.title}</p>
                  <p className="font-body text-xs text-[#71717a]">
                    {job.company} · {job.location}
                  </p>
                  {job.tags.length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {job.tags.slice(0, 4).map((t) => (
                        <span key={t} className="font-body text-[10px] text-[#52525b] bg-[#27272a] border border-[#3f3f46] px-1.5 py-0.5">
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                {job.url && (
                  <a
                    href={job.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="shrink-0 text-[#00E6D8] hover:text-[#00E6D8]/70 transition-colors"
                    aria-label="Open job posting"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </a>
                )}
              </div>
              <p className="mt-1 font-body text-[10px] text-[#52525b]">via {job.source}</p>
            </li>
          ))}
        </ul>
      )}

      {result && result.jobs.length === 0 && status === "done" && (
        <div className="mt-2 space-y-1">
          <p className="font-body text-xs text-[#52525b]">
            No postings found in this time window.
          </p>
          <p className="font-body text-xs text-[#3f3f46]">
            Sources: Arbeitnow · RemoteOK (public, no login required).
            LinkedIn requires authentication and cannot be searched directly.
            Try broader keywords or a longer window (e.g. &ldquo;past week&rdquo;).
          </p>
        </div>
      )}
    </div>
  );
}

// ─── JobToolCard (main export) ────────────────────────────────────────────────

export function JobToolCard({ data }: { data: JobToolCardData }) {
  return (
    <div
      className={cn(
        "border-2 bg-[#18181b] p-4 transition-colors duration-300",
        data.status === "loading"
          ? "border-[#00E6D8]/30"
          : data.status === "error"
          ? "border-red-500/40"
          : "border-[#00E6D8]/60"
      )}
      style={{ boxShadow: "3px 3px 0 0 rgba(0,230,216,0.12)" }}
    >
      {/* Header chip */}
      <div className="flex items-center gap-1.5 mb-3">
        <Briefcase className="h-3.5 w-3.5 text-[#00E6D8]" />
        <span className="font-heading text-[10px] uppercase tracking-widest text-[#00E6D8]">
          Job Mode
        </span>
      </div>

      {data.tool === "fetch" && <FetchCard status={data.status} result={data.result} />}
      {data.tool === "score" && <ScoreCard status={data.status} result={data.result} />}
      {data.tool === "search" && (
        <SearchCard status={data.status} result={data.result} keywords={data.keywords} />
      )}
    </div>
  );
}
