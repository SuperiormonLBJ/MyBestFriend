import { NextRequest } from "next/server";
import { BACKEND_URL } from "@/lib/backend";

export async function GET(_req: NextRequest) {
  const res = await fetch(`${BACKEND_URL}/api/eval/dataset/download`, {
    cache: "no-store",
  });
  const text = await res.text();
  return new Response(text, {
    status: res.status,
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Content-Disposition": 'attachment; filename="eval_data.jsonl"',
    },
  });
}

