import os
import html
import json
import random
import streamlit as st
from llama_cpp import Llama
from engine.final_generator import generate_story_fast
import requests

# =========================
# LOAD DATASET (SIMPLE WAY)
# =========================

DATASET_FILE = "datasets.json"

@st.cache_data
def load_prompts():
    if not os.path.exists(DATASET_FILE):
        return []

    with open(DATASET_FILE) as f:
        data = json.load(f)

    all_prompts = []

    for url in data.get("story_prompts", []):
        try:
            response = requests.get(url)

            if response.status_code == 200:
                file_data = response.json()  # expects JSON list
                all_prompts.extend(file_data)
        except:
            pass

    return all_prompts


# =========================
# MODEL SETUP
# =========================

MODEL_PATH = "models/tinyllama.gguf"

MODEL_URL = "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q2_K.gguf"


def download_model():
    if not os.path.exists(MODEL_PATH):
        st.warning("Downloading model... ⏳")
        os.makedirs("models", exist_ok=True)

        try:
            with requests.get(MODEL_URL, stream=True) as r:
                r.raise_for_status()
                with open(MODEL_PATH, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
        except Exception as e:
            st.error(f"Download failed: {e}")
            st.stop()


download_model()

# ✅ LOAD MODEL (ONLY ONCE)
@st.cache_resource
def load_model():
    return Llama(
        model_path="models/tinyllama.gguf",
        n_ctx=2048,      # Increased context for longer stories
        n_threads=4,     # Experiment: 4 is often faster than 6 or 8 due to overhead
        n_batch=512,     # Process the prompt in larger chunks
    )

model = load_model()


# ✅ PAGE CONFIG
st.set_page_config(
    page_title="AI Story Generator",
    layout="wide",
)


# ✅ LOAD CSS
css_path = os.path.join("styles", "theme.css")
if os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# ✅ SESSION STATE INIT
if "page" not in st.session_state:
    st.session_state.page = "Home"

if "stories" not in st.session_state:
    st.session_state.stories = []


# ✅ NAVBAR
def navbar():
    col1, col2, col3, col4 = st.columns([6, 1, 1, 1])

    with col1:
        st.markdown("### 📖 AI Story Generator")

    with col2:
        if st.button("Home", use_container_width=True):
            st.session_state.page = "Home"

    with col3:
        if st.button("About", use_container_width=True):
            st.session_state.page = "About"

    with col4:
        if st.button("Contact", use_container_width=True):
            st.session_state.page = "Contact"


# ✅ RESET BUTTON
def reset_button():
    col1, col2 = st.columns([8, 2])
    with col2:
        if st.button("➕ Add New Story", use_container_width=True):
            st.session_state.stories = []


# ✅ SIDEBAR CONTROLS
def sidebar_controls():
    with st.sidebar:
        st.markdown("## ✨ Story Settings")

        genre = st.selectbox(
            "Genre",
            ["Mystery", "Fantasy", "Romance", "Sci-Fi", "Slice of Life", "Horror", "Adventure"],
        )

        character = st.text_input(
            "Character",
            value="A curious girl"
        )

        theme = st.selectbox(
            "Theme",
            ["Secrets", "Friendship", "Revenge", "Betrayal", "Love", "Survival", "Redemption", "Ambition"],
        )

        tone = st.selectbox(
            "Tone",
            ["Serious", "Warm", "Melancholic", "Hopeful", "Dark", "Dreamy"],
        )

        length = st.selectbox(
            "Length",
            ["Short", "Medium", "Long"],
            index=1,
        )

    return genre, character, theme, tone, length


# ✅ FORMAT STORY
def format_story(story: str) -> str:
    paragraphs = story.strip().split("\n\n")
    formatted = "".join(f"<p>{p.strip()}</p>" for p in paragraphs)
    return formatted


# ✅ STORY CARD (🔥 TITLE FIX HERE)
def render_story_card(item: dict, story_number: int):
    title = item.get("title", "").strip()

    # 🔥 fallback title
    if not title or title.lower() == "generated story":
        title = f"Story {story_number}"

    prompt = html.escape(item.get("prompt", ""))
    story = item.get("story", "")

    # 🔥 DYNAMIC TITLE (FIXED)
    st.markdown(f"## 📖 {title}")

    with st.expander("🧠 View Prompt"):
        st.write(prompt)

    st.markdown("#### ✨ Story")

    st.markdown(
        f"""
        <div class='card'>
            <div class='story-text'>
                {format_story(story)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()


# ✅ HOME PAGE
def home_page():
    reset_button()

    genre, character, theme, tone, length = sidebar_controls()

    st.markdown(
        """
        <div style='text-align:center; margin-top:30px;'>
            <h1>Narrative Dashboard</h1>
            <p>Create, explore, and generate AI stories</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.subheader("✍️ Start a New Story")

    with st.form("prompt_form", clear_on_submit=True):
        user_prompt = st.text_area(
            "Enter your story idea",
            placeholder="Example: A girl finds an old letter in a quiet rainy town...",
            height=120,
        )

        submitted = st.form_submit_button("➤ Generate Story")

    if submitted and user_prompt.strip():
        with st.spinner("Generating story... ✨"):
            result = generate_story_fast(
                model=model,
                genre=genre,
                character=character,
                theme=theme,
                tone=tone,
                length=length,
                user_prompt=user_prompt,
            )

        # ✅ SAVE STORY
        st.session_state.stories.append(result)

        st.rerun()

    # 🔥 STORY VAULT
    st.markdown(f"## 📚 Story Vault ({len(st.session_state.stories)})")

    for i, item in enumerate(reversed(st.session_state.stories), 1):
        story_number = len(st.session_state.stories) - i + 1
        render_story_card(item, story_number)


# ✅ ABOUT PAGE
def about_page():
    st.markdown(
        """
        <div class='info-page'>
            <h2>About</h2>
            <p>
            A lightweight AI-powered story generation application that runs fully offline using Small Language Models (SLMs). This project allows users to generate creative stories based on custom inputs like genre, theme, tone, and characters — without relying on cloud APIs.
            </p>
            <h5>Features</h5>
            <p>
            🧠 Offline AI Generation - Runs locally using SLMs (e.g., TinyLLaMA via llama.cpp) <br>
            🎭 Custom Story Inputs - Genre, tone, theme, character, and user prompts <br>
            ⚡ Fast Inference - Optimized for low-resource systems <br>
            ✍️ Structured Story Output - Clean, readable, and formatted stories <br>
            🔒 Privacy-Friendly - No internet or external API required <br>
            </p>          
        </div>
        """,
        unsafe_allow_html=True,
    )


# ✅ CONTACT PAGE
def contact_page():
    st.markdown(
        """
        <div class='info-page'>
            <h2>Contact</h2>
            <p>Have questions, suggestions, or want to collaborate? Feel free to reach out!</p>
            <p><b>Email:</b> ai_story_generator@gmail.in</p>
            <p><b>Phone:</b>9874563210</p>
            <p><b>Address:</b> <br> AI Story Plot Generator <br> Bhavani Street <br> Hydrebad, Andhra Pradesh - 530045 <br> India</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ✅ RUN APP
navbar()

if st.session_state.page == "Home":
    home_page()
elif st.session_state.page == "About":
    about_page()
elif st.session_state.page == "Contact":
    contact_page()
    
