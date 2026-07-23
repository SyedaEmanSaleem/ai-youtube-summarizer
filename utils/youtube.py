"""
youtube.py
----------
Helper functions to:
1. Parse/validate a YouTube URL and extract the video ID.
2. Fetch the transcript of a video (free, no API key) using youtube-transcript-api.
3. Fetch basic video metadata (title, author) using YouTube's public oEmbed
   endpoint (free, no API key, no downloads).

No paid API, no API key, and no heavy downloads are used anywhere in this file.
"""

import re
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

# ---------------------------------------------------------------------------
# Custom exceptions so the Streamlit app can show clean, specific error
# messages instead of raw Python tracebacks.
# ---------------------------------------------------------------------------
class InvalidYouTubeURLError(Exception):
    """Raised when the given string is not a recognizable YouTube URL."""
    pass


class TranscriptNotAvailableError(Exception):
    """Raised when a video has no transcript/captions available."""
    pass


class VideoNotAccessibleError(Exception):
    """Raised when a video is private, deleted, or otherwise unreachable."""
    pass


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------
_YOUTUBE_ID_PATTERNS = [
    r"(?:youtube\.com/watch\?v=)([\w-]{11})",
    r"(?:youtube\.com/shorts/)([\w-]{11})",
    r"(?:youtu\.be/)([\w-]{11})",
    r"(?:youtube\.com/embed/)([\w-]{11})",
]


def extract_video_id(url: str) -> str:
    """
    Extract the 11-character YouTube video ID from a variety of URL formats:
    - https://www.youtube.com/watch?v=VIDEOID
    - https://youtu.be/VIDEOID
    - https://www.youtube.com/shorts/VIDEOID
    - https://www.youtube.com/embed/VIDEOID

    Raises InvalidYouTubeURLError if no valid ID can be found.
    """
    if not url or not isinstance(url, str):
        raise InvalidYouTubeURLError("Please enter a YouTube URL.")

    url = url.strip()

    for pattern in _YOUTUBE_ID_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # Fallback: maybe the user pasted just the raw 11-char video ID
    if re.fullmatch(r"[\w-]{11}", url):
        return url

    raise InvalidYouTubeURLError(
        "That doesn't look like a valid YouTube URL. "
        "Expected formats: https://www.youtube.com/watch?v=..., "
        "https://youtu.be/..., or https://www.youtube.com/shorts/..."
    )


# ---------------------------------------------------------------------------
# Metadata (video title / author) via the free oEmbed endpoint.
# This avoids needing yt-dlp/pytube just to fetch a title, keeping the
# project lightweight. No API key required.
# ---------------------------------------------------------------------------
def get_video_metadata(video_id: str) -> dict:
    """
    Fetch the video title and author using YouTube's public oEmbed endpoint.
    Returns a dict with 'title' and 'author'. Falls back to generic values
    if the request fails (this is metadata only, so it should never block
    the summarization flow).
    """
    oembed_url = (
        f"https://www.youtube.com/oembed?url="
        f"https://www.youtube.com/watch?v={video_id}&format=json"
    )
    try:
        response = requests.get(oembed_url, timeout=8)
        if response.status_code == 200:
            data = response.json()
            return {
                "title": data.get("title", "Unknown Title"),
                "author": data.get("author_name", "Unknown Channel"),
            }
        elif response.status_code == 401 or response.status_code == 400:
            # Typically means the video is private or otherwise restricted
            raise VideoNotAccessibleError(
                "This video appears to be private, age-restricted, or unavailable."
            )
    except requests.exceptions.RequestException:
        pass  # Non-fatal: metadata is a "nice to have"

    return {"title": "Unknown Title", "author": "Unknown Channel"}


# ---------------------------------------------------------------------------
# Transcript extraction
# ---------------------------------------------------------------------------
def get_transcript(video_id: str, languages=None) -> str:
    """
    Fetch transcript using the latest youtube-transcript-api (v1.x).
    """

    if languages is None:
        languages = ["en", "en-US", "en-GB"]

    api = YouTubeTranscriptApi()

    try:
        transcript_list = api.list(video_id)

        try:
            transcript = transcript_list.find_transcript(languages)
        except NoTranscriptFound:
            transcript = next(iter(transcript_list))

        fetched = transcript.fetch()

        text = " ".join(
            snippet.text
            for snippet in fetched
            if snippet.text.strip()
        )

        if not text:
            raise TranscriptNotAvailableError(
                "The transcript for this video is empty."
            )

        return text

    except TranscriptsDisabled:
        raise TranscriptNotAvailableError(
            "Captions/transcripts are disabled for this video."
        )

    except NoTranscriptFound:
        raise TranscriptNotAvailableError(
            "No transcript could be found for this video."
        )

    except VideoUnavailable:
        raise VideoNotAccessibleError(
            "This video is unavailable."
        )

    except Exception as exc:
        raise TranscriptNotAvailableError(
            f"Could not retrieve transcript ({exc})"
        )
