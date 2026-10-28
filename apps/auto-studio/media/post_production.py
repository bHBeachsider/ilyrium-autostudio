import os
# moviepy 2.x API: editor module removed; effects are classes in the vfx namespace.
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips, vfx, CompositeAudioClip
from moviepy.audio.fx.AudioLoop import AudioLoop

# How far to duck the clip's native audio (ambient/SFX/dialogue the video model
# generated) under the narrator voiceover. 0.0 = silent, 1.0 = full volume.
CLIP_AUDIO_DUCK = 0.35


def _build_scene_audio(item: dict, video_clip, duck_level: float):
    """Return an AudioClip for a single scene.

    If the scene's ``audio_elements`` list is populated, mixes those tracks via
    AudioMixer (multi-track path). Otherwise falls back to the existing single-
    narrator path so prior behaviour is preserved exactly.
    """
    audio_elements = item.get("audio_elements") or []
    # Multi-track path: requires at least one element with a valid url
    valid_tracks = [t for t in audio_elements if isinstance(t, dict) and t.get("url") and os.path.exists(t["url"])]
    if valid_tracks:
        try:
            from media.audio_mixer import AudioMixer, AudioTrack
            tracks = [AudioTrack.from_dict(t) for t in valid_tracks]
            out_dir = os.path.dirname(item.get("video") or "") or "."
            out_path = os.path.join(out_dir, f"scene_{item.get('scene_number', 0)}_mix.aac")
            mixer = AudioMixer()
            mixer.mix(tracks, video_clip.duration, out_path)
            return AudioFileClip(out_path)
        except Exception as e:
            print(f"[post_production] multi-track mix failed for scene {item.get('scene_number')}, "
                  f"falling back to narrator-only: {e}")

    # --- Narrator-only (legacy) path ---
    narrator_path = item.get("audio")
    if not narrator_path or not os.path.exists(narrator_path):
        return None

    audio_clip = AudioFileClip(narrator_path)
    native = video_clip.audio
    if native is not None:
        try:
            ducked = native.with_volume_scaled(duck_level)
            return CompositeAudioClip([ducked, audio_clip])
        except Exception:
            pass
    return audio_clip

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
            # Multi-track path (audio_elements) takes priority; narrator-only is the fallback.
            has_audio = bool(
                (item.get("audio_elements") or [])
                or (item.get("audio") and os.path.exists(item.get("audio", "")))
            )
            if has_audio:
                try:
                    # Extend video if the narrator audio is longer (legacy path only).
                    narrator_path = item.get("audio")
                    if narrator_path and os.path.exists(narrator_path) and not item.get("audio_elements"):
                        audio_len = AudioFileClip(narrator_path).duration
                        if audio_len > video_clip.duration:
                            print(f"🔄 Scene {item['scene_number']} video shorter than audio. Extending ({extend_mode})...")
                            video_clip = _extend_to(video_clip, audio_len, extend_mode)
                            # After extension drop the native audio to avoid moviepy loop bug.
                            item = dict(item)   # shallow copy so we don't mutate caller's dict
                            item["_extended"] = True

                    # When extended, suppress native audio in the mixer (avoid loop-read bug).
                    if item.get("_extended"):
                        item = dict(item)
                        item.pop("audio_elements", None)  # multi-track skipped on extended clips

                    mixed = _build_scene_audio(item, video_clip, duck_level)
                    if mixed is not None:
                        scene_with_audio = video_clip.with_audio(mixed)
                    else:
                        scene_with_audio = video_clip
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