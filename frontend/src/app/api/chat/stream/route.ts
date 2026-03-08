import { NextRequest } from "next/server";
import { BACKEND_URL } from "@/lib/backend";

const LOG_TAG = "[chat/stream]";

export async function POST(request: NextRequest) {
  try {
    const { message, history } = await request.json();

    if (!message || typeof message !== "string") {
      console.warn(LOG_TAG, "bad request: message required");
      return new Response(JSON.stringify({ error: "Message is required" }), { status: 400 });
    }

    const url = `${BACKEND_URL}/api/chat/stream`;
    console.log(LOG_TAG, "fetching backend", { url: url.replace(/^https?:\/\/[^/]+/, "***"), messageLen: message.length });

    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history: history || [] }),
    });

    if (!res.ok) {
      const err = await res.text();
      console.error(LOG_TAG, "backend error", { status: res.status, body: err.slice(0, 200) });
      return new Response(JSON.stringify({ error: "Backend unavailable" }), { status: 502 });
    }

    console.log(LOG_TAG, "streaming response", { ok: res.ok });
    return new Response(res.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
      },
    });
  } catch (err) {
    console.error(LOG_TAG, "exception", err);
    return new Response(JSON.stringify({ error: "Internal error" }), { status: 500 });
  }
}
