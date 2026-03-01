"use client";

export function TypingIndicator() {
  return (
    <div className="flex gap-3" role="status" aria-label="Assistant is typing">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--chat-assistant-bg)] text-[var(--primary)]">
        <span className="sr-only">Typing</span>
      </div>
      <div className="flex items-center gap-1 rounded-2xl bg-[var(--chat-assistant-bg)] px-4 py-3">
        <span
          className="h-2 w-2 animate-pulse rounded-full bg-[var(--primary)]"
          style={{ animationDelay: "0ms" }}
        />
        <span
          className="h-2 w-2 animate-pulse rounded-full bg-[var(--primary)]"
          style={{ animationDelay: "150ms" }}
        />
        <span
          className="h-2 w-2 animate-pulse rounded-full bg-[var(--primary)]"
          style={{ animationDelay: "300ms" }}
        />
      </div>
    </div>
  );
}
