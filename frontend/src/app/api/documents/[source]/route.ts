import { NextRequest, NextResponse } from "next/server";
import { BACKEND_URL } from "@/lib/backend";

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ source: string }> }
) {
  try {
    const { source } = await params;
    const decoded = decodeURIComponent(source);
    const { searchParams } = new URL(request.url);
    const docType = searchParams.get("doc_type") || undefined;
    const url = new URL(`${BACKEND_URL}/api/documents/${encodeURIComponent(decoded)}`);
    if (docType) url.searchParams.set("doc_type", docType);

    const res = await fetch(url.toString(), { method: "DELETE" });
    const data = await res.json();
    if (!res.ok) {
      return NextResponse.json(data, { status: res.status });
    }
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json(
      { error: String(err) },
      { status: 500 }
    );
  }
}
