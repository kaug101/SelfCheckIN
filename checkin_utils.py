import openai
import streamlit as st
import matplotlib.pyplot as plt

import pandas as pd
from datetime import datetime
from google_sheet import append_checkin_to_sheet, get_all_checkins
from checkin_crypto import encrypt_checkin, decrypt_checkin
from openai import OpenAI


from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

canvas_qs = {
    "Motivation": ["What still excites or matters to me?", "If I could only keep one reason to continue, what would it be?"],
    "Energy & Resilience": ["How am I feeling lately - physically, emotionally?", "What restores me? What drains me?"],
    "Support Systems": ["Who's truly in my corner right now?", "Where can I get the help I'm missing?"],
    "Growth Mindset": ["What's something new I've learned recently?", "Where am I avoiding challenge or feedback?"],
    "Vision": ["What would 'further' look like?", "Even if I don't know the final goal, what feels like the next right step?"]
}

def ask_questions():
    answers = {}
    for section, questions in canvas_qs.items():
        st.markdown(f"#### {section}")
        answers[section] = [
            st.text_area(q, key=q, max_chars=500, help="Max 100 words (~500 characters)") for q in questions
        ]
    return answers

def save_checkin(user_email, canvas_answers, score, recommendation=None):
    password = st.session_state.get("user_password", "")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = {
        "date": encrypt_checkin(now_str, password, user_email),
        "user": encrypt_checkin(user_email, password, user_email),
        "score": encrypt_checkin(str(score), password, user_email),
        "recommendation": encrypt_checkin(recommendation or "", password, user_email)
    }
    for section, answers in canvas_answers.items():
        entry[f"{section} Q1"] = encrypt_checkin(answers[0], password, user_email)
        entry[f"{section} Q2"] = encrypt_checkin(answers[1], password, user_email)
    append_checkin_to_sheet(entry)

def load_user_checkins(user_email):
    df = get_all_checkins()
    if df is not None and not df.empty:
        password = st.session_state.get("user_password", "")
        df["user_decrypted"] = df["user"].apply(lambda val: decrypt_checkin(val, password, user_email))
        df = df[df["user_decrypted"] == user_email]
        for col in df.columns:
            if col in ("user", "score", "recommendation", "date") or "Q" in col:
                df[col] = df[col].apply(lambda val: decrypt_checkin(val, password, user_email) if val else "")
        return df
    return None

def generate_openai_feedback(canvas_answers: dict) -> tuple[int, str, list[str]]:
    from openai import OpenAI
    import streamlit as st

    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    flat_responses = []
    for category, responses in canvas_answers.items():
        joined = " | ".join(responses)
        flat_responses.append(f"{category}: {joined}")

    prompt = f"""
You are a professional human coach known for being warm, insightful, and practical.

A user has completed a daily self-check-in across 5 key life areas: Motivation, Energy & Resilience, Support Systems, Growth Mindset, and Vision.

Your task is to:
1. Thoughtfully analyze their responses
2. Assign a score from 1 to 25 based on:
   - Emotional clarity
   - Depth of self-awareness
   - Intentionality
   - Growth-oriented thinking
3. Provide a short justification for the score
4. Share 2–3 specific coaching actions or reflections
5. Summarize their overall theme or growth direction in one line

Format:
Score: <number>
Explanation: <brief explanation>
Actions:
- <Personalized suggestion 1>
- <Personalized suggestion 2>
- <Optional suggestion 3>
Theme: <1-line theme>

User's responses:
{chr(10).join(flat_responses)}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4-0125-preview",
            messages=[
                {"role": "system", "content": "You are a wise and supportive human coach."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
        )
        content = response.choices[0].message.content.strip()

        # Extract score
        score_line = next((line for line in content.splitlines() if line.startswith("Score:")), "")
        score = int("".join([c for c in score_line if c.isdigit()])) if score_line else 0

        # Extract action lines
        actions = []
        capture = False
        for line in content.splitlines():
            if line.strip().startswith("Actions:"):
                capture = True
                continue
            if capture:
                if line.strip().startswith("Theme:"):
                    break
                if line.strip().startswith("-"):
                    actions.append(line.strip("- ").strip())

        return score, content, actions

    except Exception as e:
        return 0, f"⚠️ OpenAI Error: {str(e)}", []


def build_image_prompt(insights: str) -> str:
    return f"""
Create a clean, flat-style digital illustration that clearly represents a personalized coaching action plan.
Purpose: The image should help the user **visually recall** and **stay motivated to follow** their action plan.

The image should:
- Depict 3 key steps based on the actions from these coaching suggestions: {insights}
- Show these steps as a vertical or horizontal sequence, like a roadmap or flow
- For each step, include a symbolic scene   
- Use realistic or symbolic visuals only 
- Strictly avoid any form of written or typographic characters. Do not include letters, numbers, signs, or symbolic text.
- Style: Flat illustration, warm tone, soft colors

"""





def generate_image_from_prompt(prompt_text: str) -> str:
    try:
        client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt_text,
            n=1,
            size="1024x1024"
        )
        return response.data[0].url
    except Exception as e:
        st.error(f"❌ Image generation failed: {e}")
        return ""



from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

def overlay_coaching_text(image_url: str, action_items: list[str]) -> Image.Image:

    # Parse coaching suggestions
    #lines = [line.strip("- ").strip() for line in insights.splitlines() if line.strip().startswith("-")]
    lines = action_items

    # Load image
    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content)).convert("RGBA")

    draw = ImageDraw.Draw(img)
    width, height = img.size

    # Try to load a clean font
    try:
        font = ImageFont.truetype("arial.ttf", size=28)
    except:
        font = ImageFont.load_default()

    # Draw background strip at top
    overlay = Image.new("RGBA", img.size, (255,255,255,0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle([0, 0, width, 40 + 35 * len(lines)], fill=(255, 255, 255, 220))  # White strip

    # Draw each line
    y = 20
    for line in lines:
        overlay_draw.text((30, y), line, font=font, fill=(0, 0, 0, 255))  # Black text
        y += 35

    # Combine
    combined = Image.alpha_composite(img, overlay)

    return combined.convert("RGB")


def show_insights(df):
    import matplotlib.pyplot as plt
    from datetime import datetime, timedelta
    import matplotlib.dates as mdates

    st.subheader("📊 Check-In Score Summary")

    if "date" in df.columns and "score" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["score"] = pd.to_numeric(df["score"], errors="coerce")
        df = df.sort_values("date")

        # User selection for timeframe
        timeframe = st.selectbox("Show scores for:", ["Last 7 days", "Last 14 days", "Last 30 days", "All time"])
        days_map = {
            "Last 7 days": 7,
            "Last 14 days": 14,
            "Last 30 days": 30,
            "All time": None
        }
        days = days_map[timeframe]
        if days:
            cutoff_date = datetime.now().date() - timedelta(days=days)
            df_filtered = df[df["date"].dt.date >= cutoff_date]
        else:
            df_filtered = df

        # Plot
        fig, ax = plt.subplots(figsize=(12, 4))
        ax.plot(df["date"], df["score"], marker='o', linestyle='-', color='gray', alpha=0.3, label="All scores")
        ax.plot(df_filtered["date"], df_filtered["score"], marker='o', linestyle='-', color='blue', label=f"{timeframe}")

        # Threshold lines
        ax.axhline(y=10, color='red', linestyle='--', linewidth=1, label='Needs Attention (<10)')
        ax.axhline(y=20, color='green', linestyle='--', linewidth=1, label='Excellent (≥20)')

        ax.set_ylim(1, 25)
        ax.set_title("Check-In Score Summary")
        ax.set_xlabel("Date")
        ax.set_ylabel("Score (1–25)")

        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        fig.autofmt_xdate(rotation=45)

        ax.grid(True)
        ax.legend()
        st.pyplot(fig)

    # Coaching recommendation
    if "recommendation" in df.columns and not df["recommendation"].isnull().all():
        latest = df.sort_values("date").iloc[-1]
        st.subheader("🧠 Last Coaching Recommendation")
        st.markdown(latest["recommendation"])

    # Full data table
    with st.expander("📋 Show full check-in details"):
        st.dataframe(
            df.sort_values(by="date", ascending=False).style.format({"date": lambda d: d.strftime("%Y-%m-%d")}),
            use_container_width=True,
            height=300
        )




def get_demo_checkins(selected_email):
    df = get_all_checkins()
    if df is not None and not df.empty:
        password = st.session_state.get("user_password", "")
        df["user_decrypted"] = df["user"].apply(lambda val: decrypt_checkin(val, password, selected_email))
        df = df[df["user_decrypted"] == selected_email]
        for col in df.columns:
            if col in ("user", "score", "recommendation", "date") or "Q" in col:
                df[col] = df[col].apply(lambda val: decrypt_checkin(val, password, selected_email) if val else "")
        return df
    return pd.DataFrame()

def show_demo_coaching(selected_email):
    if selected_email == "alex@example.com":
        st.markdown("### Alex (alex@example.com)")
        st.markdown("- 🧠 **Stretch into a Leadership Role**  \nAlex is consistently performing at a high level and showing signs of sustained motivation and support. Taking on leadership can help channel their energy into multiplying impact.")
        st.markdown("- 🌱 **Experiment with New Challenges**  \nTo avoid plateauing, Alex should seek out stretch assignments or novel tasks that demand new skills and perspectives.")
        st.markdown("- 🧘 **Invest in Recovery Rituals**  \nWhile high performing, the data hints at intense engagement that could lead to burnout. Small rituals like nature walks or journaling can enhance long-term resilience.")
    elif selected_email == "jamie@example.com":
        st.markdown("### Jamie (jamie@example.com)")
        st.markdown("- 🛠️ **Build a Resilience Routine**  \nJamie’s entries show signs of moderate motivation but inconsistent energy. Introducing small, daily recovery habits can help maintain momentum.")
        st.markdown("- 🔍 **Clarify a Meaningful Short-Term Goal**  \nThe text shows a drift in purpose. Setting a concrete 2-week target can reinstate direction and reduce emotional fatigue.")
        st.markdown("- 🤝 **Expand Support Circle**  \nSupport system references are sparse. Encouraging Jamie to proactively reconnect with peers or mentors can stabilize emotional load.")
    elif selected_email == "morgan@example.com":
        st.markdown("### Morgan (morgan@example.com)")
        st.markdown("- 🛌 **Permission to Rest**  \nMorgan’s check-ins point to exhaustion and demotivation. Before any change, recovery needs to be prioritized — guilt-free rest is valid and necessary.")
        st.markdown("- 🧩 **Reconnect to Core Values**  \nThe text shows signs of identity disconnection. Reflecting on why certain things matter can re-anchor purpose and self-worth.")
        st.markdown("- 🔦 **Find Micro-Moments of Joy**  \nMorgan should be encouraged to note 1–2 tiny joys per day. Building emotional scaffolding from joy is a proven recovery tool.")
    else:
        st.warning("No coaching suggestions available.")
