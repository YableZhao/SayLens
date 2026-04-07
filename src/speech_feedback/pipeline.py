"""Orchestrator: ties all modules into a single pronunciation analysis pipeline."""
from __future__ import annotations

import numpy as np
import soundfile as sf
import torch
import torchaudio

from speech_feedback.aligner import ForcedAligner
from speech_feedback.comparator import PhonemeComparator
from speech_feedback.feedback import FeedbackGenerator
from speech_feedback.g2p import G2PConverter
from speech_feedback.recognizer import PhonemeRecognizer
from speech_feedback.scorer import GOPScorer


class PronunciationPipeline:
    """End-to-end pronunciation analysis pipeline.

    Takes audio + target text, outputs phoneme-level feedback.
    """

    def __init__(self, language: str = "en-us", device: str = "cpu"):
        self.language = language
        self.device = device

        self.g2p = G2PConverter(language)

        # Recognizer loads the wav2vec2 model
        self.recognizer = PhonemeRecognizer(device)

        # Aligner shares the same model to avoid phoneme set mismatches
        self.aligner = ForcedAligner(
            model=self.recognizer.model,
            processor=self.recognizer.processor,
            device=device,
        )

        self.scorer = GOPScorer()
        self.comparator = PhonemeComparator()
        self.feedback_gen = FeedbackGenerator()

    def analyze(self, audio_path: str, target_text: str) -> dict:
        """Run full pronunciation analysis.

        Args:
            audio_path: Path to audio file (WAV, MP3, etc.)
            target_text: The text the user intended to say

        Returns:
            Dict with keys: highlighted_text, summary, accuracy,
                            expected_ipa, actual_ipa, details
        """
        # 1. Load audio
        audio_np, sample_rate = sf.read(audio_path, dtype="float32")
        if audio_np.ndim > 1:
            audio_np = audio_np.mean(axis=1)  # mono
        waveform = torch.from_numpy(audio_np).unsqueeze(0)  # (1, T)
        audio_duration = waveform.shape[1] / sample_rate

        # 2. G2P: text -> expected IPA phonemes
        expected_phones = self.g2p.convert(target_text)
        if not expected_phones:
            return self._empty_result("Could not convert text to phonemes.")

        # 3. Forced alignment: audio + expected phones -> timed segments
        aligned_phones = self.aligner.align(waveform, sample_rate, expected_phones)

        # 4. Phoneme recognition: audio -> actual phonemes + posteriors
        waveform_np = waveform.squeeze(0).numpy()
        if sample_rate != 16000:
            resampled = torchaudio.functional.resample(waveform, sample_rate, 16000)
            waveform_np = resampled.squeeze(0).numpy()

        actual_phones = self.recognizer.recognize(waveform_np, 16000)
        posteriors = self.recognizer.get_posteriors(waveform_np, 16000)

        # 5. GOP scoring (using posteriors + alignment timing)
        phone_to_idx = {}
        for p in set(expected_phones):
            idx = self.recognizer.get_phone_index(p)
            if idx is not None:
                phone_to_idx[p] = idx

        scores = self.scorer.score(
            posteriors, aligned_phones, phone_to_idx,
            total_frames=posteriors.shape[0],
            audio_duration_sec=audio_duration,
        )

        # 6. Compare expected vs actual
        comparisons = self.comparator.compare(expected_phones, actual_phones)

        # 7. Generate feedback
        feedbacks = self.feedback_gen.generate(comparisons, scores)
        highlighted = self.feedback_gen.to_highlighted_text(feedbacks)
        summary = self.feedback_gen.to_summary(feedbacks)
        articulatory_html = self.feedback_gen.to_articulatory_html(feedbacks)
        accuracy = self.comparator.accuracy(comparisons) * 100

        return {
            "highlighted_text": highlighted,
            "summary": summary,
            "articulatory_html": articulatory_html,
            "accuracy": round(accuracy, 1),
            "expected_ipa": " ".join(expected_phones),
            "actual_ipa": " ".join(actual_phones),
            "details": feedbacks,
        }

    def _empty_result(self, message: str) -> dict:
        return {
            "highlighted_text": [],
            "summary": message,
            "accuracy": 0.0,
            "expected_ipa": "",
            "actual_ipa": "",
            "details": [],
        }
