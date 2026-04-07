"""Articulatory features database, SVG diagram generation, and pronunciation guidance."""
from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# 1. Articulatory feature database
# ---------------------------------------------------------------------------

@dataclass
class ArticulatoryFeatures:
    """Phonetic features for a single IPA phoneme."""
    place: str        # bilabial, labiodental, dental, alveolar, postalveolar, palatal, velar, glottal
    manner: str       # plosive, nasal, fricative, affricate, approximant, lateral, trill
    voicing: str      # voiced, voiceless
    is_vowel: bool = False
    height: str | None = None      # close, close-mid, open-mid, open
    backness: str | None = None    # front, central, back
    rounding: str | None = None    # rounded, unrounded


def _v(height, backness, rounding="unrounded"):
    """Shorthand for vowel features."""
    return ArticulatoryFeatures(
        place="", manner="vowel", voicing="voiced",
        is_vowel=True, height=height, backness=backness, rounding=rounding,
    )


def _c(place, manner, voicing):
    """Shorthand for consonant features."""
    return ArticulatoryFeatures(place=place, manner=manner, voicing=voicing)


IPA_FEATURES: dict[str, ArticulatoryFeatures] = {
    # --- Plosives ---
    "p": _c("bilabial", "plosive", "voiceless"),
    "b": _c("bilabial", "plosive", "voiced"),
    "t": _c("alveolar", "plosive", "voiceless"),
    "d": _c("alveolar", "plosive", "voiced"),
    "k": _c("velar", "plosive", "voiceless"),
    "ɡ": _c("velar", "plosive", "voiced"),
    "g": _c("velar", "plosive", "voiced"),
    "ʔ": _c("glottal", "plosive", "voiceless"),
    # --- Nasals ---
    "m": _c("bilabial", "nasal", "voiced"),
    "n": _c("alveolar", "nasal", "voiced"),
    "ŋ": _c("velar", "nasal", "voiced"),
    # --- Fricatives ---
    "f": _c("labiodental", "fricative", "voiceless"),
    "v": _c("labiodental", "fricative", "voiced"),
    "θ": _c("dental", "fricative", "voiceless"),
    "ð": _c("dental", "fricative", "voiced"),
    "s": _c("alveolar", "fricative", "voiceless"),
    "z": _c("alveolar", "fricative", "voiced"),
    "ʃ": _c("postalveolar", "fricative", "voiceless"),
    "ʒ": _c("postalveolar", "fricative", "voiced"),
    "h": _c("glottal", "fricative", "voiceless"),
    # --- Affricates ---
    "tʃ": _c("postalveolar", "affricate", "voiceless"),
    "dʒ": _c("postalveolar", "affricate", "voiced"),
    # --- Approximants ---
    "ɹ": _c("alveolar", "approximant", "voiced"),
    "j": _c("palatal", "approximant", "voiced"),
    "w": _c("bilabial", "approximant", "voiced"),
    "l": _c("alveolar", "lateral", "voiced"),
    "ɫ": _c("alveolar", "lateral", "voiced"),
    "ɾ": _c("alveolar", "trill", "voiced"),
    "r": _c("alveolar", "trill", "voiced"),
    # --- Vowels ---
    "i": _v("close", "front"),
    "iː": _v("close", "front"),
    "ɪ": _v("close", "front"),
    "e": _v("close-mid", "front"),
    "eɪ": _v("close-mid", "front"),
    "ɛ": _v("open-mid", "front"),
    "æ": _v("open", "front"),
    "ə": _v("mid", "central"),
    "ɜ": _v("open-mid", "central"),
    "ɜː": _v("open-mid", "central"),
    "ʌ": _v("open-mid", "back"),
    "ɑ": _v("open", "back"),
    "ɑː": _v("open", "back"),
    "ɒ": _v("open", "back", "rounded"),
    "ɔ": _v("open-mid", "back", "rounded"),
    "ɔː": _v("open-mid", "back", "rounded"),
    "ɔɪ": _v("open-mid", "back", "rounded"),
    "o": _v("close-mid", "back", "rounded"),
    "oː": _v("close-mid", "back", "rounded"),
    "oʊ": _v("close-mid", "back", "rounded"),
    "u": _v("close", "back", "rounded"),
    "uː": _v("close", "back", "rounded"),
    "ʊ": _v("close", "back", "rounded"),
    "aɪ": _v("open", "front"),
    "aʊ": _v("open", "back"),
}


# ---------------------------------------------------------------------------
# 2. SVG diagram generation
# ---------------------------------------------------------------------------

# Tongue tip target positions for each place of articulation
# Format: (tip_x, tip_y) relative to the SVG coordinate system (300x250)
_TONGUE_POSITIONS: dict[str, tuple[int, int, int, int]] = {
    # (tip_x, tip_y, body_raise_x, body_raise_y)
    "bilabial":     (85, 115, 130, 170),
    "labiodental":  (90, 108, 130, 165),
    "dental":       (100, 95, 135, 160),
    "alveolar":     (115, 85, 140, 155),
    "postalveolar": (130, 78, 145, 145),
    "palatal":      (150, 75, 155, 130),
    "velar":        (175, 90, 175, 120),
    "glottal":      (140, 140, 200, 140),
}

# Contact zone highlight positions
_CONTACT_ZONES: dict[str, tuple[int, int, int, int]] = {
    # (x, y, width, height) of the highlighted contact region
    "bilabial":     (68, 105, 25, 25),
    "labiodental":  (78, 92, 20, 22),
    "dental":       (88, 78, 20, 25),
    "alveolar":     (105, 65, 22, 22),
    "postalveolar": (125, 58, 22, 20),
    "palatal":      (148, 55, 25, 18),
    "velar":        (178, 60, 25, 22),
    "glottal":      (215, 130, 20, 25),
}


def _svg_sagittal_base() -> str:
    """Return the static parts of the sagittal cross-section SVG."""
    return """
    <!-- Oral cavity outline -->
    <path d="M 70 130 Q 70 100 85 85 Q 100 70 120 60 Q 150 48 180 50 Q 210 55 230 75 Q 245 90 250 120 L 250 200 L 230 210"
          fill="none" stroke="#666" stroke-width="2.5" />
    <!-- Upper lip -->
    <path d="M 60 135 Q 65 125 70 130" fill="none" stroke="#888" stroke-width="2.5" />
    <!-- Lower lip -->
    <path d="M 60 140 Q 65 150 75 148" fill="none" stroke="#888" stroke-width="2.5" />
    <!-- Upper teeth -->
    <rect x="80" y="88" width="8" height="18" rx="2" fill="#ddd" stroke="#aaa" stroke-width="1" />
    <!-- Lower teeth -->
    <rect x="82" y="118" width="7" height="16" rx="2" fill="#ddd" stroke="#aaa" stroke-width="1" />
    <!-- Nose -->
    <path d="M 60 130 L 50 120 L 50 80 Q 52 70 60 65" fill="none" stroke="#999" stroke-width="1.5" />
    <!-- Pharynx wall -->
    <path d="M 240 90 Q 248 130 245 170 Q 243 200 235 220" fill="none" stroke="#666" stroke-width="2" />
    <!-- Velum (soft palate) -->
    <path d="M 195 55 Q 210 60 220 75 Q 225 85 225 95" fill="none" stroke="#888" stroke-width="2" stroke-dasharray="4,3" />
    """


def generate_sagittal_svg(
    phoneme: str,
    features: ArticulatoryFeatures | None = None,
    color: str = "#E53E3E",
    label: str = "",
    width: int = 300,
    height: int = 260,
) -> str:
    """Generate a sagittal cross-section SVG for a consonant phoneme.

    Shows the vocal tract with tongue position and contact zone highlighted.
    """
    if features is None:
        features = IPA_FEATURES.get(phoneme)
    if features is None or features.is_vowel:
        return ""

    place = features.place
    tip = _TONGUE_POSITIONS.get(place, (130, 120, 160, 155))
    zone = _CONTACT_ZONES.get(place, None)

    tip_x, tip_y, body_x, body_y = tip

    svg = f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
    svg += f'width="{width}" height="{height}" style="background:#fafafa;border-radius:8px;">\n'

    # Base anatomy
    svg += _svg_sagittal_base()

    # Contact zone highlight
    if zone:
        zx, zy, zw, zh = zone
        svg += f'  <ellipse cx="{zx + zw//2}" cy="{zy + zh//2}" rx="{zw//2 + 4}" ry="{zh//2 + 4}" '
        svg += f'fill="{color}" opacity="0.25" />\n'
        svg += f'  <ellipse cx="{zx + zw//2}" cy="{zy + zh//2}" rx="{zw//2}" ry="{zh//2}" '
        svg += f'fill="{color}" opacity="0.4" />\n'

    # Tongue
    svg += f'  <path d="M 200 210 Q {body_x + 20} {body_y + 30} {body_x} {body_y} '
    svg += f'Q {(tip_x + body_x)//2} {(tip_y + body_y)//2 - 5} {tip_x} {tip_y}" '
    svg += f'fill="none" stroke="{color}" stroke-width="3.5" stroke-linecap="round" />\n'

    # Tongue tip dot
    svg += f'  <circle cx="{tip_x}" cy="{tip_y}" r="4" fill="{color}" />\n'

    # Arrow pointing to contact
    if zone:
        ax = zone[0] + zone[2] // 2
        ay = zone[1] + zone[3] + 15
        svg += f'  <line x1="{ax}" y1="{ay + 20}" x2="{ax}" y2="{ay}" '
        svg += f'stroke="{color}" stroke-width="2" marker-end="url(#arrowhead-{color.replace("#", "")})" />\n'
        svg += f'  <defs><marker id="arrowhead-{color.replace("#", "")}" markerWidth="8" markerHeight="6" '
        svg += f'refX="8" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{color}" /></marker></defs>\n'

    # Labels
    if label:
        svg += f'  <text x="{width//2}" y="22" text-anchor="middle" font-size="14" '
        svg += f'font-family="sans-serif" fill="#333" font-weight="bold">{label}</text>\n'

    # Phoneme label
    svg += f'  <text x="{width//2}" y="{height - 8}" text-anchor="middle" font-size="18" '
    svg += f'font-family="serif" fill="{color}" font-weight="bold">/{phoneme}/</text>\n'

    # Place label
    svg += f'  <text x="{width//2}" y="{height - 25}" text-anchor="middle" font-size="11" '
    svg += f'font-family="sans-serif" fill="#888">{place} {features.manner}</text>\n'

    svg += '</svg>'
    return svg


def generate_vowel_chart_svg(
    phoneme: str,
    features: ArticulatoryFeatures | None = None,
    color: str = "#E53E3E",
    width: int = 280,
    height: int = 220,
) -> str:
    """Generate an IPA vowel quadrilateral with the target vowel marked."""
    if features is None:
        features = IPA_FEATURES.get(phoneme)
    if features is None or not features.is_vowel:
        return ""

    # Vowel chart coordinates: trapezoid
    # front-close, back-close, front-open, back-open
    margin_x, margin_y = 50, 40
    chart_w = width - 2 * margin_x
    chart_h = height - 2 * margin_y

    # Trapezoid corners
    fc = (margin_x + 20, margin_y)            # front-close
    bc = (margin_x + chart_w, margin_y)        # back-close
    fo = (margin_x, margin_y + chart_h)        # front-open
    bo = (margin_x + chart_w - 20, margin_y + chart_h)  # back-open

    # Map features to position
    backness_map = {"front": 0.0, "central": 0.5, "back": 1.0}
    height_map = {"close": 0.0, "close-mid": 0.33, "mid": 0.5, "open-mid": 0.67, "open": 1.0}

    bk = backness_map.get(features.backness or "central", 0.5)
    ht = height_map.get(features.height or "mid", 0.5)

    # Interpolate position on the trapezoid
    left_x = fo[0] + (fc[0] - fo[0]) * (1 - ht)
    left_y = fo[1] + (fc[1] - fo[1]) * (1 - ht)
    right_x = bo[0] + (bc[0] - bo[0]) * (1 - ht)
    right_y = bo[1] + (bc[1] - bo[1]) * (1 - ht)
    dot_x = left_x + (right_x - left_x) * bk
    dot_y = left_y + (right_y - left_y) * bk

    svg = f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
    svg += f'width="{width}" height="{height}" style="background:#fafafa;border-radius:8px;">\n'

    # Trapezoid outline
    svg += f'  <polygon points="{fc[0]},{fc[1]} {bc[0]},{bc[1]} {bo[0]},{bo[1]} {fo[0]},{fo[1]}" '
    svg += f'fill="none" stroke="#ccc" stroke-width="1.5" />\n'

    # Height lines
    for label, frac in [("close-mid", 0.33), ("mid", 0.5), ("open-mid", 0.67)]:
        lx = fo[0] + (fc[0] - fo[0]) * (1 - frac)
        ly = fo[1] + (fc[1] - fo[1]) * (1 - frac)
        rx = bo[0] + (bc[0] - bo[0]) * (1 - frac)
        ry = bo[1] + (bc[1] - bo[1]) * (1 - frac)
        svg += f'  <line x1="{lx}" y1="{ly}" x2="{rx}" y2="{ry}" stroke="#eee" stroke-width="1" />\n'

    # Axis labels
    svg += f'  <text x="{fc[0] - 5}" y="{fc[1] - 5}" font-size="10" fill="#999" text-anchor="end">Close</text>\n'
    svg += f'  <text x="{fo[0] - 5}" y="{fo[1] + 12}" font-size="10" fill="#999" text-anchor="end">Open</text>\n'
    svg += f'  <text x="{(fc[0]+fo[0])//2}" y="{margin_y - 15}" font-size="10" fill="#999" text-anchor="middle">Front</text>\n'
    svg += f'  <text x="{(bc[0]+bo[0])//2}" y="{margin_y - 15}" font-size="10" fill="#999" text-anchor="middle">Back</text>\n'

    # Target dot
    svg += f'  <circle cx="{dot_x}" cy="{dot_y}" r="10" fill="{color}" opacity="0.3" />\n'
    svg += f'  <circle cx="{dot_x}" cy="{dot_y}" r="5" fill="{color}" />\n'
    svg += f'  <text x="{dot_x + 14}" y="{dot_y + 5}" font-size="14" font-family="serif" '
    svg += f'fill="{color}" font-weight="bold">/{phoneme}/</text>\n'

    # Rounding indicator
    r = features.rounding or "unrounded"
    svg += f'  <text x="{width//2}" y="{height - 5}" text-anchor="middle" font-size="10" '
    svg += f'fill="#888">lips: {r}</text>\n'

    svg += '</svg>'
    return svg


def generate_comparison_svg(expected: str, actual: str) -> str:
    """Generate side-by-side comparison of expected vs actual articulation."""
    feat_exp = IPA_FEATURES.get(expected)
    feat_act = IPA_FEATURES.get(actual)

    if feat_exp is None and feat_act is None:
        return ""

    parts = ['<div style="display:flex;gap:16px;align-items:flex-start;flex-wrap:wrap;">']

    # Target (green)
    if feat_exp is not None:
        if feat_exp.is_vowel:
            svg = generate_vowel_chart_svg(expected, feat_exp, color="#38A169", width=260, height=200)
        else:
            svg = generate_sagittal_svg(expected, feat_exp, color="#38A169", label="Target", width=280, height=240)
        parts.append(f'<div style="text-align:center;">{svg}</div>')

    # Actual (red)
    if feat_act is not None:
        if feat_act.is_vowel:
            svg = generate_vowel_chart_svg(actual, feat_act, color="#E53E3E", width=260, height=200)
        else:
            svg = generate_sagittal_svg(actual, feat_act, color="#E53E3E", label="What you produced", width=280, height=240)
        parts.append(f'<div style="text-align:center;">{svg}</div>')

    parts.append('</div>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 3. Articulatory guidance
# ---------------------------------------------------------------------------

# Specific guidance for common substitution pairs
_PAIR_GUIDANCE: dict[tuple[str, str], str] = {
    ("θ", "s"): "Your tongue tip should be between your upper and lower teeth, not behind the upper teeth. Let air pass over the tongue tip.",
    ("θ", "t"): "Don't let your tongue fully block the airflow. Keep a small gap between your tongue tip and teeth for the air to pass through.",
    ("θ", "f"): "Use your tongue tip between your teeth, not your lower lip against upper teeth.",
    ("ð", "d"): "Keep your tongue between your teeth and let air flow continuously. Don't make a full stop.",
    ("ð", "z"): "Move your tongue forward between your teeth instead of placing it behind the upper teeth.",
    ("ɹ", "l"): "Don't touch your tongue tip to the roof of your mouth. Curl it back slightly and let air flow around it.",
    ("ɹ", "w"): "Your tongue tip should curl back slightly. Don't just round your lips.",
    ("ʃ", "s"): "Pull your tongue back slightly from the teeth ridge. The sound is made further back in the mouth.",
    ("v", "w"): "Your lower lip should touch your upper teeth. Don't just round both lips.",
    ("æ", "ɛ"): "Open your mouth wider and push your tongue lower. The sound is more open than /ɛ/.",
    ("ɑ", "æ"): "Pull your tongue back and drop it lower. Open your mouth wide.",
    ("ɪ", "iː"): "Relax your tongue slightly. This is a shorter, more relaxed sound than /iː/.",
    ("ʊ", "uː"): "Relax your lips and tongue. This is shorter and less tense than /uː/.",
    ("ŋ", "n"): "The back of your tongue should touch your soft palate (back of mouth), not the ridge behind your teeth.",
}

# Generic templates by feature difference
_PLACE_GUIDANCE: dict[tuple[str, str], str] = {
    ("bilabial", "labiodental"): "Use both lips together instead of lip-to-teeth contact.",
    ("labiodental", "bilabial"): "Touch your lower lip to your upper teeth instead of pressing both lips together.",
    ("dental", "alveolar"): "Move your tongue forward so it touches between or behind your teeth, not the ridge.",
    ("alveolar", "dental"): "Pull your tongue back to the ridge behind your upper teeth.",
    ("alveolar", "postalveolar"): "Move your tongue forward to the ridge right behind your upper teeth.",
    ("postalveolar", "alveolar"): "Pull your tongue back slightly past the ridge.",
    ("velar", "alveolar"): "Use the back of your tongue against the soft palate instead of the tongue tip at the ridge.",
    ("alveolar", "velar"): "Use your tongue tip at the ridge behind your upper teeth, not the back of your tongue.",
}


def get_articulatory_guidance(expected: str, actual: str) -> str:
    """Generate articulatory correction guidance for a substitution error."""
    # Check for specific pair guidance
    guidance = _PAIR_GUIDANCE.get((expected, actual))
    if guidance:
        return guidance

    # Reverse pair
    guidance = _PAIR_GUIDANCE.get((actual, expected))
    if guidance:
        return f"(Reverse correction) {guidance}"

    feat_exp = IPA_FEATURES.get(expected)
    feat_act = IPA_FEATURES.get(actual)

    if feat_exp is None or feat_act is None:
        return f"Expected /{expected}/ but heard /{actual}/."

    parts = []

    # Compare place
    if not feat_exp.is_vowel and not feat_act.is_vowel:
        if feat_exp.place != feat_act.place:
            place_tip = _PLACE_GUIDANCE.get((feat_exp.place, feat_act.place))
            if place_tip:
                parts.append(place_tip)
            else:
                parts.append(
                    f"Change your tongue position from {feat_act.place} to {feat_exp.place}."
                )

        if feat_exp.manner != feat_act.manner:
            parts.append(
                f"The target is a {feat_exp.manner} (not a {feat_act.manner})."
            )

        if feat_exp.voicing != feat_act.voicing:
            if feat_exp.voicing == "voiced":
                parts.append("Add vocal cord vibration (voice the sound).")
            else:
                parts.append("Stop vocal cord vibration (make it voiceless).")

    elif feat_exp.is_vowel and feat_act.is_vowel:
        if feat_exp.height != feat_act.height:
            parts.append(f"Adjust tongue height: target is {feat_exp.height}, you produced {feat_act.height}.")
        if feat_exp.backness != feat_act.backness:
            parts.append(f"Adjust tongue position: target is {feat_exp.backness}, you produced {feat_act.backness}.")
        if feat_exp.rounding != feat_act.rounding:
            if feat_exp.rounding == "rounded":
                parts.append("Round your lips more.")
            else:
                parts.append("Spread your lips (unround them).")

    if not parts:
        parts.append(f"Expected /{expected}/ but heard /{actual}/.")

    return " ".join(parts)


def generate_articulation_html(expected: str, actual: str) -> str:
    """Generate complete HTML block with SVG diagrams and guidance text for one error."""
    guidance = get_articulatory_guidance(expected, actual)
    comparison = generate_comparison_svg(expected, actual)

    if not comparison:
        # No SVG available, text-only
        return (
            f'<div style="padding:12px;margin:8px 0;background:#fff8f0;border-left:4px solid #E53E3E;border-radius:4px;">'
            f'<strong>/{expected}/ → /{actual}/</strong><br/>'
            f'<span style="color:#555;">{guidance}</span></div>'
        )

    return (
        f'<div style="padding:16px;margin:12px 0;background:#fff;border:1px solid #e2e8f0;border-radius:8px;'
        f'box-shadow:0 1px 3px rgba(0,0,0,0.08);">'
        f'<div style="font-size:16px;font-weight:bold;margin-bottom:8px;color:#2D3748;">'
        f'/{expected}/ → /{actual}/</div>'
        f'{comparison}'
        f'<div style="margin-top:12px;padding:10px;background:#EBF8FF;border-radius:6px;'
        f'font-size:14px;color:#2C5282;line-height:1.5;">'
        f'{guidance}</div></div>'
    )
