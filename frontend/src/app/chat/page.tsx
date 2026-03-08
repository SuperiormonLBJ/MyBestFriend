"use client";

import { useState, useRef, useEffect } from "react";
import { ChatInput } from "@/components/chat-input";
import { ChatMessageBubble, type ChatMessage } from "@/components/chat-message";
import { TypingIndicator } from "@/components/typing-indicator";
import { useConfig } from "@/components/config-provider";

async function fetchAnswer(message: string, history: { role: string; content: string }[]) {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  });
  if (!res.ok) throw new Error("Failed to get response");
  const data = await res.json();
  return { answer: data.answer as string, no_info: data.no_info as boolean };
}

type ContactState = "idle" | "open" | "sending" | "sent" | "error";

export default function ChatPage() {
  const { config } = useConfig();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Contact form state
  const [pendingQuestion, setPendingQuestion] = useState("");
  const [contactState, setContactState] = useState<ContactState>("idle");
  const [contactName, setContactName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactError, setContactError] = useState("");

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading, contactState]);

  const handleSend = async (content: string) => {
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content,
    };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);
    setContactState("idle");
    setPendingQuestion("");

    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const { answer, no_info } = await fetchAnswer(content, history);

      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: answer,
      };
      setMessages((prev) => [...prev, assistantMessage]);

      if (no_info) {
        setPendingQuestion(content);
        setContactState("open");
      }
    } catch {
      const errorMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "Sorry, I couldn't connect to the backend. Please make sure the API is running.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleContactSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!contactName.trim() || !contactEmail.trim()) {
      setContactError("Please fill in both your name and email.");
      return;
    }
    setContactError("");
    setContactState("sending");
    try {
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          requester_name: contactName.trim(),
          requester_email: contactEmail.trim(),
          question: pendingQuestion,
        }),
      });
      if (!res.ok) throw new Error("send failed");
      setContactState("sent");
      setContactName("");
      setContactEmail("");
    } catch {
      setContactState("error");
    }
  };

  return (
    <div className="flex min-h-full flex-1 flex-col">
      <header className="shrink-0 border-b border-[var(--border)] px-6 py-4">
        <h2 className="font-heading text-xl font-bold tracking-wider text-[var(--primary)]">
          {config.chat_title.toUpperCase()}
        </h2>
        <p className="mt-1 text-sm text-[var(--foreground-muted)] font-body">
          {config.chat_subtitle}
        </p>
      </header>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-6 py-4"
        role="log"
        aria-live="polite"
      >
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
            <p className="text-[var(--foreground-muted)] font-body">
              {config.empty_state_hint}
            </p>
            <p className="text-sm text-[var(--foreground-muted)]/80 font-body">
              {config.empty_state_examples}
            </p>
          </div>
        )}
        <div className="mx-auto flex max-w-3xl flex-col gap-6">
          {messages.map((m) => (
            <ChatMessageBubble key={m.id} message={m} />
          ))}
          {loading && <TypingIndicator />}

          {/* Contact form — shown when the bot couldn't find the answer */}
          {contactState !== "idle" && (
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 shadow-sm">
              {contactState === "sent" ? (
                <p className="text-sm text-[var(--foreground-muted)]">
                  ✅ Your question has been sent! You&apos;ll hear back soon.
                </p>
              ) : contactState === "error" ? (
                <p className="text-sm text-red-500">
                  Failed to send. Please try again or reach out directly.
                </p>
              ) : (
                <>
                  <p className="mb-4 text-sm text-[var(--foreground-muted)]">
                    I don&apos;t have that information yet. Leave your details and I&apos;ll pass your question along.
                  </p>
                  <form onSubmit={handleContactSubmit} className="flex flex-col gap-3">
                    <input
                      type="text"
                      placeholder="Your name"
                      value={contactName}
                      onChange={(e) => setContactName(e.target.value)}
                      disabled={contactState === "sending"}
                      className="rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--foreground-muted)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)] disabled:opacity-50"
                    />
                    <input
                      type="email"
                      placeholder="Your email"
                      value={contactEmail}
                      onChange={(e) => setContactEmail(e.target.value)}
                      disabled={contactState === "sending"}
                      className="rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--foreground-muted)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)] disabled:opacity-50"
                    />
                    {contactError && (
                      <p className="text-xs text-red-500">{contactError}</p>
                    )}
                    <div className="flex gap-2">
                      <button
                        type="submit"
                        disabled={contactState === "sending"}
                        className="rounded-lg bg-[var(--primary)] px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                      >
                        {contactState === "sending" ? "Sending…" : "Send question"}
                      </button>
                      <button
                        type="button"
                        onClick={() => setContactState("idle")}
                        disabled={contactState === "sending"}
                        className="rounded-lg border border-[var(--border)] px-4 py-2 text-sm text-[var(--foreground-muted)] transition-colors hover:bg-[var(--border)] disabled:opacity-50"
                      >
                        Dismiss
                      </button>
                    </div>
                  </form>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="shrink-0 border-t border-[var(--border)] bg-[var(--background)] p-4">
        <div className="mx-auto max-w-3xl">
          <ChatInput
            onSend={handleSend}
            disabled={loading}
            placeholder={config.input_placeholder}
          />
        </div>
      </div>
    </div>
  );
}
