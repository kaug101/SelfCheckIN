
from openai import OpenAI
import streamlit as st

def generate_openai_score(canvas_answers: dict) -> tuple[int, str]:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    flat_responses = []
    for section, answers in canvas_answers.items():
        joined = " | ".join(answers)
        flat_responses.append(f"{section}: {joined}")

    prompt = f"""
You are a coach evaluating a user's self-check-in.

Instructions:
- Read the responses below across five categories.
- Give a total score from 1–25 based on insightfulness, clarity, and depth of reflection.
- Provide a 2–3 sentence justification for the score.

Respond in this format only:
Score: <number>
Explanation: <brief explanation>

Responses:
{chr(10).join(flat_responses)}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4-0125-preview",
            messages=[
                {"role": "system", "content": "You are a coach evaluating self-check-in responses."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )

        output = response.choices[0].message.content.strip()
        lines = output.splitlines()
        score_line = next((line for line in lines if "Score" in line), "")
        explanation_line = next((line for line in lines if "Explanation" in line), "")

        score = int("".join([c for c in score_line if c.isdigit()]))
        explanation = explanation_line.replace("Explanation:", "").strip()

        return min(max(score, 1), 25), explanation

    except Exception as e:
        st.error(f"⚠️ OpenAI Score Error: {e}")
        return 0, "Error during scoring."
