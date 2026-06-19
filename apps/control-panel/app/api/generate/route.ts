// apps/control-panel/app/api/generate/route.ts
import { NextResponse } from "next/server";
import { executeGeneration } from "../../../lib/adapter-bus";
import { GenerateRequest } from "../../../lib/adapters/types";

export async function POST(request: Request) {
  try {
    const body: GenerateRequest = await request.json();

    // Basic validation
    if (!body.media || !body.prompt || !body.project) {
      return NextResponse.json({ error: "Missing required fields (media, prompt, project)" }, { status: 400 });
    }

    // Hand off to the spine
    const response = await executeGeneration(body);

    if (!response.ok) {
      return NextResponse.json(response, { status: 502 }); // Bad Gateway / Upstream failure
    }

    return NextResponse.json(response, { status: 200 });

  } catch (error) {
    console.error("Spine execution error:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}