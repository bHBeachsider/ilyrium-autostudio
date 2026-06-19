import { NextResponse } from "next/server";
import prisma from "@/lib/db";
import { triggerAssembly } from "@/lib/agents/assembly";

export async function POST(request: Request) {
  try {
    const body = await request.json();

    // 1. Extract data from the incoming webhook payload 
    // (This structure depends on your specific video provider, e.g., Runway, Luma)
    const providerJobId = body.id; 
    const finalVideoUrl = body.output.url;
    const status = body.status; // e.g., "SUCCEEDED" or "FAILED"

    if (!providerJobId) {
      return NextResponse.json({ error: "Missing Job ID" }, { status: 400 });
    }

    if (status === "SUCCEEDED") {
      // 2. Find the scene in our database and update it
      const updatedScene = await prisma.scene.updateMany({
        where: { videoProviderId: providerJobId },
        data: { 
          videoStatus: "DONE", 
          videoUrl: finalVideoUrl 
        }
      });

      // 3. Find the parent campaign to check if ALL scenes are finished
      const sceneRecord = await prisma.scene.findFirst({ where: { videoProviderId: providerJobId } });
      
      if (sceneRecord) {
        const campaignId = sceneRecord.campaignId;
        
        // Fetch all scenes for this campaign
        const allScenes = await prisma.scene.findMany({
          where: { campaignId: campaignId }
        });

        // Check if every single scene has both audio and video marked as "DONE"
        const isCampaignReady = allScenes.every(s => s.videoStatus === "DONE" && s.audioStatus === "DONE");

        if (isCampaignReady) {
          // 🚀 FLIGHT 3 TAKEOFF: The movie has all its parts. Time to edit.
          // We trigger this asynchronously so the webhook can respond with a 200 OK immediately
          triggerAssembly(campaignId); 
        }
      }
    } else if (status === "FAILED") {
      await prisma.scene.updateMany({
        where: { videoProviderId: providerJobId },
        data: { videoStatus: "FAILED" }
      });
    }

    return NextResponse.json({ message: "Webhook processed" }, { status: 200 });

  } catch (error) {
    console.error("Webhook processing error:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}