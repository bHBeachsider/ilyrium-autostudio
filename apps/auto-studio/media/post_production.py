import os
# moviepy 2.x API: editor module removed; effects are classes in the vfx namespace.
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips, vfx, CompositeAudioClip
from moviepy.audio.fx.AudioLoop import AudioLoop

# How far to duck the clip's native audio (ambient/SFX/dialogue the video model
# generated) under the narrator voiceover. 0.0 = silent, 1.0 = full volume.
CLIP_AUDIO_DUCK = 0.35

def _extend_to(video_clip, target_duration, mode):
    """Extend a clip to `target_duration` when its audio is longer than its video.
    mode='loop' repeats the clip from the start (can look like a re-take/re-entry);
    mode='freeze' holds the final frame (natural for a character finishing a line);
    mode='trim' leaves the video as-is (audio simply overhangs)."""
    if mode == "trim":
        return video_clip
    if mode == "freeze":
        from moviepy import concatenate_videoclips
        extra = target_duration - video_clip.duration
        last = video_clip.to_ImageClip(t=max(0.0, video_clip.duration - 0.05)).with_duration(extra)
        return concatenate_videoclips([video_clip, last])
    # default: loop
    return video_clip.with_effects([vfx.Loop(duration=target_duration)])


def compile_final_video(media_list: list, output_filename="final_commercial.mp4", duck: float = None,
                        music_path: str = None, music_gain: float = 0.15,
                        extend_mode: str = "loop") -> str:
    """
    Bulletproof compiler: safely handles missing files and extends video if audio is longer.
    `duck` (0.0-1.0) sets how loud the clip's native audio sits under the narrator;
    defaults to CLIP_AUDIO_DUCK when not provided.
    `extend_mode` ('loop'|'freeze'|'trim') controls how a clip is stretched when its
    audio outlasts its video; default 'loop' preserves prior behavior.
    """
    duck_level = CLIP_AUDIO_DUCK if duck is None else max(0.0, min(1.0, duck))
    print("\n🎬 [POST-PRODUCTION] Stitching scenes and audio together...")
    clips = []
    
    try:
        for item in media_list:
            # 1. Skip entirely if the video track failed to generate
            if not item.get("video") or not os.path.exists(item["video"]):
                print(f"⚠️ [POST-PRODUCTION] Skipping Scene {item.get('scene_number', 'Unknown')}: Missing video file.")
                continue
                
            try:
                video_clip = VideoFileClip(item["video"])
            except Exception as e:
                print(f"⚠️ [POST-PRODUCTION] Corrupted video file for Scene {item.get('scene_number')}: {e}")
                continue
            
            # 2. Handle the Audio Track Safely
            if item.get("audio") and os.path.exists(item["audio"]):
                try:
                    audio_clip = AudioFileClip(item["audio"])

                    # If voiceover is longer than the video, extend the video to match.
                    extended = False
                    if audio_clip.duration > video_clip.duration:
                        print(f"🔄 Scene {item['scene_number']} video shorter than audio. Extending ({extend_mode})...")
                        video_clip = _extend_to(video_clip, audio_clip.duration, extend_mode)
                        extended = True

                    # Mix the narrator OVER the clip's native audio (ambient / SFX /
                    # dialogue the video model generated), ducked under the voiceover.
                    # BUT: when the clip was looped/extended to match a longer
                    # voiceover, its native audio is looped too, and moviepy's audio
                    # reader raises "index 0 is out of bounds for axis 0 with size 0"
                    # reading past the end of that stretched track during write. On
                    # extended clips, drop the native audio and use only the
                    # voiceover — the mp3 is the intended audio anyway.
                    native = None if extended else video_clip.audio
                    if native is not None:
                        try:
                            ducked = native.with_volume_scaled(duck_level)
                            mixed = CompositeAudioClip([ducked, audio_clip])
                        except Exception:
                            mixed = audio_clip  # native-audio compose failed; voiceover only
                    else:
                        mixed = audio_clip
                    scene_with_audio = video_clip.with_audio(mixed)
                    clips.append(scene_with_audio)
                except Exception as e:
                    print(f"⚠️ [POST-PRODUCTION] Audio compilation failed for Scene {item.get('scene_number')}, using silent video. Error: {e}")
                    clips.append(video_clip)
            else:
                print(f"⚠️ [POST-PRODUCTION] No audio for Scene {item.get('scene_number')}. Using silent video.")
                clips.append(video_clip)
            
        # 3. Final Concatenation
        if not clips:
            print("❌ [POST-PRODUCTION] No valid scenes to compile!")
            return None
            
        print("⏳ Compiling final timeline... (This may take a minute)")
        final_video = concatenate_videoclips(clips, method="compose")

        # Optional music bed under the whole commercial (looped/trimmed to length, ducked low).
        if music_path and os.path.exists(music_path):
            try:
                bed = AudioFileClip(music_path).with_volume_scaled(music_gain)
                if bed.duration < final_video.duration:
                    bed = bed.with_effects([AudioLoop(duration=final_video.duration)])
                else:
                    bed = bed.with_duration(final_video.duration)
                base = final_video.audio
                final_video = final_video.with_audio(
                    CompositeAudioClip([base, bed]) if base is not None else bed
                )
                print(f"🎵 [POST-PRODUCTION] Music bed mixed at gain {music_gain}.")
            except Exception as e:
                print(f"⚠️ [POST-PRODUCTION] Music bed failed: {e}")

        final_video.write_videofile(
            output_filename, 
            fps=24, 
            codec="libx264", 
            audio_codec="aac",
            logger=None 
        )
        
        # Cleanup memory
        for clip in clips:
            clip.close()
        final_video.close()
            
        print(f"✅ [POST-PRODUCTION] Master video saved as {output_filename}!")
        return output_filename
        
    except Exception as e:
        print(f"❌ [POST-PRODUCTION] Compiler crashed: {e}")
        return None