import { NextResponse } from "next/server";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  process.env.BACKEND_URL ||
  "http://127.0.0.1:8000";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ jobId: string }> }
) {
  const { jobId } = await params;
  try {
    const res = await fetch(`${BACKEND_URL}/api/evaluate/${jobId}`, {
      cache: "no-store",
    });
    if (!res.ok) {
      const err = await res.text();
      return NextResponse.json({ error: err }, { status: res.status });
    }
    return NextResponse.json(await res.json());
  } catch (err) {
    console.error("Evaluate poll error:", err);
    return NextResponse.json({ error: "Failed to poll evaluation" }, { status: 500 });
  }
}
