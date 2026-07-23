"""
app.py
------
AI YouTube Video Summarizer - Streamlit front-end.

Runs entirely on free, local, open-source tools:
- youtube-transcript-api  -> transcript extraction (no API key)
- YouTube oEmbed endpoint -> video title/author (no API key)
- Hugging Face Transformers (google/flan-t5-base by default) -> local CPU/GPU
  summarization (no API key, no Ollama, no paid service)

Run with:
    streamlit run app.py
"""

import streamlit as st
import requests

from utils.youtube import (
    extract_video_id,
    get_transcript,
    get_video_metadata,
    InvalidYouTubeURLError,
    TranscriptNotAvailableError,
    VideoNotAccessibleError,
)
from utils.text_processing import clean_transcript, word_count
from utils.summarizer import summarize_transcript, AVAILABLE_MODELS, DEFAULT_MODEL

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI YouTube Video Summarizer",
    layout="centered",
)

st.title("AI YouTube Video Summarizer")
st.caption("Paste a YouTube link to get a concise, high-quality summary.")

# ---------------------------------------------------------------------------
# Sidebar: model selection and settings
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Settings")
    model_label = st.selectbox(
        "AI Model",
        options=list(AVAILABLE_MODELS.keys()),
        index=list(AVAILABLE_MODELS.values()).index(DEFAULT_MODEL),
        help="Smaller models are faster but slightly less detailed. The model downloads once and is cached.",
    )
    selected_model = AVAILABLE_MODELS[model_label]

    st.markdown("---")
    st.markdown(
        "**About**\n\n"
        "This app runs an open-source AI model locally on your machine. "
        "No data is sent to any paid AI service, and no API key is needed."
    )

# ---------------------------------------------------------------------------
# Main input
# ---------------------------------------------------------------------------
url = st.text_input(
    "YouTube Video URL",
    placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
)

summarize_clicked = st.button("Summarize", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------
if summarize_clicked:
    if not url or not url.strip():
        st.warning("Please enter a YouTube URL first.")
        st.stop()

    progress = st.progress(0, text="Starting...")

    # ---- Step 1: Parse the URL -------------------------------------------------
    try:
        video_id = extract_video_id(url)
    except InvalidYouTubeURLError as e:
        progress.empty()
        st.error(f"Invalid URL: {e}")
        st.stop()

    # ---- Step 2: Fetch metadata ------------------------------------------------
    progress.progress(10, text="Fetching video info...")
    try:
        metadata = get_video_metadata(video_id)
    except VideoNotAccessibleError as e:
        progress.empty()
        st.error(f"{e}")
        st.stop()

    # ---- Step 3: Fetch transcript ----------------------------------------------
    progress.progress(30, text="Extracting transcript...")
    try:
        raw_transcript = get_transcript(video_id)
    except TranscriptNotAvailableError as e:
        progress.empty()
        st.error(
            f"{e}\n\n"
            "Tips: Some videos (music, auto-dubbed, or creator-disabled captions) "
            "simply have no transcript available. Try a different video."
        )
        st.stop()
    except VideoNotAccessibleError as e:
        progress.empty()
        st.error(f"{e}")
        st.stop()
    except requests.exceptions.ConnectionError:
        progress.empty()
        st.error("Network error. Please check your internet connection and try again.")
        st.stop()

    # ---- Step 4: Clean transcript ----------------------------------------------
    progress.progress(45, text="Cleaning transcript...")
    cleaned = clean_transcript(raw_transcript)
    transcript_word_count = word_count(cleaned)

    if transcript_word_count < 20:
        progress.empty()
        st.error("The transcript is too short or empty to summarize meaningfully.")
        st.stop()

    if transcript_word_count > 8000:
        st.info(
            f"This is a long video (approximately {transcript_word_count} words). "
            "Summarization may take a bit longer since it is processed in chunks."
        )

    # ---- Step 5: Summarize -----------------------------------------------------
    progress.progress(55, text="Loading AI model (first run downloads weights)...")

    def _update_progress(fraction: float):
        pct = 55 + int(fraction * 40)
        progress.progress(min(pct, 95), text=f"Summarizing chunks... {int(fraction * 100)}%")

    try:
        result = summarize_transcript(
            cleaned, model_name=selected_model, progress_callback=_update_progress
        )
    except Exception as e:
        progress.empty()
        st.error(
            f"An error occurred while generating the summary: {e}\n\n"
            "If this is a memory error, try selecting a smaller model "
            "(flan-t5-small) in the sidebar and try again."
        )
        st.stop()

    progress.progress(100, text="Done.")
    progress.empty()

    # ---- Display results -------------------------------------------------------
    st.success("Summary generated.")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Video Title", metadata["title"])
    with col2:
        st.metric("Transcript Length", f"{transcript_word_count} words")

    st.markdown(f"**Channel:** {metadata['author']}")

    st.markdown("---")

    st.subheader("Summary")
    st.write(result["summary"])

else:
    st.info("Enter a YouTube URL above and click **Summarize** to get started.")