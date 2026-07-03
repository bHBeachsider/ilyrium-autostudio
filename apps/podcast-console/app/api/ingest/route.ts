import { NextResponse } from "next/server"

export const runtime = "nodejs"

type IngestedItem = {
  title: string
  summary: string
  angle: string
  source?: string
}

// The Media Ingestion Spine: uses Perplexity to discover fresh, sourced
// content that can be pulled into the podcast production pipeline.
export async function POST(request: Request) {
  const apiKey = process.env.PERPLEXITY_API_KEY
  if (!apiKey) {
    return NextResponse.json(
      { error: "PERPLEXITY_API_KEY is not configured." },
      { status: 500 },
    )
  }

  let topic = ""
  try {
    const body = await request.json()
    topic = (body?.topic ?? "").toString().trim()
  } catch {
    return NextResponse.json({ error: "Invalid request body." }, { status: 400 })
  }

  if (!topic) {
    return NextResponse.json({ error: "A topic is required." }, { status: 400 })
  }

  const systemPrompt = [
    "You are the ingestion engine for 'Palm Beach County Weekly', a local news podcast.",
    "Given a topic, surface 4 distinct, recent, newsworthy story angles suitable for podcast segments.",
    "Prefer Palm Beach County / South Florida relevance when the topic allows.",
    "Respond ONLY with strict JSON of the shape:",
    '{"items":[{"title":string,"summary":string,"angle":string,"source":string}]}',
    "title: a punchy segment title. summary: 1-2 sentences. angle: why it matters to local listeners. source: a publication or outlet name.",
  ].join(" ")

  try {
    const res = await fetch("https://api.perplexity.ai/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "sonar",
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: `Topic to ingest: ${topic}` },
        ],
        temperature: 0.2,
      }),
    })

    if (!res.ok) {
      const detail = await res.text()
      return NextResponse.json(
        { error: `Perplexity request failed (${res.status}).`, detail },
        { status: 502 },
      )
    }

    const data = await res.json()
    const content: string = data?.choices?.[0]?.message?.content ?? ""

    let items: IngestedItem[] = []
    try {
      const jsonStart = content.indexOf("{")
      const jsonEnd = content.lastIndexOf("}")
      const parsed = JSON.parse(content.slice(jsonStart, jsonEnd + 1))
      items = Array.isArray(parsed?.items) ? parsed.items.slice(0, 6) : []
    } catch {
      return NextResponse.json(
        { error: "Could not parse ingestion results.", raw: content },
        { status: 502 },
      )
    }

    const citations: string[] = Array.isArray(data?.citations) ? data.citations : []

    return NextResponse.json({ items, citations })
  } catch (error) {
    return NextResponse.json(
      { error: "Ingestion failed.", detail: String(error) },
      { status: 500 },
    )
  }
}
