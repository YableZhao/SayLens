"""Gradio Web UI for pronunciation feedback."""
from __future__ import annotations

import os
import subprocess
import tempfile

import gradio as gr

from speech_feedback.pipeline import PronunciationPipeline
from speech_feedback.voice_cloner import VoiceCloner

# Global instances (loaded once at startup)
_pipeline: PronunciationPipeline | None = None
_cloner: VoiceCloner | None = None


def get_pipeline(language: str = "en-us") -> PronunciationPipeline:
    global _pipeline
    if _pipeline is None or _pipeline.language != language:
        _pipeline = PronunciationPipeline(language=language)
    return _pipeline


def get_voice_cloner() -> VoiceCloner:
    global _cloner
    if _cloner is None:
        _cloner = VoiceCloner()
    return _cloner


def generate_reference_audio(target_text: str, language: str) -> str | None:
    """Generate reference audio using espeak-ng TTS."""
    if not target_text.strip():
        return None
    lang_map = {
        "en-us": "en-us", "en-gb": "en-gb", "fr-fr": "fr",
        "de": "de", "es": "es", "cmn": "cmn", "ja": "ja",
    }
    espeak_lang = lang_map.get(language, "en-us")
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    try:
        subprocess.run(
            ["espeak-ng", "-w", tmp.name, "-v", espeak_lang, target_text.strip()],
            check=True, capture_output=True,
        )
        return tmp.name
    except Exception:
        os.unlink(tmp.name)
        return None


def analyze_pronunciation(
    audio_filepath: str | None,
    target_text: str,
    language: str,
) -> tuple:
    """Main analysis function called by Gradio."""
    empty = [], "", "", "Please record or upload audio, or click 'Generate TTS Audio' first.", 0.0, ""
    if not audio_filepath:
        return empty
    if not target_text.strip():
        return [], "", "", "Please enter the target text.", 0.0, ""

    try:
        pipeline = get_pipeline(language)
        result = pipeline.analyze(audio_filepath, target_text.strip())
        return (
            result["highlighted_text"],
            result["expected_ipa"],
            result["actual_ipa"],
            result["summary"],
            result["accuracy"],
            result.get("articulatory_html", ""),
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return [], "", "", f"Error: {e}", 0.0, ""


def clone_voice(
    ref_audio: str | None,
    target_text: str,
    language: str,
) -> tuple:
    """Generate speech in cloned voice."""
    if not ref_audio:
        return None, "Please upload a reference voice sample (6+ seconds)."
    if not target_text.strip():
        return None, "Please enter target text first."

    cloner = get_voice_cloner()
    if not cloner.is_available:
        return None, (
            "Voice cloning requires the TTS package. "
            "Install with: `pip install TTS`"
        )

    valid, msg = cloner.validate_reference(ref_audio)
    if not valid:
        return None, msg

    try:
        lang = language.split("-")[0]
        output = cloner.generate(target_text.strip(), ref_audio, lang)
        return output, "Generated successfully! (using XTTS v2)"
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None, f"Error generating cloned voice: {e}"


def build_app() -> gr.Blocks:
    """Build the Gradio Blocks app."""
    with gr.Blocks(title="Phoneme Pronunciation Feedback") as demo:
        gr.Markdown(
            "# Phoneme-Level Pronunciation Feedback\n"
            "Enter target text, then either **record/upload your audio** or click "
            "**Generate TTS Audio** to create a test sample. Finally click **Analyze**.\n\n"
            "> **Tip**: If recording shows a flat waveform, click the device name "
            "next to the record button and switch to your real microphone."
        )

        with gr.Row():
            # ---- Left column: inputs ----
            with gr.Column(scale=1):
                language = gr.Dropdown(
                    choices=[
                        ("English (US)", "en-us"),
                        ("English (UK)", "en-gb"),
                        ("French", "fr-fr"),
                        ("German", "de"),
                        ("Spanish", "es"),
                        ("Mandarin", "cmn"),
                        ("Japanese", "ja"),
                    ],
                    value="en-us",
                    label="Language",
                )
                target_text = gr.Textbox(
                    label="Target Text",
                    placeholder="Type what you want to say, e.g. 'hello world'",
                    lines=2,
                )
                audio_input = gr.Audio(
                    sources=["microphone", "upload"],
                    type="filepath",
                    label="Your Audio (record, upload, or generate below)",
                    waveform_options=gr.WaveformOptions(
                        show_recording_waveform=True,
                        sample_rate=16000,
                    ),
                )
                with gr.Row():
                    tts_btn = gr.Button("Generate TTS Audio", variant="secondary")
                    analyze_btn = gr.Button("Analyze", variant="primary")

            # ---- Right column: outputs ----
            with gr.Column(scale=2):
                with gr.Row():
                    expected_ipa = gr.Textbox(label="Expected IPA", interactive=False)
                    actual_ipa = gr.Textbox(label="Recognized IPA", interactive=False)

                highlighted = gr.HighlightedText(
                    label="Phoneme Feedback",
                    color_map={
                        "good": "#4CAF50", "fair": "#FF9800", "poor": "#F44336",
                        "missing": "#9E9E9E", "insertion": "#9C27B0",
                    },
                    show_legend=True,
                )

                accuracy = gr.Number(label="Accuracy %", interactive=False, precision=1)
                summary = gr.Markdown(label="Feedback Details")

                # Articulatory visualization
                with gr.Accordion("Articulation Guide (mouth diagrams)", open=True):
                    articulatory_viz = gr.HTML(value="", label="Articulation Guide")

        # Voice cloning section
        with gr.Accordion("Voice Cloning - hear the correct pronunciation in YOUR voice", open=False):
            gr.Markdown(
                "Upload a **6+ second** sample of your voice reading anything. "
                "The system will generate the target phrase in your own voice so you can "
                "hear how you should sound. *(First use downloads ~2GB model, generation takes 10-30s on CPU)*"
            )
            with gr.Row():
                with gr.Column(scale=1):
                    ref_voice = gr.Audio(
                        sources=["microphone", "upload"],
                        type="filepath",
                        label="Reference Voice (6+ seconds of your speech)",
                    )
                    clone_btn = gr.Button("Generate My Voice Reference", variant="secondary")
                with gr.Column(scale=1):
                    cloned_audio = gr.Audio(
                        label="Target Phrase in Your Voice",
                        interactive=False,
                        type="filepath",
                    )
                    clone_status = gr.Markdown("")

        # ---- Wire up events ----
        tts_btn.click(
            fn=generate_reference_audio,
            inputs=[target_text, language],
            outputs=[audio_input],
        )

        analyze_btn.click(
            fn=analyze_pronunciation,
            inputs=[audio_input, target_text, language],
            outputs=[highlighted, expected_ipa, actual_ipa, summary, accuracy, articulatory_viz],
        )

        clone_btn.click(
            fn=clone_voice,
            inputs=[ref_voice, target_text, language],
            outputs=[cloned_audio, clone_status],
        )

        # Examples
        gr.Examples(
            examples=[
                ["Hello world", "en-us"],
                ["The quick brown fox", "en-us"],
                ["She sells seashells", "en-us"],
            ],
            inputs=[target_text, language],
            label="Example Phrases",
        )

    return demo


def main():
    demo = build_app()
    demo.launch(share=False)


if __name__ == "__main__":
    main()
