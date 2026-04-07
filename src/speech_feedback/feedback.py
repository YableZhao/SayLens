"""Generate human-readable pronunciation feedback."""
from __future__ import annotations

from dataclasses import dataclass

from speech_feedback.articulation import generate_articulation_html, get_articulatory_guidance
from speech_feedback.comparator import PhonemeComparison
from speech_feedback.scorer import PhonemeScore


@dataclass
class PhoneFeedback:
    """Feedback for a single phoneme position."""
    expected: str | None
    actual: str | None
    score: float          # 0-1 confidence
    quality: str          # "good", "fair", "poor"
    error_type: str | None  # "substitution", "insertion", "deletion", None
    suggestion: str
    articulatory_html: str | None = None  # SVG visualization HTML


# Common pronunciation tips by phoneme
PHONEME_TIPS: dict[str, str] = {
    "θ": "Place tongue tip between teeth and blow air gently.",
    "ð": "Like /θ/ but with voice; tongue between teeth, vibrate vocal cords.",
    "ɹ": "Curl tongue tip back slightly without touching the roof of mouth.",
    "ʃ": "Round lips slightly, tongue near the hard palate.",
    "ʒ": "Like /ʃ/ but voiced; add vocal cord vibration.",
    "æ": "Open mouth wide, tongue low and front.",
    "ɑ": "Open mouth wide, tongue low and back.",
    "ɪ": "Short, relaxed 'i' sound; tongue high and front but not tense.",
    "ʊ": "Short, relaxed 'u' sound; lips slightly rounded.",
    "ŋ": "Back of tongue touches soft palate; air through nose.",
}


class FeedbackGenerator:
    """Combine comparison and scoring results into user-facing feedback."""

    def generate(
        self,
        comparisons: list[PhonemeComparison],
        scores: list[PhonemeScore],
    ) -> list[PhoneFeedback]:
        """Merge comparison and score data into feedback items."""
        feedbacks = []
        score_idx = 0

        for comp in comparisons:
            if comp.match_type == "insertion":
                feedbacks.append(PhoneFeedback(
                    expected=None, actual=comp.actual,
                    score=0.0, quality="poor",
                    error_type="insertion",
                    suggestion=f"Extra sound /{comp.actual}/ detected; try to omit it.",
                ))
                continue

            # For correct/substitution/deletion, consume a score
            if score_idx < len(scores):
                sc = scores[score_idx]
                score_idx += 1
            else:
                sc = PhonemeScore(phoneme=comp.expected or "", gop_score=-10.0,
                                 confidence=0.0, quality="poor")

            if comp.match_type == "deletion":
                feedbacks.append(PhoneFeedback(
                    expected=comp.expected, actual=None,
                    score=sc.confidence, quality="poor",
                    error_type="deletion",
                    suggestion=f"Sound /{comp.expected}/ was not detected; make sure to pronounce it.",
                ))
            elif comp.match_type == "substitution":
                suggestion = get_articulatory_guidance(comp.expected or "", comp.actual or "")
                art_html = generate_articulation_html(comp.expected or "", comp.actual or "")
                feedbacks.append(PhoneFeedback(
                    expected=comp.expected, actual=comp.actual,
                    score=sc.confidence, quality=sc.quality,
                    error_type="substitution",
                    suggestion=suggestion,
                    articulatory_html=art_html if art_html else None,
                ))
            else:  # correct
                feedbacks.append(PhoneFeedback(
                    expected=comp.expected, actual=comp.actual,
                    score=sc.confidence, quality=sc.quality,
                    error_type=None,
                    suggestion="",
                ))

        return feedbacks

    def to_highlighted_text(
        self, feedbacks: list[PhoneFeedback]
    ) -> list[tuple[str, str | None]]:
        """Convert feedbacks to Gradio HighlightedText format.

        Returns list of (text, label) tuples where label maps to color.
        """
        result = []
        for fb in feedbacks:
            if fb.error_type == "insertion":
                result.append((f"+{fb.actual}", "insertion"))
            elif fb.error_type == "deletion":
                result.append((f"[{fb.expected}]", "missing"))
            else:
                display = fb.expected or fb.actual or "?"
                result.append((display, fb.quality))
        return result

    def to_articulatory_html(self, feedbacks: list[PhoneFeedback]) -> str:
        """Combine all articulatory visualizations into one HTML block."""
        parts = []
        for fb in feedbacks:
            if fb.articulatory_html:
                parts.append(fb.articulatory_html)
        if not parts:
            return ""
        return (
            '<div style="font-family:sans-serif;">'
            '<h3 style="color:#2D3748;margin-bottom:12px;">Articulation Guide</h3>'
            + "\n".join(parts)
            + '</div>'
        )

    def to_summary(self, feedbacks: list[PhoneFeedback]) -> str:
        """Generate a text summary of pronunciation feedback."""
        total = len(feedbacks)
        if total == 0:
            return "No phonemes to analyze."

        correct = sum(1 for f in feedbacks if f.error_type is None)
        accuracy = correct / total * 100

        lines = [f"**Overall accuracy: {accuracy:.0f}%** ({correct}/{total} phonemes correct)\n"]

        errors = [f for f in feedbacks if f.error_type is not None]
        if errors:
            lines.append("**Issues found:**\n")
            for fb in errors:
                if fb.error_type == "substitution":
                    lines.append(f"- /{fb.expected}/ → /{fb.actual}/ (substitution)")
                elif fb.error_type == "deletion":
                    lines.append(f"- /{fb.expected}/ missing (deletion)")
                elif fb.error_type == "insertion":
                    lines.append(f"- Extra /{fb.actual}/ (insertion)")

            lines.append("\n**Suggestions:**\n")
            for fb in errors:
                if fb.suggestion:
                    lines.append(f"- {fb.suggestion}")
        else:
            lines.append("Great job! All phonemes pronounced correctly.")

        return "\n".join(lines)
