"""Text-to-speech service powered by the free `edge-tts` engine.

Improvements applied:
- IDEA-01  : list_voices() returns a pre-built constant (O(1), no allocation per call)
- IDEA-09  : Long texts are split at sentence boundaries and synthesised in parallel
- IDEA-26  : Input text is preprocessed (HTML stripped, URLs replaced, whitespace normalised)
- IDEA-25  : SSML mode bypasses preprocessing when the caller opts in
"""

import asyncio
import html
import re
import uuid
from pathlib import Path

import edge_tts

from app.config import settings
from app.schemas.tts import VoiceOut


class TTSError(Exception):
    """Raised when speech synthesis fails."""


# ── Text utilities ────────────────────────────────────────────────────────────

def _preprocess(text: str) -> str:
    """Clean HTML entities/tags, URLs, and extra whitespace — IDEA-26."""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", "", text)                    # strip HTML tags
    text = re.sub(r"https?://\S+", "رابط", text)           # replace URLs
    text = re.sub(r"[^\S\n]+", " ", text)                  # collapse inline spaces
    text = re.sub(r"\n{3,}", "\n\n", text)                 # max two consecutive newlines
    return text.strip()


def _split_into_chunks(text: str, max_chars: int = 900) -> list[str]:
    """Split at sentence boundaries so each chunk ≤ max_chars — IDEA-09."""
    if len(text) <= max_chars:
        return [text]

    # Split on Arabic and Latin sentence-ending punctuation
    pieces = re.split(r"(?<=[.!?؟\n])\s*", text)
    chunks: list[str] = []
    current = ""

    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue
        if len(current) + len(piece) + 1 <= max_chars:
            current = (current + " " + piece).strip()
        else:
            if current:
                chunks.append(current)
            # A single sentence longer than max_chars: keep it whole
            current = piece

    if current:
        chunks.append(current)

    return chunks or [text]


# ── Preview sample texts — IDEA-07 ──────────────────────────────────────────

_PREVIEW_SAMPLES: dict[str, str] = {
    "ar": "مرحباً! هذا مثال على صوتي. كيف تجدني؟",
    "en": "Hello! This is a quick sample of my voice. How do I sound?",
    "fr": "Bonjour! Voici un exemple de ma voix.",
    "es": "¡Hola! Este es un ejemplo de mi voz.",
    "de": "Hallo! Dies ist ein Beispiel meiner Stimme.",
}


def _preview_text_for_voice(voice_id: str, user_text: str) -> str:
    """Return a short preview text: user's own text (≤100 chars) or a sample."""
    if user_text.strip():
        words = user_text.split()[:15]
        return " ".join(words)
    locale = voice_id.split("-")[0].lower()
    return _PREVIEW_SAMPLES.get(locale, _PREVIEW_SAMPLES["en"])


# ── Service ───────────────────────────────────────────────────────────────────

class TTSService:
    """Synthesize speech and list available voices."""

    # Built once at import time — returned as-is by list_voices() — IDEA-01
    CURATED_VOICES: list[VoiceOut] = [
        VoiceOut(id="en-US-GuyNeural",    name="Guy",              locale="en-US", gender="Male"),
        VoiceOut(id="en-US-JennyNeural",  name="Jenny",            locale="en-US", gender="Female"),
        VoiceOut(id="en-US-AriaNeural",   name="Aria",             locale="en-US", gender="Female"),
        VoiceOut(id="en-GB-RyanNeural",   name="Ryan (UK)",        locale="en-GB", gender="Male"),
        VoiceOut(id="en-GB-SoniaNeural",  name="Sonia (UK)",       locale="en-GB", gender="Female"),
        VoiceOut(id="ar-EG-SalmaNeural",  name="سلمى (مصر)",       locale="ar-EG", gender="Female"),
        VoiceOut(id="ar-EG-ShakirNeural", name="شاكر (مصر)",       locale="ar-EG", gender="Male"),
        VoiceOut(id="ar-SA-ZariyahNeural",name="زارية (السعودية)", locale="ar-SA", gender="Female"),
        VoiceOut(id="ar-SA-HamedNeural",  name="حامد (السعودية)",  locale="ar-SA", gender="Male"),
        VoiceOut(id="fr-FR-DeniseNeural", name="Denise (FR)",      locale="fr-FR", gender="Female"),
        VoiceOut(id="es-ES-AlvaroNeural", name="Álvaro (ES)",      locale="es-ES", gender="Male"),
        VoiceOut(id="de-DE-KatjaNeural",  name="Katja (DE)",       locale="de-DE", gender="Female"),
    ]

    def __init__(self, output_dir: str = settings.audio_output_dir) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def list_voices(self) -> list[VoiceOut]:
        """Return the curated list (already built at import, O(1))."""
        return self.CURATED_VOICES

    def is_valid_voice(self, voice: str) -> bool:
        return any(v.id == voice for v in self.CURATED_VOICES)

    # ── Core synthesis ────────────────────────────────────────────────────────

    async def _synthesize_chunk(
        self,
        text: str,
        voice: str,
        rate: str,
        volume: str,
    ) -> Path:
        """Synthesize a single text chunk and return its MP3 path."""
        filename = f"{uuid.uuid4().hex}.mp3"
        filepath = self.output_dir / filename
        try:
            comm = edge_tts.Communicate(text=text, voice=voice, rate=rate, volume=volume)
            await comm.save(str(filepath))
        except Exception as exc:
            raise TTSError(f"Speech synthesis failed: {exc}") from exc
        if not filepath.exists() or filepath.stat().st_size == 0:
            raise TTSError("Speech synthesis produced no audio.")
        return filepath

    async def synthesize(
        self,
        text: str,
        voice: str = "en-US-GuyNeural",
        rate: str = "+0%",
        volume: str = "+0%",
        ssml: bool = False,
    ) -> Path:
        """Convert text to an MP3 and return its path.

        Long texts are automatically split and synthesised in parallel (IDEA-09).
        Input is preprocessed unless ssml=True (IDEA-25, IDEA-26).
        """
        if not ssml:
            text = _preprocess(text)

        if not text:
            raise TTSError("النص فارغ.")

        if not self.is_valid_voice(voice):
            raise TTSError(f"صوت غير مدعوم: {voice}")

        chunks = _split_into_chunks(text)

        if len(chunks) == 1:
            return await self._synthesize_chunk(text, voice, rate, volume)

        # Parallel synthesis — IDEA-09
        tasks = [self._synthesize_chunk(c, voice, rate, volume) for c in chunks]
        chunk_paths = await asyncio.gather(*tasks)

        # Merge chunks by byte-concatenation (valid for CBR MP3 streams)
        merged_path = self.output_dir / f"{uuid.uuid4().hex}.mp3"
        with open(merged_path, "wb") as out:
            for cp in chunk_paths:
                if cp.exists():
                    out.write(cp.read_bytes())
                    cp.unlink(missing_ok=True)

        return merged_path

    async def preview(
        self,
        voice: str = "en-US-GuyNeural",
        user_text: str = "",
    ) -> Path:
        """Synthesize a short preview clip for voice selection — IDEA-07."""
        sample = _preview_text_for_voice(voice, user_text)
        return await self._synthesize_chunk(sample, voice, "+0%", "+0%")


# Shared instance.
tts_service = TTSService()
