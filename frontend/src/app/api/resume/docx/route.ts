import { NextRequest } from "next/server";
import { BACKEND_URL } from "@/lib/backend";

export async function POST(request: NextRequest) {
  try {
    const body = await request.text();

    const res = await fetch(`${BACKEND_URL}/api/resume/docx`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });

    const contentType =
      res.headers.get("content-type") ??
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
    const disposition =
      res.headers.get("content-disposition") ?? 'attachment; filename="rewritten_resume.docx"';

    return new Response(res.body, {
      status: res.status,
      headers: {
        "content-type": contentType,
        "content-disposition": disposition,
      },
    });
  } catch (err) {
    console.error("Resume DOCX API error:", err);
    return new Response(JSON.stringify({ error: "Internal error" }), {
      status: 500,
      headers: { "content-type": "application/json" },
    });
  }
}

