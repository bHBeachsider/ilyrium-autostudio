-- CreateTable
CREATE TABLE "takes" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "shot_id" TEXT NOT NULL,
    "song_id" TEXT NOT NULL,
    "scene_number" INTEGER NOT NULL,
    "model" TEXT,
    "public_url" TEXT NOT NULL,
    "c2pa_status" TEXT NOT NULL DEFAULT 'missing',
    "hidden" BOOLEAN NOT NULL DEFAULT false,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- CreateTable
CREATE TABLE "audio_elements" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "song_id" TEXT NOT NULL,
    "scene_number" INTEGER,
    "kind" TEXT NOT NULL,
    "voice_id" TEXT,
    "text" TEXT,
    "asset_url" TEXT,
    "ducking_db" REAL NOT NULL DEFAULT -6,
    "cut_id" TEXT,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "audio_elements_cut_id_fkey" FOREIGN KEY ("cut_id") REFERENCES "cuts" ("id") ON DELETE SET NULL ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "cuts" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "song_id" TEXT NOT NULL,
    "version" INTEGER NOT NULL,
    "render_url" TEXT,
    "approved_at" DATETIME,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- CreateTable
CREATE TABLE "_CutToTake" (
    "A" TEXT NOT NULL,
    "B" TEXT NOT NULL,
    CONSTRAINT "_CutToTake_A_fkey" FOREIGN KEY ("A") REFERENCES "cuts" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "_CutToTake_B_fkey" FOREIGN KEY ("B") REFERENCES "takes" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateIndex
CREATE INDEX "takes_song_id_shot_id_idx" ON "takes"("song_id", "shot_id");

-- CreateIndex
CREATE INDEX "audio_elements_song_id_idx" ON "audio_elements"("song_id");

-- CreateIndex
CREATE UNIQUE INDEX "cuts_song_id_version_key" ON "cuts"("song_id", "version");

-- CreateIndex
CREATE UNIQUE INDEX "_CutToTake_AB_unique" ON "_CutToTake"("A", "B");

-- CreateIndex
CREATE INDEX "_CutToTake_B_index" ON "_CutToTake"("B");
