import { generateEpisodeImages } from "@/lib/generation/images"

export const runtime = "nodejs"
export const maxDuration = 300

// Scene planning + Imagen generation (see lib/generation/images.ts). Contract
// unchanged: returns { visualStyle, images: [{caption, dataUrl}], weights }.
export async function POST(req: Request) {
  let body: { title?: string; description?: string; segments?: { speaker: string; text: string }[] }
  try {
    body = await req.json()
  } catch {
    return Response.json({ error: "Invalid request body." }, { status: 400 })
  }

  const title = body.title?.trim()
  const segments = body.segments ?? []
  if (!title || segments.length === 0) {
    return Response.json({ error: "An episode title and segments are required." }, { status: 400 })
  }

  try {
    const result = await generateEpisodeImages({ title, description: body.description, segments })
    return Response.json({
      visualStyle: result.visualStyle,
      images: result.images.map((img) => ({
        caption: img.caption,
        dataUrl: `data:${img.mediaType};base64,${img.bytes.toString("base64")}`,
      })),
      weights: result.weights,
    })
  } catch (err) {
    console.log("[v0] Image generation failed:", err instanceof Error ? err.message : err)
    return Response.json({ error: "Failed to generate scene images." }, { status: 500 })
  }
}
