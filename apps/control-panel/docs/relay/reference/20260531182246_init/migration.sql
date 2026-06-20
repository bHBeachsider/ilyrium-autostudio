-- CreateTable
CREATE TABLE "Campaign" (
    "id" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'DRAFT',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Campaign_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Scene" (
    "id" TEXT NOT NULL,
    "campaignId" TEXT NOT NULL,
    "sceneNumber" INTEGER NOT NULL,
    "visualPrompt" TEXT NOT NULL,
    "cleanVoiceover" TEXT NOT NULL,
    "audioStatus" TEXT NOT NULL DEFAULT 'PENDING',
    "audioUrl" TEXT,
    "videoStatus" TEXT NOT NULL DEFAULT 'PENDING',
    "videoProviderId" TEXT,
    "videoUrl" TEXT,

    CONSTRAINT "Scene_pkey" PRIMARY KEY ("id")
);

-- AddForeignKey
ALTER TABLE "Scene" ADD CONSTRAINT "Scene_campaignId_fkey" FOREIGN KEY ("campaignId") REFERENCES "Campaign"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
