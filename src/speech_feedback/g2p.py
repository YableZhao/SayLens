"""Grapheme-to-phoneme conversion using phonemizer (espeak-ng backend)."""
from __future__ import annotations

import re
from functools import lru_cache

from phonemizer import phonemize
from phonemizer.separator import Separator


class G2PConverter:
    """Convert text to IPA phoneme sequences using espeak-ng."""

    def __init__(self, language: str = "en-us"):
        self.language = language
        self._separator = Separator(phone=" ", word="  ", syllable="")

    def convert(self, text: str) -> list[str]:
        """Convert text to a list of IPA phoneme tokens."""
        text = text.strip()
        if not text:
            return []

        raw = phonemize(
            text,
            language=self.language,
            backend="espeak",
            separator=self._separator,
            strip=True,
            preserve_punctuation=False,
            with_stress=False,
        )
        # Split by space, filter empties
        phones = [p for p in raw.split() if p]
        return phones

    def convert_to_string(self, text: str) -> str:
        """Convert text to an IPA string (phones separated by spaces)."""
        return " ".join(self.convert(text))


@lru_cache(maxsize=1)
def get_default_g2p() -> G2PConverter:
    """Get a cached default English G2P converter."""
    return G2PConverter("en-us")
