import { NextResponse } from "next/server";
import {
  getBackendNoStore,
  nextJsonFromBackend,
} from "@/lib/proxy-backend-json";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ jobId: string }> },
) {
  const { jobId } = await params;
  try {
    const res = await getBackendNoStore(`/api/evaluate/${jobId}`);
    return nextJsonFromBackend(res);
  } catch (err) {
    console.error("Evaluate poll error:", err);
    return NextResponse.json(
      { error: "Failed to poll evaluation" },
      { status: 500 },
    );
  }
}
