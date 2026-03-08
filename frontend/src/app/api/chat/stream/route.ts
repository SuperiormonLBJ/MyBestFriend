import { NextRequest } from "next/server";
import { BACKEND_URL } from "@/lib/backend";

const LOG_TAG = "[chat/stream]";

export async function POST(request: NextRequest) {
  console.log(LOG_TAG, "request start");
  try {
    const { message, history } = await request.json();

    if (!message || typeof message !== "string") {
      console.warn(LOG_TAG, "bad request: message required");
      return new Response(JSON.stringify({ error: "Message is required" }), { status: 400 });
    }

    const url = `${BACKEND_URL}/api/chat/stream`;
    const fromEnv = !!(process.env.NEXT_PUBLIC_BACKEND_URL ?? process.env.BACKEND_URL);
    console.log(LOG_TAG, "fetching backend", { fromEnv, url: url.replace(/^https?:\/\/[^/]+/, "***"), messageLen: message.length });

    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history: history || [] }),
    });

    const contentType = res.headers.get("content-type") ?? "";
    if (!res.ok) {
      const err = await res.text();
      console.error(LOG_TAG, "backend error", { status: res.status, body: err.slice(0, 200) });
      return new Response(JSON.stringify({ error: "Backend unavailable" }), { status: 502 });
    }

    if (!contentType.includes("text/event-stream") && !contentType.includes("application/stream")) {
      const body = await res.text();
      console.error(LOG_TAG, "backend did not return stream", { contentType, body: body.slice(0, 300) });
      return new Response(JSON.stringify({ error: "Backend unavailable" }), { status: 502 });
    }

    console.log(LOG_TAG, "streaming response");
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
