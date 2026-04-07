"""Forced alignment using wav2vec2 CTC emissions + torchaudio forced_align."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
import torchaudio
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

from speech_feedback.recognizer import MODEL_ID, SAMPLE_RATE


@dataclass
class AlignedPhone:
    """A single phoneme with timing and alignment score."""
    phoneme: str
    start_sec: float
    end_sec: float
    score: float  # alignment confidence from CTC


class ForcedAligner:
    """Phoneme-level forced alignment using wav2vec2-xlsr CTC emissions.

    Shares the same model/vocab as PhonemeRecognizer to avoid phoneme set mismatches.
    """

    def __init__(self, model=None, processor=None, device: str = "cpu"):
        self.device = device
        if model is not None and processor is not None:
            self.model = model
            self.processor = processor
        else:
            self.processor = Wav2Vec2Processor.from_pretrained(MODEL_ID)
            self.model = Wav2Vec2ForCTC.from_pretrained(MODEL_ID).to(device)
            self.model.eval()

        self.vocab = self.processor.tokenizer.get_vocab()
        self._pad_id = self.processor.tokenizer.pad_token_id

    def align(
        self, waveform: torch.Tensor, sample_rate: int, phones: list[str]
    ) -> list[AlignedPhone]:
        """Align audio to a phoneme sequence using CTC forced alignment.

        Args:
            waveform: Audio tensor of shape (1, T) or (T,)
            sample_rate: Sample rate of the waveform
            phones: List of IPA phoneme strings (from G2P)

        Returns:
            List of AlignedPhone with timing and scores
        """
        if waveform.dim() == 1:
            waveform = waveform.unsqueeze(0)

        # Resample to 16kHz if needed
        if sample_rate != SAMPLE_RATE:
            waveform = torchaudio.functional.resample(
                waveform, orig_freq=sample_rate, new_freq=SAMPLE_RATE
            )

        audio_duration = waveform.shape[1] / SAMPLE_RATE

        # Get CTC emissions (log probabilities)
        waveform_np = waveform.squeeze(0).numpy()
        inputs = self.processor(
            waveform_np, sampling_rate=SAMPLE_RATE, return_tensors="pt", padding=True
        )
        input_values = inputs.input_values.to(self.device)

        with torch.no_grad():
            logits = self.model(input_values).logits

        # Log softmax for forced_align
        log_probs = torch.nn.functional.log_softmax(logits, dim=-1)

        # Map phones to token indices, skipping unknown ones
        valid_phones = []
        token_ids = []
        for p in phones:
            idx = self.vocab.get(p)
            if idx is not None and idx != self._pad_id:
                valid_phones.append(p)
                token_ids.append(idx)

        if not token_ids:
            return []

        # Run CTC forced alignment
        targets = torch.tensor([token_ids], dtype=torch.int32, device=self.device)
        try:
            aligned_tokens, scores = torchaudio.functional.forced_align(
                log_probs, targets, blank=self._pad_id
            )
        except Exception:
            # Fallback: if forced_align fails, return empty
            return []

        aligned_tokens = aligned_tokens[0]
        scores = scores[0]

        # Merge tokens into phone segments
        num_frames = log_probs.shape[1]
        sec_per_frame = audio_duration / num_frames if num_frames > 0 else 0.02

        segments = self._merge_to_phones(aligned_tokens, scores, valid_phones, sec_per_frame)
        return segments

    def _merge_to_phones(
        self,
        aligned_tokens: torch.Tensor,
        scores: torch.Tensor,
        phones: list[str],
        sec_per_frame: float,
    ) -> list[AlignedPhone]:
        """Merge CTC frame-level alignment into phone-level segments."""
        results = []
        phone_idx = 0
        cur_start = None
        cur_scores: list[float] = []

        for i in range(len(aligned_tokens)):
            tok = aligned_tokens[i].item()
            sc = scores[i].item()

            if tok == self._pad_id:
                # Blank frame
                if cur_start is not None and phone_idx < len(phones):
                    avg_score = sum(cur_scores) / len(cur_scores) if cur_scores else 0.0
                    results.append(AlignedPhone(
                        phoneme=phones[phone_idx],
                        start_sec=cur_start * sec_per_frame,
                        end_sec=(i - 1) * sec_per_frame,
                        score=avg_score,
                    ))
                    phone_idx += 1
                    cur_start = None
                    cur_scores = []
                continue

            if cur_start is None:
                cur_start = i
                cur_scores = [sc]
            else:
                cur_scores.append(sc)

            # Check if next frame is a different token
            is_last = (i == len(aligned_tokens) - 1)
            next_different = (not is_last and aligned_tokens[i + 1].item() != tok)

            if is_last or next_different:
                if phone_idx < len(phones):
                    avg_score = sum(cur_scores) / len(cur_scores) if cur_scores else 0.0
                    results.append(AlignedPhone(
                        phoneme=phones[phone_idx],
                        start_sec=cur_start * sec_per_frame,
                        end_sec=i * sec_per_frame,
                        score=avg_score,
                    ))
                    phone_idx += 1
                cur_start = None
                cur_scores = []

        return results

    def get_vocab_phones(self) -> list[str]:
        """Return phonemes supported by this aligner (same as recognizer vocab)."""
        return list(self.vocab.keys())
