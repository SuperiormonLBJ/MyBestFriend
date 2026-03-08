"use client";

import { useState, useRef, useEffect } from "react";
import { SquarePen } from "lucide-react";
import { ChatInput } from "@/components/chat-input";
import { ChatMessageBubble, type ChatMessage } from "@/components/chat-message";
import { TypingIndicator } from "@/components/typing-indicator";
import { useConfig } from "@/components/config-provider";

const HISTORY_KEY = "chat_history";

type ContactState = "idle" | "open" | "sending" | "sent" | "error";

export default function ChatPage() {
  const { config } = useConfig();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Contact form state
  const [pendingQuestion, setPendingQuestion] = useState("");
  const [contactState, setContactState] = useState<ContactState>("idle");
  const [contactName, setContactName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactError, setContactError] = useState("");

  // Load history from localStorage on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem(HISTORY_KEY);
      if (saved) setMessages(JSON.parse(saved));
    } catch {}
    setHistoryLoaded(true);
  }, []);

  // Persist history to localStorage whenever messages change
  useEffect(() => {
    if (!historyLoaded) return;
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(messages));
    } catch {}
  }, [messages, historyLoaded]);

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
      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: content, history }),
      });

      if (!res.ok) throw new Error("Failed to get response");

      const assistantId = crypto.randomUUID();
      let accumulated = "";
      let firstToken = true;
      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done: readerDone, value } = await reader.read();
        if (readerDone) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          if (!part.startsWith("data: ")) continue;
          const event = JSON.parse(part.slice(6));

          if (event.done) {
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...m, content: event.final } : m))
            );
            setStreaming(false);
            if (event.no_info) {
              setPendingQuestion(content);
              setContactState("open");
            }
          } else if (event.token) {
            if (firstToken) {
              firstToken = false;
              accumulated = event.token;
              setMessages((prev) => [...prev, { id: assistantId, role: "assistant", content: accumulated }]);
              setLoading(false);
              setStreaming(true);
            } else {
              accumulated += event.token;
              setMessages((prev) =>
                prev.map((m) => (m.id === assistantId ? { ...m, content: accumulated } : m))
              );
            }
          }
        }
      }
    } catch {
      const errorMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "Sorry, I couldn't connect to the backend. Please make sure the API is running.",
      };
      setMessages((prev) => [...prev, errorMessage]);
      setStreaming(false);
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

  const handleNewChat = () => {
    try { localStorage.removeItem(HISTORY_KEY); } catch {}
    setMessages([]);
    setContactState("idle");
    setPendingQuestion("");
    setContactName("");
    setContactEmail("");
    setContactError("");
  };

  const ownerName = config.owner_name || "Beiji";

  return (
    <div className="flex h-full flex-1 flex-col">
      <header className="shrink-0 border-b-2 border-[var(--border)] bg-[var(--primary)] px-6 py-4 header-texture flex items-center justify-between gap-4">
        <div>
          <h2 className="font-heading text-3xl text-[#000000] uppercase tracking-wide glitch-title">
            DIGITAL TWIN
          </h2>
          <p className="mt-1 font-body text-base font-bold text-[#000000]/75 uppercase tracking-widest blinking-cursor">
            Ask anything about <span className="underline">{ownerName}</span> — career, projects, hobbies, or daily life
          </p>
        </div>
        <button
          type="button"
          onClick={handleNewChat}
          aria-label="New chat"
          title="New chat"
          className="flex shrink-0 items-center gap-2 border-2 border-[#000000] px-3 py-2 font-heading text-sm uppercase tracking-wide text-[#000000] transition-colors duration-150 hover:bg-[#000000] hover:text-[var(--primary)] cursor-pointer"
          style={{ boxShadow: "3px 3px 0 rgba(0,0,0,0.35)" }}
        >
          <SquarePen className="h-4 w-4 shrink-0" strokeWidth={2.5} />
          New Chat
        </button>
      </header>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-6 py-4"
        role="log"
        aria-live="polite"
      >
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
            <div className="border-2 border-[var(--border)] px-8 py-6" style={{ boxShadow: "5px 5px 0 var(--border)" }}>
              <p className="font-body text-base font-semibold text-[var(--foreground-muted)] uppercase tracking-wide">
                Type a question or use the microphone for voice input
              </p>
              <p className="mt-2 font-body text-sm text-[var(--foreground-muted)]/70">
                Try: &ldquo;What is {ownerName}&rsquo;s job experience in Singapore?&rdquo; or &ldquo;Tell me about their hobbies&rdquo;
              </p>
            </div>
          </div>
        )}
        <div className="mx-auto flex max-w-3xl flex-col gap-6">
          {messages.map((m) => (
            <ChatMessageBubble key={m.id} message={m} />
          ))}
          {loading && <TypingIndicator />}

          {/* Contact form — shown when the bot couldn't find the answer */}
          {contactState !== "idle" && (
            <div
              className="border-2 border-[var(--border)] bg-[var(--surface)] p-5"
              style={{ boxShadow: "5px 5px 0 var(--border)" }}
            >
              {contactState === "sent" ? (
                <p className="font-body text-sm font-semibold text-[var(--foreground)] uppercase tracking-wide">
                  Your question has been sent! You&apos;ll hear back soon.
                </p>
              ) : contactState === "error" ? (
                <p className="font-body text-sm font-semibold text-[var(--secondary)] uppercase tracking-wide">
                  Failed to send. Please try again or reach out directly.
                </p>
              ) : (
                <>
                  <p className="mb-4 font-body text-sm font-semibold text-[var(--foreground-muted)] uppercase tracking-wide">
                    I don&apos;t have that information yet. Leave your details and I&apos;ll pass your question along.
                  </p>
                  <form onSubmit={handleContactSubmit} className="flex flex-col gap-3">
                    <input
                      type="text"
                      placeholder="Your name"
                      value={contactName}
                      onChange={(e) => setContactName(e.target.value)}
                      disabled={contactState === "sending"}
                      className="border-2 border-[var(--border)] bg-[var(--background)] px-3 py-2 font-body text-sm text-[var(--foreground)] placeholder:text-[var(--foreground-muted)] focus:outline-none focus:border-[var(--primary)] disabled:opacity-50"
                    />
                    <input
                      type="email"
                      placeholder="Your email"
                      value={contactEmail}
                      onChange={(e) => setContactEmail(e.target.value)}
                      disabled={contactState === "sending"}
                      className="border-2 border-[var(--border)] bg-[var(--background)] px-3 py-2 font-body text-sm text-[var(--foreground)] placeholder:text-[var(--foreground-muted)] focus:outline-none focus:border-[var(--primary)] disabled:opacity-50"
                    />
                    {contactError && (
                      <p className="font-body text-xs font-semibold text-[var(--secondary)] uppercase">{contactError}</p>
                    )}
                    <div className="flex gap-2">
                      <button
                        type="submit"
                        disabled={contactState === "sending"}
                        className="border-2 border-[var(--border)] bg-[var(--primary)] px-4 py-2 font-body text-sm font-bold uppercase tracking-wide text-[#000000] transition-colors hover:bg-[var(--primary-hover)] disabled:opacity-50 cursor-pointer"
                      >
                        {contactState === "sending" ? "Sending…" : "Send question"}
                      </button>
                      <button
                        type="button"
                        onClick={() => setContactState("idle")}
                        disabled={contactState === "sending"}
                        className="border-2 border-[var(--border)] bg-transparent px-4 py-2 font-body text-sm font-bold uppercase tracking-wide text-[var(--foreground-muted)] transition-colors hover:bg-[var(--background-elevated)] hover:text-[var(--foreground)] disabled:opacity-50 cursor-pointer"
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

      <div className="shrink-0 border-t-2 border-[var(--border)] bg-[var(--background)] p-4">
        <div className="mx-auto max-w-3xl">
          <ChatInput
            onSend={handleSend}
            disabled={loading || streaming}
            placeholder={`Ask anything about ${ownerName}…`}
          />
        </div>
      </div>
    </div>
  );
}
