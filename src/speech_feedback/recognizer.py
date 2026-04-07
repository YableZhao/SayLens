"""Phoneme recognition using wav2vec2-xlsr-53-espeak-cv-ft."""
from __future__ import annotations

import numpy as np
import torch
import torchaudio
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor


MODEL_ID = "facebook/wav2vec2-xlsr-53-espeak-cv-ft"
SAMPLE_RATE = 16000


class PhonemeRecognizer:
    """IPA phoneme recognition from audio using wav2vec2."""

    def __init__(self, device: str = "cpu"):
        self.device = device
        self.processor = Wav2Vec2Processor.from_pretrained(MODEL_ID)
        self.model = Wav2Vec2ForCTC.from_pretrained(MODEL_ID).to(device)
        self.model.eval()
        # Build phoneme-to-index mapping
        self.vocab = self.processor.tokenizer.get_vocab()
        self.idx_to_phone = {v: k for k, v in self.vocab.items()}

    def recognize(self, waveform: np.ndarray, sample_rate: int = SAMPLE_RATE) -> list[str]:
        """Recognize IPA phonemes from audio.

        Args:
            waveform: Audio as 1D numpy float array
            sample_rate: Sample rate (should be 16000)

        Returns:
            List of recognized IPA phoneme strings
        """
        logits = self._get_logits(waveform, sample_rate)
        pred_ids = torch.argmax(logits, dim=-1)[0]

        # CTC decode: collapse blanks and repeats
        phones = []
        prev_id = -1
        blank_id = self.processor.tokenizer.pad_token_id
        for idx in pred_ids:
            idx = idx.item()
            if idx == blank_id or idx == prev_id:
                prev_id = idx
                continue
            phone = self.idx_to_phone.get(idx, "")
            if phone and phone not in ("<s>", "</s>", "<pad>", "<unk>", "|"):
                phones.append(phone)
            prev_id = idx

        return phones

    def get_posteriors(self, waveform: np.ndarray, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
        """Get full softmax posterior matrix from audio.

        Args:
            waveform: Audio as 1D numpy float array
            sample_rate: Sample rate

        Returns:
            Posterior matrix of shape (T, V) where T=frames, V=vocab size
        """
        logits = self._get_logits(waveform, sample_rate)
        probs = torch.nn.functional.softmax(logits[0], dim=-1)
        return probs.cpu().numpy()

    def _resample(self, waveform: np.ndarray, sample_rate: int) -> np.ndarray:
        """Resample audio to 16kHz if needed."""
        if sample_rate != SAMPLE_RATE:
            waveform_t = torch.from_numpy(waveform).unsqueeze(0)
            resampled = torchaudio.functional.resample(waveform_t, sample_rate, SAMPLE_RATE)
            return resampled.squeeze(0).numpy()
        return waveform

    def _get_logits(self, waveform: np.ndarray, sample_rate: int) -> torch.Tensor:
        """Run model forward pass and return logits."""
        waveform = self._resample(waveform, sample_rate)
        inputs = self.processor(
            waveform, sampling_rate=SAMPLE_RATE, return_tensors="pt", padding=True
        )
        input_values = inputs.input_values.to(self.device)

        with torch.no_grad():
            outputs = self.model(input_values)
        return outputs.logits

    def get_phone_index(self, phone: str) -> int | None:
        """Get vocab index for a phoneme, or None if not in vocab."""
        return self.vocab.get(phone)
