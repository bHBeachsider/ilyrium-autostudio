import streamlit as st
import google.generativeai as genai
import os
import json

# --- 1. SETUP GEMINI API ---
# In production on Railway, securely load this via the Variables tab.
# For local testing, you can paste your actual API key below temporarily.
API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
genai.configure(api_key=API_KEY)

# Using gemini-1.5-pro for strict JSON schema conformance and advanced reasoning
model = genai.GenerativeModel('gemini-1.5-pro')

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
    business_name = st.text_input("Business Name", value="Ilyrium Bar & Grill", help="Your business name as it should appear on screen.")
    brand_color = st.color_picker("Primary Brand Color", "#FF4B4B", help="Used to brand text overlays and hardcoded captions.")

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
    placeholder="e.g., Live Music this Saturday night featuring local blues band 'The Delta Echoes'. Doors open at 7 PM. Happy hour pricing on all craft beer pitchers until 9 PM!",
    height=120
)

# --- 5. THE AGENTIC AGENT SWARM EXECUTION ---
if st.button("🚀 Generate Marketing Campaign Script", use_container_width=True):
    if not promo_prompt:
        st.warning("Please describe your event or offer before generating!")
    elif API_KEY == "YOUR_GEMINI_API_KEY_HERE" and "GEMINI_API_KEY" not in os.environ:
        st.error("Missing Gemini API Key! Please add it to your Railway environment variables or paste it into app.py.")
    else:
        with st.spinner("Calling Agent 2: The Creative Director is structuring your timeline..."):
            
            # System prompt structuring Gemini into a deterministic content agent
            system_instruction = f"""
            You are an expert B2B social media marketing director specializing in local brick-and-mortar advertising.
            Your job is to read raw campaign details from a small business owner and convert them into a tight, conversion-focused 15-second script.
            
            Business Context:
            - Business Name: {business_name}
            - Visual Style/Vibe: {brand_vibe}
            - Output Dimension: {video_ratio}
            
            Rules:
            1. Create exactly 3 logical chronological scenes totalizing 15 seconds.
            2. Scene 1 MUST be a high-impact 'Hook' to stop users from scrolling.
            3. Scene 3 MUST include a clear Call to Action (CTA) based on the business name.
            
            You must return ONLY a clean JSON block matching the structure below. Do not wrap it in markdown code blocks or add conversational prose.
            
            Expected JSON format:
            {{
                "campaign_hook": "Hook sentence",
                "scenes": [
                    {{
                        "scene_number": 1,
                        "duration_seconds": 5,
                        "visual_prompt_for_imagen": "Detailed descriptive visual prompt suitable for an image generator (Imagen 3) describing backgrounds, actors, lighting, and textures.",
                        "on_screen_caption": "SHORT UPPERCASE BOLD CAPTIONS FOR OVERLAY",
                        "voiceover_audio_script": "The exact words the voiceover agent will read out loud naturally."
                    }}
                ]
            }}
            """
            
            try:
                # Execution
                response = model.generate_content(
                    contents=f"{system_instruction}\n\nUser Input Data: {promo_prompt}"
                )
                
                # Dynamic sanitization to clean up output
                raw_text = response.text.strip()
                if raw_text.startswith("```json"):
                    raw_text = raw_text.replace("```json", "", 1)
                if raw_text.endswith("```"):
                    raw_text = raw_text.rsplit("```", 1)[0]
                raw_text = raw_text.strip()
                
                # Parse JSON string to Python dictionary
                script_output = json.loads(raw_text)
                
                st.success("🎉 Swarm Processing Complete! Campaign Script finalized.")
                
                # Display output cleanly for the dashboard interface
                st.subheader("📋 Final Production Blueprint")
                st.info(f"**Main Campaign Hook:** {script_output.get('campaign_hook')}")
                
                for scene in script_output.get("scenes", []):
                    with st.expander(f"🎬 Scene {scene.get('scene_number')} ({scene.get('duration_seconds')}s)", expanded=True):
                        st.markdown(f"🎨 **AI Visual Asset Prompt (Agent 3):** *\"{scene.get('visual_prompt_for_imagen')}\"*")
                        st.markdown(f"🔤 **Hardcoded Screen Text (Color: {brand_color}):** `{scene.get('on_screen_caption')}`")
                        st.markdown(f"🎙️ **Voiceover Narration:** *\"{scene.get('voiceover_audio_script')}\"*")
                        
            except json.JSONDecodeError:
                st.error("Failed to parse output as clean JSON. The AI gave an unformatted response.")
                st.text(response.text)
            except Exception as e:
                st.error(f"Execution Error: {str(e)}")