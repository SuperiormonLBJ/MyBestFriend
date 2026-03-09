"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ChevronDown, ChevronUp, FileText } from "lucide-react";

export type MessageRole = "user" | "assistant";

export type SourceItem = {
  source: string;
  section: string;
  doc_type: string;
  year: string;
  snippet: string;
};

export type ChatMessage = {
  id: string;
  role: MessageRole;
  content: string;
  sources?: SourceItem[];
};

type ChatMessageProps = {
  message: ChatMessage;
};

function UserAvatar() {
  return (
    <svg viewBox="0 0 32 32" className="h-5 w-5" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="16" cy="11" r="5" fill="currentColor" stroke="currentColor" strokeWidth="2"/>
      <path d="M6 28c0-5.523 4.477-10 10-10s10 4.477 10 10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="square"/>
    </svg>
  );
}

function BotAvatar() {
  return (
    <svg viewBox="0 0 32 32" className="h-5 w-5" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="6" y="10" width="20" height="16" fill="currentColor" stroke="currentColor" strokeWidth="2"/>
      <rect x="10" y="14" width="4" height="4" fill="var(--background)" stroke="var(--background)" strokeWidth="0.5"/>
      <rect x="18" y="14" width="4" height="4" fill="var(--background)" stroke="var(--background)" strokeWidth="0.5"/>
      <path d="M12 22h8" stroke="var(--background)" strokeWidth="2" strokeLinecap="square"/>
      <path d="M16 10V6" stroke="currentColor" strokeWidth="2" strokeLinecap="square"/>
      <circle cx="16" cy="5" r="1.5" fill="currentColor"/>
    </svg>
  );
}

function SourcesPanel({ sources }: { sources: SourceItem[] }) {
  const [open, setOpen] = useState(false);
  if (!sources.length) return null;

  return (
    <div className="mt-2 border border-[var(--border)] bg-[var(--background)]">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-1.5 font-heading text-[10px] uppercase tracking-widest text-[var(--foreground-muted)] hover:bg-[var(--background-elevated)] transition-colors cursor-pointer"
        aria-expanded={open}
      >
        <FileText className="h-3 w-3 shrink-0" strokeWidth={2.5} />
        <span>{sources.length} source{sources.length > 1 ? "s" : ""}</span>
        {open ? (
          <ChevronUp className="ml-auto h-3 w-3 shrink-0" strokeWidth={2.5} />
        ) : (
          <ChevronDown className="ml-auto h-3 w-3 shrink-0" strokeWidth={2.5} />
        )}
      </button>
      {open && (
        <div className="border-t border-[var(--border)] divide-y divide-[var(--border)]">
          {sources.map((s, i) => (
            <div key={i} className="px-3 py-2 space-y-0.5">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-heading text-[10px] uppercase tracking-wider text-[var(--foreground)] truncate max-w-[200px]">
                  {s.source.replace(/\.md$/, "")}
                </span>
                {s.section && (
                  <span className="font-body text-[10px] text-[var(--foreground-muted)] truncate max-w-[160px]">
                    › {s.section}
                  </span>
                )}
                <div className="ml-auto flex items-center gap-1.5 shrink-0">
                  {s.doc_type && (
                    <span className="rounded-sm border border-[var(--border)] px-1.5 py-0.5 font-heading text-[9px] uppercase tracking-wider text-[var(--foreground-muted)]">
                      {s.doc_type}
                    </span>
                  )}
                  {s.year && (
                    <span className="rounded-sm border border-[var(--border)] px-1.5 py-0.5 font-heading text-[9px] uppercase tracking-wider text-[var(--foreground-muted)]">
                      {s.year}
                    </span>
                  )}
                </div>
              </div>
              {s.snippet && (
                <p className="font-body text-xs text-[var(--foreground-muted)] leading-relaxed line-clamp-2">
                  {s.snippet}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function ChatMessageBubble({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}
      role="article"
      aria-label={isUser ? "Your message" : "Assistant message"}
    >
      <div
        className={`flex h-9 w-9 shrink-0 items-center justify-center border-[3px] border-[var(--border)] ${
          isUser
            ? "bg-[var(--primary)] text-[#000000]"
            : "bg-[var(--background-elevated)] text-[var(--foreground)]"
        }`}
        style={{ boxShadow: "2px 2px 0 var(--border)" }}
      >
        {isUser ? <UserAvatar /> : <BotAvatar />}
      </div>
      <div className={`flex max-w-[80%] flex-col gap-1 ${isUser ? "items-end" : "items-start"}`}>
        <span className="font-heading text-[11px] uppercase tracking-[0.18em] text-[var(--foreground-muted)] px-0.5">
          {isUser ? "YOU" : "BOT"}
        </span>
        <div
          className={`px-4 py-3 border-[3px] border-[var(--border)] ${
            isUser
              ? "bg-[var(--chat-user-bg)] text-[#000000]"
              : "bg-[var(--chat-assistant-bg)] text-[var(--foreground)]"
          }`}
          style={{ boxShadow: "4px 4px 0 var(--border)" }}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap text-base leading-snug font-body font-semibold">{message.content}</p>
          ) : (
            <div className="prose max-w-none font-body text-[var(--foreground)] prose-headings:font-heading prose-headings:text-[var(--foreground)] prose-strong:text-[var(--foreground)] prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-p:my-2 prose-p:leading-relaxed">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="w-full max-w-full">
            <SourcesPanel sources={message.sources} />
          </div>
        )}
      </div>
    </div>
  );
}
