import { NextRequest, NextResponse } from "next/server";
import { adminKeyFromRequest } from "@/lib/admin";
import {
  deleteBackendAdmin,
  nextJsonFromBackendResponse,
} from "@/lib/proxy-backend-json";

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ source: string }> },
) {
  try {
    const { source } = await params;
    const decoded = decodeURIComponent(source);
    const { searchParams } = new URL(request.url);
    const docType = searchParams.get("doc_type") || undefined;
    let path = `/api/documents/${encodeURIComponent(decoded)}`;
    if (docType) {
      path += `?doc_type=${encodeURIComponent(docType)}`;
    }
    const res = await deleteBackendAdmin(path, adminKeyFromRequest(request));
    return nextJsonFromBackendResponse(res);
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
