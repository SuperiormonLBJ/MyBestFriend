import { NextRequest, NextResponse } from "next/server";
import { adminKeyFromRequest } from "@/lib/admin";
import { getBackendNoStore, putBackendJsonAdmin } from "@/lib/proxy-backend-json";

export async function GET() {
  try {
    const res = await getBackendNoStore("/api/config");

    if (!res.ok) {
      const err = await res.text();
      console.error("Config fetch error:", err);
      return NextResponse.json(getDefaultConfig(), { status: 200 });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    console.error("Config API error:", err);
    return NextResponse.json(getDefaultConfig(), { status: 200 });
  }
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();
    const res = await putBackendJsonAdmin(
      "/api/config",
      body,
      adminKeyFromRequest(request),
    );

    if (!res.ok) {
      const err = await res.text();
      console.error("Config update error:", err);
      return NextResponse.json(
        { error: err || "Failed to update config" },
        { status: res.status },
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    console.error("Config update API error:", err);
    return NextResponse.json(
      { error: "Failed to update config" },
      { status: 500 },
    );
  }
}

function getDefaultConfig() {
  return {
    app_name: "MyBestFriend",
    owner_name: "Beiji",
    embedding_model: "text-embedding-3-large",
    generator_model: "gpt-4o-mini",
    llm_model: "gpt-4o-mini",
    evaluator_model: "gpt-4o-mini",
  };
}
