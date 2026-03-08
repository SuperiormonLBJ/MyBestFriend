import { NextRequest } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || process.env.BACKEND_URL || "http://127.0.0.1:8000";

export async function POST(request: NextRequest) {
  try {
    const { message, history } = await request.json();

    if (!message || typeof message !== "string") {
      return new Response(JSON.stringify({ error: "Message is required" }), { status: 400 });
    }

    const res = await fetch(`${BACKEND_URL}/api/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history: history || [] }),
    });

    if (!res.ok) {
      const err = await res.text();
      console.error("Backend stream error:", err);
      return new Response(JSON.stringify({ error: "Backend unavailable" }), { status: 502 });
    }

    return new Response(res.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
      },
    });
  } catch (err) {
    console.error("Chat stream API error:", err);
    return new Response(JSON.stringify({ error: "Internal error" }), { status: 500 });
  }
}
