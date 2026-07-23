from typing import List, Dict, Optional, Callable
import re
import torch
from functools import lru_cache
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from utils.text_processing import chunk_text

DEFAULT_MODEL = "google/flan-t5-base"

AVAILABLE_MODELS = {
    "flan-t5-small (fastest)": "google/flan-t5-small",
    "flan-t5-base (recommended)": "google/flan-t5-base",
    "flan-t5-large (best quality)": "google/flan-t5-large",
}

@lru_cache(maxsize=1)
def get_device():
    if torch.cuda.is_available():
        return torch.device("cuda")
    elif torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")

def load_model(model_name: str = DEFAULT_MODEL):
    device = get_device()
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    model.to(device)
    model.eval()
    return tokenizer, model, device

def _force_summarize_text(text: str) -> str:
    """Removes questions and instructional triggers to prevent AI refusals."""
    text = re.sub(r'[^.!?]*\?[^.!?]*', '', text)
    
    bad_phrases = [
        r"i'm going to ask you", r"i will ask you", r"let's see if you",
        r"let me ask you", r"can you tell me", r"what do you think",
        r"your task is to", r"figure out your", r"take this test",
        r"leave your answers", r"write your answers", r"pause the video",
        r"watch the video", r"in today's video", r"in this video",
        r"welcome back", r"before we begin",
    ]
    
    for phrase in bad_phrases:
        text = re.sub(phrase, "", text, flags=re.IGNORECASE)

    text = re.sub(r'\bI am\b', 'The speaker is', text, flags=re.IGNORECASE)
    text = re.sub(r'\bI will\b', 'The speaker will', text, flags=re.IGNORECASE)
    text = re.sub(r"\bI'll\b", 'The speaker will', text, flags=re.IGNORECASE)
    text = re.sub(r"\bI'm\b", 'The speaker is', text, flags=re.IGNORECASE)
    
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def _generate(tokenizer, model, device, prompt: str, max_new_tokens: int = 150, force_length: bool = False) -> str:
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512).to(device)

    gen_kwargs = {
        "max_new_tokens": max_new_tokens,
        "do_sample": False,
        "num_beams": 4,
        "repetition_penalty": 2.5, 
    }

    if force_length:
        gen_kwargs["length_penalty"] = 4.0    
        gen_kwargs["early_stopping"] = False 
    else:
        gen_kwargs["length_penalty"] = 1.2
        gen_kwargs["early_stopping"] = True

    with torch.no_grad():
        outputs = model.generate(**inputs, **gen_kwargs)

    text = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
    text = text.lstrip(":").lstrip('"').lstrip("'").strip()
    return text if text else "Could not generate output."

def summarize_chunks(
    chunks: List[str],
    tokenizer,
    model,
    device,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> List[str]:
    summaries = []
    total = len(chunks)

    for i, chunk in enumerate(chunks):
        if not chunk.strip():
            if progress_callback: progress_callback((i + 1) / total)
            continue

        clean_chunk = _force_summarize_text(chunk)
        
        if not clean_chunk.strip():
            if progress_callback: progress_callback((i + 1) / total)
            continue

        prompt = (
            "Article: "
            f"{clean_chunk}\n\n"
            "Extract the main facts from this article in two short sentences."
        )

        summaries.append(_generate(tokenizer, model, device, prompt, max_new_tokens=80))

        if progress_callback:
            progress_callback((i + 1) / total)

    return summaries

def generate_final_summary(cleaned_transcript: str, mini_summaries: List[str], tokenizer, model, device) -> str:
    """Generates the strict 6-line final summary as a proper paragraph."""
    word_count = len(cleaned_transcript.split())
    source_text = cleaned_transcript if word_count <= 600 else ' '.join(mini_summaries)
    
    strict_prompt = (
        "Summarize the provided text into a single paragraph containing exactly six full sentences. "
        "You must write in a narrative, educational tone. "
        "Do not write commands (do not start sentences with words like 'do', 'don't', 'stop', 'practice', 'know', or 'try'). "
        "Do not use bullet points. "
        "Ensure every sentence has a subject and a verb.\n\n"
        f"Text: {source_text}\n\n"
        "Paragraph:"
    )

    # Increased to 180 tokens to ensure the 6th sentence never gets cut off mid-word
    raw_paragraph = _generate(tokenizer, model, device, strict_prompt, max_new_tokens=180, force_length=True)
    
    # Split the paragraph by periods to create 6 distinct lines
    sentences = re.split(r'(?<=[.!?])\s+', raw_paragraph)
    
    # Filter out any empty strings just in case
    valid_sentences = [s.strip() for s in sentences if s.strip()]
    
    # Join them with line breaks so Streamlit displays them on 6 separate lines
    return "\n".join(valid_sentences[:6])

def summarize_transcript(
    transcript: str,
    model_name: str = DEFAULT_MODEL,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> Dict[str, str]:
    if not transcript or not transcript.strip():
        return {"summary": "No transcript provided.", "chunk_count": 0}

    tokenizer, model, device = load_model(model_name)
    
    fully_cleaned_transcript = _force_summarize_text(transcript)
    word_count = len(fully_cleaned_transcript.split())
    
    if word_count <= 400:
        mini_summaries = [fully_cleaned_transcript]
        chunks = [transcript]
    else:
        chunks = chunk_text(transcript, max_words=350)
        mini_summaries = summarize_chunks(chunks, tokenizer, model, device, progress_callback)

    final_summary = generate_final_summary(fully_cleaned_transcript, mini_summaries, tokenizer, model, device)

    return {
        "summary": final_summary,
        "chunk_count": len(chunks)
    }