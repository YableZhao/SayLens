"""Goodness of Pronunciation (GOP) scoring from CTC posteriors."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from speech_feedback.aligner import AlignedPhone


@dataclass
class PhonemeScore:
    """GOP score and quality label for a single phoneme."""
    phoneme: str
    gop_score: float      # average log posterior of target phone over its frames
    confidence: float     # normalized 0-1 score
    quality: str          # "good", "fair", "poor"


class GOPScorer:
    """Compute per-phoneme Goodness of Pronunciation scores."""

    # Thresholds for quality classification (tunable)
    GOOD_THRESHOLD = -1.0
    FAIR_THRESHOLD = -3.0

    def score(
        self,
        posteriors: np.ndarray,
        aligned_phones: list[AlignedPhone],
        phone_to_idx: dict[str, int | None],
        total_frames: int,
        audio_duration_sec: float,
    ) -> list[PhonemeScore]:
        """Compute GOP scores for aligned phonemes.

        Args:
            posteriors: Softmax posterior matrix (T, V) from recognizer
            aligned_phones: Time-aligned phonemes from forced aligner
            phone_to_idx: Mapping from IPA phoneme to vocab index in posteriors
            total_frames: Total number of frames in posteriors
            audio_duration_sec: Duration of audio in seconds

        Returns:
            List of PhonemeScore, one per aligned phoneme
        """
        sec_per_frame = audio_duration_sec / total_frames if total_frames > 0 else 0.02
        results = []

        for ap in aligned_phones:
            # Convert time to frame indices
            start_frame = int(ap.start_sec / sec_per_frame)
            end_frame = int(ap.end_sec / sec_per_frame)
            start_frame = max(0, min(start_frame, total_frames - 1))
            end_frame = max(start_frame, min(end_frame, total_frames - 1))

            phone_idx = phone_to_idx.get(ap.phoneme)
            if phone_idx is None:
                # Can't score this phone - no matching vocab entry
                results.append(PhonemeScore(
                    phoneme=ap.phoneme, gop_score=-10.0,
                    confidence=0.0, quality="poor",
                ))
                continue

            # GOP = average log P(target_phone | frame) over duration
            frame_range = posteriors[start_frame:end_frame + 1, phone_idx]
            if len(frame_range) == 0:
                gop = -10.0
            else:
                # Clamp to avoid log(0)
                frame_range = np.clip(frame_range, 1e-10, 1.0)
                gop = float(np.mean(np.log(frame_range)))

            confidence = self._gop_to_confidence(gop)
            quality = self._classify(gop)
            results.append(PhonemeScore(
                phoneme=ap.phoneme, gop_score=gop,
                confidence=confidence, quality=quality,
            ))

        return results

    def _gop_to_confidence(self, gop: float) -> float:
        """Map GOP score to 0-1 confidence using sigmoid."""
        return float(1.0 / (1.0 + np.exp(-(gop + 2.0))))

    def _classify(self, gop: float) -> str:
        if gop >= self.GOOD_THRESHOLD:
            return "good"
        elif gop >= self.FAIR_THRESHOLD:
            return "fair"
        return "poor"
