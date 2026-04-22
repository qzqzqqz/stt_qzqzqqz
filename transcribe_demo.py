#!/Users/qizhao/.venvs/mlx-audio/bin/python
import sys
from mlx_audio.stt.utils import load_model
from mlx_audio.stt.generate import generate_transcription


def transcribe(audio_path, output_path=None, format="txt"):
    print(f"Loading model...")
    model = load_model("mlx-community/VibeVoice-ASR-bf16")

    print(f"Transcribing: {audio_path}")
    transcription = generate_transcription(
        model=model,
        audio=audio_path,
        output_path=output_path,
        format=format,
        verbose=True,
    )
    print(f"\nTranscription:\n{transcription.text}")
    return transcription.text


if __name__ == "__main__":
    transcribe(
        audio_path="/Users/qizhao/Downloads/小Lin说多邻国Luis访谈.wav",
        output_path="/Users/qizhao/Downloads/小Lin说多邻国Luis访谈.txt",
    )
