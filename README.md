# 🎬 AI YouTube Video Summarizer

Paste any YouTube link and get an easy-to-understand **summary, main ideas,
key points, important lessons, and a conclusion** — generated locally on
your own CPU. No API keys, no paid services, no Ollama, no GPU required.

---

## ✨ Features

- Extracts transcripts directly from YouTube (`youtube-transcript-api`).
- Cleans up auto-caption artifacts (`[Music]`, filler words, extra whitespace).
- Automatically splits long transcripts into chunks so the AI model never
  gets overloaded, no matter how long the video is.
- Uses a small, free, locally-run Hugging Face model to generate:
  - ✅ Simple Summary
  - ✅ Main Ideas
  - ✅ Key Points
  - ✅ Important Lessons
  - ✅ Short Conclusion
- Clean Streamlit UI with a progress bar and clear error messages.
- Model loads once and is cached for the rest of the session (fast repeat use).
- Works on a normal laptop, CPU-only — no GPU needed.
- Choice of 3 model sizes in the sidebar, from ~80MB to ~300MB.

---

## 🧠 How It Works

```
YouTube URL
    │
    ▼
Extract video ID  ──────────────►  Fetch title/author (YouTube oEmbed, free)
    │
    ▼
Fetch transcript (youtube-transcript-api)
    │
    ▼
Clean transcript (remove [Music], filler words, extra whitespace)
    │
    ▼
Split into ~350-word chunks (keeps within the AI model's input limit)
    │
    ▼
"Map" step: summarize each chunk individually with the local AI model
    │
    ▼
"Reduce" step: combine mini-summaries, then ask the model for:
   simple summary / main ideas / key points / lessons / conclusion
    │
    ▼
Display everything in the Streamlit UI
```

This **map-reduce** approach is what allows the app to handle very long
videos (multi-hour talks, lectures, podcasts) without crashing or exceeding
the AI model's input size, since each individual piece of text sent to the
model stays small.

---

## 🛠 Technologies Used

| Purpose                  | Technology                                   |
|---------------------------|----------------------------------------------|
| UI                        | [Streamlit](https://streamlit.io)            |
| Transcript extraction     | [youtube-transcript-api](https://pypi.org/project/youtube-transcript-api/) |
| Video title/author        | YouTube's public oEmbed endpoint (no key needed) |
| AI summarization          | [Hugging Face Transformers](https://huggingface.co/docs/transformers) running `google/flan-t5-base` (default), `google/flan-t5-small`, or `sshleifer/distilbart-cnn-12-6` — all free, open-source, CPU-friendly models |
| ML backend                | [PyTorch](https://pytorch.org) (CPU version) |

**No OpenAI, no Claude API, no paid Gemini tier, no Ollama, and no credit
card are used anywhere in this project.**

---

## 📦 Project Structure

```
youtube-ai-summarizer/
│
├── app.py                     # Streamlit UI and main app flow
├── requirements.txt           # All Python dependencies
├── README.md                  # This file
├── .gitignore
│
├── utils/
│   ├── __init__.py
│   ├── youtube.py              # URL parsing, transcript + metadata fetching
│   ├── summarizer.py           # Model loading + map-reduce summarization
│   └── text_processing.py      # Transcript cleaning + chunking
│
└── models/                     # (empty) Hugging Face model cache lands here
```

---

## 🚀 Installation & Setup (VS Code Terminal)

### 1. Open the project folder in VS Code, then open a terminal (`` Ctrl+` ``)

### 2. Create a virtual environment
```bash
python -m venv venv
```

### 3. Activate the virtual environment

**Windows CMD:**
```bash
venv\Scripts\activate
```

**Windows PowerShell:**
```powershell
venv\Scripts\Activate.ps1
```
> If PowerShell blocks the script with an execution-policy error, run:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
> then try activating again.

**macOS / Linux:**
```bash
source venv/bin/activate
```

### 4. Install dependencies
```bash
pip install -r requirements.txt
```
> First install may take a few minutes since it downloads PyTorch (CPU
> version). This is a one-time step.

### 5. Run the app
```bash
streamlit run app.py
```

Streamlit will open the app automatically in your browser (usually at
`http://localhost:8501`). If it doesn't open automatically, click the
link shown in the terminal.

### 6. First-time model download

The very first time you click **Summarize**, Transformers will download the
selected AI model (~80–300MB depending on your choice in the sidebar) from
Hugging Face and cache it locally. Every run after that reuses the cached
copy — no repeated downloads.

---

## 🖱 Usage

1. Paste a YouTube video URL (e.g. `https://www.youtube.com/watch?v=VIDEOID`).
2. (Optional) Pick a model size in the sidebar — smaller = faster.
3. Click **Summarize**.
4. Watch the progress bar as the app extracts the transcript and processes it.
5. Read the video title, transcript length, and the five generated sections.
6. Expand "View cleaned transcript" to see the full processed transcript.

---

## ⚠️ Error Handling

The app gives clear, specific messages instead of raw errors for:

| Situation                         | What happens                                                        |
|-------------------------------------|----------------------------------------------------------------------|
| Invalid/garbled YouTube URL         | "That doesn't look like a valid YouTube URL..." with format examples |
| Video has no captions/transcript   | Clear message explaining the video has no transcript available       |
| Private / deleted / restricted video | Clear message that the video isn't accessible                      |
| No internet connection             | "No internet connection. Please check your network and try again."  |
| Very long videos                   | Automatically chunked; an info banner lets you know it may take longer |
| Empty/too-short transcript          | Rejected with a clear message rather than producing a nonsense summary |

---

## 🩺 Common Errors & Solutions

**"No module named 'streamlit'" (or transformers/torch/etc.)**
→ Your virtual environment isn't activated, or dependencies weren't
installed. Re-run steps 3–4 above.

**PowerShell: "running scripts is disabled on this system"**
→ Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
in PowerShell, then re-activate the environment.

**First summarize click is very slow**
→ Normal — the AI model is being downloaded and loaded into memory for the
first time. Subsequent summaries in the same session are much faster.

**"Could not retrieve a transcript for this video"**
→ The video may have transcripts disabled, or be a livestream/music video
with no captions. Try a different video, or one with the "CC" captions
icon available on YouTube.

**Out of memory / app crashes on a very long video**
→ Switch to the smaller `flan-t5-small` model in the sidebar, which uses
significantly less RAM.

**Torch install is slow or very large**
→ You can install the CPU-only PyTorch build explicitly for a smaller
download:
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

**`ConnectionError` when fetching transcript/metadata**
→ Check your internet connection. YouTube must be reachable to fetch
transcripts and video info (everything else — the AI model — runs offline
once downloaded).

---

## 🔒 Privacy & Cost

- No API keys are used or required anywhere in this project.
- No data is sent to any paid AI provider (OpenAI, Anthropic, Google's paid
  Gemini tier, etc.).
- The only network calls are: (1) fetching the transcript/title from
  YouTube, and (2) the one-time model download from Hugging Face. All
  summarization computation happens locally on your machine.
- This project is 100% free to run, indefinitely.

---

## 📋 Requirements Recap

- Python 3.9+
- ~1–2 GB free disk space (for PyTorch + the small model)
- A normal laptop CPU — no GPU needed
- An internet connection (for transcript fetching and the initial model download)
