import requests
import streamlit as st

def generate_image_from_prompt_gemini(prompt_text: str, resolution: str = "1080x1920") -> str:
    """
    Generate an image using Gemini's Imagegen 4 API with smartphone-optimized settings.
    
    Args:
        prompt_text (str): The prompt describing the image to be generated.
        resolution (str): Desired resolution. Suggested: "1080x1920" (default), or "1440x2560".
        
    Returns:
        str: URL or path of the generated image, or an empty string if failed.
    """

    api_key = st.secrets.get("GEMINI_API_KEY")  # Add to your .streamlit/secrets.toml
    if not api_key:
        st.error("🚫 Gemini API key missing.")
        return ""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "prompt": prompt_text,
        "resolution": resolution,
        "format": "webp",  # Prefer WebP for web/app optimization
        "style": "flat",   # Optional style hint if supported
        "model": "gemini-imagegen-4"
    }

    try:
        response = requests.post("https://api.gemini.google.com/v1/image/generate",  # Replace with actual URL
                                 headers=headers, json=payload)
        response.raise_for_status()
        image_url = response.json().get("image_url", "")
        if not image_url:
            st.error("❌ No image URL returned.")
        return image_url
    except Exception as e:
        st.error(f"❌ Gemini image generation failed: {e}")
        return ""


def generate_coaching_image_gemini(question_text: str, resolution: str = "1080x1920") -> str:
    """
    Generate a symbolic, coaching-themed image using Gemini Imagegen 4 for a given reflection question.
    """
    coaching_context = (
        "You are a visual illustrator helping users reflect deeply during a daily coaching ritual. "
        "Create a warm, symbolic, emotionally evocative image (no text or numbers) that matches the theme of this coaching question:\n\n"
        f"Question: {question_text}\n\n"
        "Image style: flat illustration, warm tones, symbolic or metaphorical visual cues. "
        "Do not include any letters, text, or numeric characters. Format must be portrait for smartphone screens."
    )

    return generate_image_from_prompt_gemini(coaching_context, resolution=resolution)

