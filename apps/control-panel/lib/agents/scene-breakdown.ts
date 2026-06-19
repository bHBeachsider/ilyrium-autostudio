import Anthropic from "@anthropic-ai/sdk";
import { z } from "zod";

// 1. Define the exact shape of the data we need for the render queue
export const SceneManifestSchema = z.object({
  scenes: z.array(
    z.object({
      scene_number: z.number(),
      // Translated for the machine: highly technical, physical descriptions only
      technical_visual_prompt: z.string().describe("E.g., 'Cinematic wide shot, 35mm lens, neon lighting, a woman walking down a rainy street'"),
      // Stripped of all stage directions, just the raw dialogue
      clean_voiceover: z.string(),
      // Helps the orchestrator know if it needs to loop video or trim it
      estimated_duration_seconds: z.number()
    })
  )
});

const client = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

// 2. The Breakout Function
export async function generateProductionManifest(approvedScript: string, brandGuidelines: string) {
  
  const systemPrompt = `
  You are the Technical Director for a video production pipeline. 
  Your job is to take a polished script and break it down into a strict rendering manifest for downstream AI media generators.
  
  RULES:
  1. visual_prompt MUST be translated into technical camera/lighting language. Remove all metaphors.
  2. visual_prompt MUST maintain visual continuity. If the protagonist is "blonde in a red jacket" in scene 1, you must repeat that exact description in scene 2's prompt. 
  3. clean_voiceover MUST contain ONLY the spoken words. Remove all brackets, character names, or emotional direction.
  4. Output your response ONLY as a JSON object matching the requested schema.
  `;

  try {
    const response = await client.messages.create({
      model: "claude-3-5-sonnet-20240620",
      max_tokens: 4000,
      system: systemPrompt,
      messages: [
        {
          role: "user",
          content: `Brand Context: ${brandGuidelines}\n\nApproved Script:\n${approvedScript}`,
        },
      ],
    });

    // Parse and validate the JSON output
    const rawContent = response.content[0].type === 'text' ? response.content[0].text : "";
    const parsedJson = JSON.parse(rawContent);
    
    // Zod throws an error if Claude hallucinated the schema, acting as our safety net
    const validatedManifest = SceneManifestSchema.parse(parsedJson);
    
    return validatedManifest;

  } catch (error) {
    console.error("Failed to generate production manifest:", error);
    throw new Error("Production breakdown failed. Check schema validation.");
  }
}