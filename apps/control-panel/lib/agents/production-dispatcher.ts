import prisma from "@/lib/db"; // Your Prisma client

// Pseudo-imports for your external API wrappers
import { generateElevenLabsAudio } from "@/lib/media/audio"; 
import { submitRunwayVideoJob } from "@/lib/media/video"; 

export async function dispatchProductionQueue(campaignId: string, sceneManifest: any[]) {
  // 1. Mark the campaign as Rendering
  await prisma.campaign.update({
    where: { id: campaignId },
    data: { status: "RENDERING" }
  });

  // 2. Loop through the manifest and dispatch jobs asynchronously
  for (const scene of sceneManifest) {
    
    // First, save the blank scene to our database
    const dbScene = await prisma.scene.create({
      data: {
        campaignId: campaignId,
        sceneNumber: scene.scene_number,
        visualPrompt: scene.technical_visual_prompt,
        cleanVoiceover: scene.clean_voiceover,
      }
    });

    // 3. FIRE AND FORGET: Start the API processes
    // We don't await the final media here; we just trigger the generation
    
    // --> Trigger Audio
    triggerAudioProcessing(dbScene.id, scene.clean_voiceover);
    
    // --> Trigger Video
    triggerVideoProcessing(dbScene.id, scene.technical_visual_prompt);
  }
}

// --- INTERNAL HELPERS ---

async function triggerAudioProcessing(sceneId: string, text: string) {
  try {
    // Audio is usually fast enough to await directly
    const audioUrl = await generateElevenLabsAudio(text);
    
    await prisma.scene.update({
      where: { id: sceneId },
      data: { audioStatus: "DONE", audioUrl: audioUrl }
    });
  } catch (error) {
    await prisma.scene.update({ where: { id: sceneId }, data: { audioStatus: "FAILED" }});
  }
}

async function triggerVideoProcessing(sceneId: string, prompt: string) {
  try {
    // Video takes a long time. The API will return a Job ID, NOT the final video.
    const providerJobId = await submitRunwayVideoJob(prompt);
    
    // Save the Job ID so our system can check on it later
    await prisma.scene.update({
      where: { id: sceneId },
      data: { videoStatus: "PROCESSING", videoProviderId: providerJobId }
    });
  } catch (error) {
    await prisma.scene.update({ where: { id: sceneId }, data: { videoStatus: "FAILED" }});
  }
}