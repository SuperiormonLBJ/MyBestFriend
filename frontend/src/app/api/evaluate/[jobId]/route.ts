import { NextResponse } from "next/server";
import { BACKEND_URL } from "@/lib/backend";

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
