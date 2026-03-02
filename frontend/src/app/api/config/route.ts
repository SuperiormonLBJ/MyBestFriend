import { NextResponse } from "next/server";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  process.env.BACKEND_URL ||
  "http://127.0.0.1:8000";

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/config`, {
      cache: "no-store",
    });

    if (!res.ok) {
      const err = await res.text();
      console.error("Config fetch error:", err);
      return NextResponse.json(getDefaultConfig(), { status: 200 });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    console.error("Config API error:", err);
    return NextResponse.json(getDefaultConfig(), { status: 200 });
  }
}

export async function PUT(request: Request) {
  try {
    const body = await request.json();
    const res = await fetch(`${BACKEND_URL}/api/config`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const err = await res.text();
      console.error("Config update error:", err);
      return NextResponse.json(
        { error: err || "Failed to update config" },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    console.error("Config update API error:", err);
    return NextResponse.json(
      { error: "Failed to update config" },
      { status: 500 }
    );
  }
}

function getDefaultConfig() {
  return {
    app_name: "MyBestFriend",
    chat_title: "Digital Twin",
    chat_subtitle:
      "Ask anything about me — career, projects, hobbies, or daily life",
    input_placeholder: "Ask anything about me...",
    empty_state_hint:
      "Type a question or use the microphone for voice input",
    empty_state_examples:
      'Try: "What is Beiji\'s experience at UOB?" or "Tell me about his hobbies"',
    embedding_model: "text-embedding-3-large",
    generator_model: "gpt-4o-mini",
    llm_model: "gpt-4o-mini",
    evaluator_model: "gpt-4o-mini",
  };
}
