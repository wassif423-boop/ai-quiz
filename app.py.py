import json
import time
import streamlit as st
from google import genai
from google.genai import types

st.set_page_config(page_title="AI Quiz Generator", page_icon="🧠", layout="wide")

st.markdown("""
<style>
.stApp {background: #0b1020; color: #f4f6ff;}
[data-testid="stSidebar"] {background: #10172a;}
h1, h2, h3, p, label {color: #f4f6ff !important;}
div.stButton > button {border-radius: 10px; font-weight: 600;}
</style>
""", unsafe_allow_html=True)

if "questions" not in st.session_state:
    st.session_state.questions = []
if "answers" not in st.session_state:
    st.session_state.answers = {}
if "submitted" not in st.session_state:
    st.session_state.submitted = False

st.title("🧠 AI Quiz Generator")
st.caption("Create and attempt topic-based multiple-choice quizzes.")

with st.sidebar:
    st.header("Quiz Settings")
    topic = st.text_input("Topic", placeholder="e.g. CNN, EDA, Python, Machine Learning")
    difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
    count = st.number_input("Number of MCQs", min_value=3, max_value=30, value=10, step=1)
    extra = st.text_area("Optional instructions", placeholder="e.g. Focus on definitions and practical concepts")
    generate = st.button("✨ Generate MCQs", type="primary", use_container_width=True)
    st.divider()
    st.caption("Gemini API key is stored in Streamlit Secrets, not in GitHub.")

def get_client():
    key = st.secrets.get("GEMINI_API_KEY", None)
    if not key:
        st.error("GEMINI_API_KEY is missing. Add it in Streamlit App settings → Secrets.")
        return None
    return genai.Client(api_key=key)

def make_questions(topic, difficulty, count, extra):
    client = get_client()
    if client is None:
        return []

    prompt = f"""
Create exactly {count} original multiple-choice questions for the topic: {topic}.
Difficulty: {difficulty}.
Additional instructions: {extra or "Cover a balanced range of important concepts."}

Return ONLY valid JSON in this exact structure:
{{
  "questions": [
    {{
      "question": "Question text",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": "Exact text of the correct option",
      "explanation": "One or two sentence explanation"
    }}
  ]
}}
Rules:
- Every question must have exactly four distinct options.
- Only one option is correct.
- The answer must exactly match one option.
- Avoid duplicate questions.
- Keep the requested difficulty appropriate.
"""
    # Try the main model first, then a backup model if Google is temporarily busy.
    # Short exponential backoff helps with temporary 503/UNAVAILABLE errors.
    model_names = ["gemini-3.8-flash", "gemini-3.7-flash"]
    last_error = None
    response = None

    for model_name in model_names:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.7
                    )
                )
                if response and response.text:
                    break
                raise ValueError("Gemini returned an empty response.")
            except Exception as e:
                last_error = e
                error_text = str(e).upper()

                # Do not retry invalid keys or exhausted quota.
                if "429" in error_text or "QUOTA" in error_text or "API KEY" in error_text or "PERMISSION_DENIED" in error_text:
                    raise

                temporary_error = any(
                    marker in error_text
                    for marker in ["503", "UNAVAILABLE", "500", "INTERNAL", "OVERLOADED", "TIMEOUT"]
                )
                if not temporary_error:
                    raise

                if attempt < 2:
                    time.sleep(2 ** (attempt + 1))  # waits 2, then 4 seconds

        if response and response.text:
            break

    if response is None or not response.text:
        raise RuntimeError(
            "Gemini is temporarily busy. Please try again in a minute. "
            f"Last error: {last_error}"
        )

    data = json.loads(response.text)
    qs = data.get("questions", [])
    valid = []
    for q in qs:
        opts = q.get("options", [])
        ans = q.get("answer", "")
        if q.get("question") and len(opts) == 4 and len(set(opts)) == 4 and ans in opts:
            valid.append(q)
    return valid

if generate:
    if not topic.strip():
        st.warning("Please enter a topic first.")
    else:
        with st.spinner("AI is preparing your MCQs..."):
            try:
                st.session_state.questions = make_questions(topic.strip(), difficulty, int(count), extra.strip())
                st.session_state.answers = {}
                st.session_state.submitted = False
                if not st.session_state.questions:
                    st.warning("No valid questions were returned. Try again with a simpler topic.")
            except Exception as e:
                error_text = str(e)
                if "503" in error_text or "UNAVAILABLE" in error_text.upper() or "temporarily busy" in error_text.lower():
                    st.error("Gemini is busy right now, even after retrying the backup model. Please wait a minute and try again.")
                elif "429" in error_text or "QUOTA" in error_text.upper():
                    st.error("Gemini free usage limit has been reached. Please wait until the quota resets.")
                else:
                    st.error(f"Could not generate the quiz: {error_text}")

if st.session_state.questions:
    qs = st.session_state.questions
    st.subheader(f"Your Quiz · {len(qs)} Questions")
    st.write(f"**Topic:** {topic or 'Selected topic'}  |  **Difficulty:** {difficulty}")
    with st.form("quiz_form"):
        selected_answers = {}
        for i, q in enumerate(qs):
            st.markdown(f"**Q{i+1}. {q['question']}**")
            selected_answers[i] = st.radio(
                "Choose one answer:",
                q["options"],
                index=None,
                key=f"answer_{i}",
                label_visibility="collapsed"
            )
            st.divider()
        submitted = st.form_submit_button("Submit Quiz", type="primary", use_container_width=True)

    if submitted:
        st.session_state.answers = selected_answers
        st.session_state.submitted = True

    if st.session_state.submitted:
        score = sum(1 for i, q in enumerate(qs) if st.session_state.answers.get(i) == q["answer"])
        total = len(qs)
        pct = round(score / total * 100, 1) if total else 0
        st.subheader("📊 Your Result")
        c1, c2, c3 = st.columns(3)
        c1.metric("Score", f"{score}/{total}")
        c2.metric("Percentage", f"{pct}%")
        c3.metric("Correct", score)
        if pct >= 80:
            st.success("Excellent work!")
        elif pct >= 50:
            st.info("Good effort. Review the explanations below.")
        else:
            st.warning("Keep practicing. You can improve!")
        st.subheader("Answer Review")
        for i, q in enumerate(qs):
            chosen = st.session_state.answers.get(i)
            correct = chosen == q["answer"]
            st.markdown(f"**Q{i+1}. {q['question']}**")
            st.write(f"Your answer: {chosen or 'Not answered'}")
            st.write(f"Correct answer: {q['answer']}")
            st.write(f"Explanation: {q.get('explanation', 'No explanation provided.')}")
            st.success("Correct") if correct else st.error("Incorrect")
            st.divider()
        if st.button("Create Another Quiz"):
            st.session_state.questions = []
            st.session_state.answers = {}
            st.session_state.submitted = False
            st.rerun()
else:
    st.info("Enter a topic in the sidebar and select a difficulty to generate your first quiz.")
