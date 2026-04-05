import { backendFetch } from "@/lib/proxy-backend-json";

export async function GET() {
  const res = await backendFetch("/api/eval/dataset/download", {
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
