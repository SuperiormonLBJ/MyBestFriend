import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  process.env.BACKEND_URL ||
  "http://127.0.0.1:8000";

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
