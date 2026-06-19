import { NextResponse } from "next/server";
// CHANGED: We are explicitly walking back up the folder tree to find the lib folder
import prisma from "../../../lib/db"; 

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { title, scenes } = body;

    if (!title || !scenes || !Array.isArray(scenes)) {
      return NextResponse.json({ error: "Invalid payload format." }, { status: 400 });
    }

    const campaign = await prisma.campaign.create({
      data: {
        title: title,
        status: "DRAFT", 
        scenes: {
          create: scenes.map((scene: any) => ({
            sceneNumber: scene.scene_number,
            visualPrompt: scene.technical_visual_prompt,
            cleanVoiceover: scene.clean_voiceover,
          }))
        }
      },
      include: {
        scenes: true 
      }
    });

    console.log(`✅ Incoming Script Received! Campaign Saved to Neon: ${campaign.id}`);

    return NextResponse.json({ 
      message: "Campaign successfully imported into Studio OS",
      campaignId: campaign.id,
      sceneCount: campaign.scenes.length
    }, { status: 201 });

  } catch (error) {
    console.error("Failed to create campaign:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}