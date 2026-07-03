import { generateScript, type ScriptRequest } from "@/lib/generation/script"

export const maxDuration = 60

export async function POST(req: Request) {
  let body: Partial<ScriptRequest>
  try {
    body = await req.json()
  } catch {
    return Response.json({ error: "Invalid request body." }, { status: 400 })
  }

  const topic = body.topic?.trim()
  if (!topic) {
    return Response.json({ error: "A topic or idea title is required." }, { status: 400 })
  }

  try {
    const episode = await generateScript({ ...body, topic })
    return Response.json({ episode })
  } catch (err) {
    console.log("[v0] Episode generation failed:", err instanceof Error ? err.message : err)
    return Response.json({ error: "Failed to generate the episode script. Please try again." }, { status: 500 })
  }
}
