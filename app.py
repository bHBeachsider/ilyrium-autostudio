import streamlit as st
from google import genai
from google.genai import types
import os
import json

# --- 1. SETUP GOOGLE GENAI CLIENT ---
# In production on Railway, load this via the Variables tab.
API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE")
client = genai.Client(api_key=API_KEY)

# --- 2. DASHBOARD UI LAYOUT ---
st.set_page_config(page_title="Ilyrium Auto-Studio", page_icon="🎬", layout="centered")

st.title("🎬 Ilyrium Auto-Studio")
st.subheader("AI Social Media Content Generator for Local Businesses")
st.write("Turn your upcoming local events, promos, and specials into high-converting 15-second vertical clips.")

st.divider()

# --- 3. THE BRAND KIT ---
st.header("🎯 1. Your Brand Kit")
col1, col2 = st.columns(2)

with col1:
    business_name = st.text_input("Business Name", value="Ilyrium Bar & Grill")
    brand_color = st.color_picker("Primary Brand Color", "#FF4B4B")

with col2:
    brand_vibe = st.selectbox(
        "Content Vibe / Tone", 
        ["High-Energy & Loud", "Cinematic & Premium", "Warm & Community-Focused", "Clean & Modern"]
    )
    video_ratio = st.selectbox("Output Format", ["9:16 (Instagram Reels/TikTok)", "1:1 (Facebook/Instagram Feed)"])

st.divider()

# --- 4. THE PROMO CONFIGURATOR ---
st.header("📝 2. Campaign Details")
promo_prompt = st.text_area(
    "What event or special are we promoting today?", 
    placeholder="e.g., Live Music this Saturday night featuring local blues band 'The Delta Echoes'. Doors open at 7 PM...",
    height=120
)

# --- 5. THE AGENTIC EXECUTION ---
if st.button("🚀 Generate Marketing Campaign Script", use_container_width=True):
    if not promo_prompt:
        st.warning("Please describe your event or offer before generating!")
    elif API_KEY == "YOUR_API_KEY_HERE" and "GEMINI_API_KEY" not in os.environ:
        st.error("Missing Gemini API Key! Please add it to your environment variables.")
    else:
        with st.spinner("Calling The Creative Director to structure your timeline..."):
            
            system_instruction = f"""
            You are an expert B2B social media marketing director. Convert the user's event details into a 15-second script.
            Business: {business_name} | Vibe: {brand_vibe} | Format: {video_ratio}
            
            Rules: Create exactly 3 logical chronological scenes. Scene 1 is a hook. Scene 3 is a CTA.
            You must output ONLY valid JSON using the exact schema requested.
            """
            
            # The schema forces the new SDK to return a guaranteed JSON structure
            response_schema = {
                "type": "OBJECT",
                "properties": {
                    "campaign_hook": {"type": "STRING"},
                    "scenes": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "scene_number": {"type": "INTEGER"},
                                "duration_seconds": {"type": "INTEGER"},
                                "visual_prompt_for_imagen": {"type": "STRING"},
                                "on_screen_caption": {"type": "STRING"},
                                "voiceover_audio_script": {"type": "STRING"}
                            },
                            "required": ["scene_number", "duration_seconds", "visual_prompt_for_imagen", "on_screen_caption", "voiceover_audio_script"]
                        }
                    }
                },
                "required": ["campaign_hook", "scenes"]
            }

            try:
                # Execution using the new google-genai syntax
                response = client.models.generate_content(
                    model='gemini-1.5-pro',
                    contents=promo_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=response_schema,
                        temperature=0.7,
                    )
                )
                
                # The SDK now automatically parses the JSON text output perfectly
                script_output = json.loads(response.text)
                
                st.success("🎉 Swarm Processing Complete! Campaign Script finalized.")
                st.subheader("📋 Final Production Blueprint")
                st.info(f"**Main Campaign Hook:** {script_output.get('campaign_hook')}")
                
                for scene in script_output.get("scenes", []):
                    with st.expander(f"🎬 Scene {scene.get('scene_number')} ({scene.get('duration_seconds')}s)", expanded=True):
                        st.markdown(f"🎨 **AI Visual Asset Prompt:** *\"{scene.get('visual_prompt_for_imagen')}\"*")
                        st.markdown(f"🔤 **Screen Text (Color: {brand_color}):** `{scene.get('on_screen_caption')}`")
                        st.markdown(f"🎙️ **Voiceover Narration:** *\"{scene.get('voiceover_audio_script')}\"*")
                        
            except Exception as e:
                st.error(f"Execution Error: {str(e)}")