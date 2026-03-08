import { NextResponse } from "next/server";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  process.env.BACKEND_URL ||
  "http://127.0.0.1:8000";

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/evaluate/latest`, {
      cache: "no-store",
    });
    if (!res.ok) {
      return NextResponse.json({ status: "none" });
    }
    return NextResponse.json(await res.json());
  } catch (err) {
    console.error("Evaluate latest error:", err);
    return NextResponse.json({ status: "none" });
  }
}
