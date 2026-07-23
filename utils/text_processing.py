"""
text_processing.py
-------------------
Utilities to clean raw YouTube transcript text and split long transcripts
into model-friendly chunks (small local models have limited input windows).
"""

import re
from typing import List


def clean_transcript(raw_text: str) -> str:
    """
    Clean a raw transcript string:
    - Remove bracketed sound-cue tags like [Music], [Applause], [Laughter].
    - Collapse repeated whitespace/newlines.
    - Fix common filler artifacts left by auto-captions.
    """
    if not raw_text:
        return ""

    text = raw_text

    # Remove [Music], [Applause], (inaudible), etc.
    text = re.sub(r"\[.*?\]", " ", text)
    text = re.sub(r"\(.*?\)", " ", text)

    # Remove excessive filler repeats like "um um um"
    text = re.sub(r"\b(um+|uh+|erm+)\b", "", text, flags=re.IGNORECASE)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def word_count(text: str) -> int:
    return len(text.split())


def chunk_text(text: str, max_words: int = 350) -> List[str]:
    """
    Split text into chunks of roughly `max_words` words each, breaking on
    sentence boundaries where possible so chunks stay coherent for the model.

    max_words=350 is a safe default for small transformer models (they
    typically handle 512-1024 tokens; ~350 words keeps well under that
    limit once tokenized).
    """
    if not text:
        return []

    # Split into sentences (simple heuristic, good enough for spoken transcripts)
    sentences = re.split(r"(?<=[.!?])\s+", text)

    chunks = []
    current_chunk_words = []
    current_count = 0

    for sentence in sentences:
        sentence_word_count = len(sentence.split())

        # If a single sentence is itself huge, force-split it
        if sentence_word_count > max_words:
            words = sentence.split()
            for i in range(0, len(words), max_words):
                chunks.append(" ".join(words[i:i + max_words]))
            continue

        if current_count + sentence_word_count > max_words and current_chunk_words:
            chunks.append(" ".join(current_chunk_words))
            current_chunk_words = []
            current_count = 0

        current_chunk_words.append(sentence)
        current_count += sentence_word_count

    if current_chunk_words:
        chunks.append(" ".join(current_chunk_words))

    return chunks
