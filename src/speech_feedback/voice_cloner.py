"""Voice cloning using XTTS v2 (Coqui TTS)."""
from __future__ import annotations

import os
import tempfile

import soundfile as sf


class VoiceCloner:
    """Generate speech in a cloned voice using XTTS v2.

    The model is lazily loaded on first use (~2GB download).
    """

    def __init__(self):
        self._tts = None

    def _load_model(self):
        """Load XTTS v2 model (downloads on first use)."""
        from TTS.api import TTS
        self._tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")

    def generate(self, text: str, speaker_wav: str, language: str = "en") -> str:
        """Generate speech in cloned voice.

        Args:
            text: Text to speak
            speaker_wav: Path to reference voice audio (>= 6 seconds)
            language: Language code (2-letter, e.g. "en", "fr", "de")

        Returns:
            Path to generated WAV file
        """
        if self._tts is None:
            self._load_model()

        # Map extended language codes
        lang = language.split("-")[0]

        output = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        output.close()

        self._tts.tts_to_file(
            text=text,
            speaker_wav=speaker_wav,
            language=lang,
            file_path=output.name,
        )
        return output.name

    def validate_reference(self, audio_path: str) -> tuple[bool, str]:
        """Check that reference audio is at least 6 seconds long."""
        try:
            data, sr = sf.read(audio_path)
            duration = len(data) / sr
            if duration < 6.0:
                return False, f"Reference audio is {duration:.1f}s. Need at least 6 seconds."
            return True, f"Reference audio: {duration:.1f}s (OK)"
        except Exception as e:
            return False, f"Could not read audio: {e}"

    @property
    def is_available(self) -> bool:
        """Check if TTS package is installed."""
        try:
            import TTS  # noqa: F401
            return True
        except ImportError:
            return False
