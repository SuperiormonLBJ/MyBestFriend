"use client";

export function TypingIndicator() {
  return (
    <div className="flex gap-3" role="status" aria-label="Assistant is typing">
      <div
        className="flex h-9 w-9 shrink-0 items-center justify-center border-[3px] border-[var(--border)] bg-[var(--background-elevated)] text-[var(--foreground)]"
        style={{ boxShadow: "2px 2px 0 var(--border)" }}
      >
        <span className="sr-only">Typing</span>
      </div>
      <div className="flex flex-col gap-1 items-start">
        <span className="font-heading text-[11px] uppercase tracking-[0.18em] text-[var(--foreground-muted)] px-0.5">
          BOT
        </span>
        <div
          className="flex items-center gap-2 border-[3px] border-[var(--border)] bg-[var(--chat-assistant-bg)] px-4 py-3"
          style={{ boxShadow: "4px 4px 0 var(--border)" }}
        >
          <span
            className="h-2.5 w-2.5 animate-pulse bg-[var(--foreground)]"
            style={{ animationDelay: "0ms" }}
          />
          <span
            className="h-2.5 w-2.5 animate-pulse bg-[var(--secondary)]"
            style={{ animationDelay: "150ms" }}
          />
          <span
            className="h-2.5 w-2.5 animate-pulse bg-[var(--primary)]"
            style={{ animationDelay: "300ms" }}
          />
        </div>
      </div>
    </div>
  );
}
