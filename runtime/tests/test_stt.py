import io
import math
import struct
import wave

from charlie.voice.stt import transcribe_wav_bytes


def _wav(samples: list[int], rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(b"".join(struct.pack("<h", s) for s in samples))
    return buf.getvalue()


class FakeWhisper:
    def __init__(self) -> None:
        self.called = False

    def transcribe(self, audio, language="en", beam_size=1):
        self.called = True

        class Seg:
            text = "open terminal"

        return [Seg()], None


def test_silence_does_not_call_model():
    whisper = FakeWhisper()
    text = transcribe_wav_bytes(_wav([0] * 8000), whisper=whisper)
    assert text == ""
    assert whisper.called is False


def test_speech_like_audio_returns_transcript():
    whisper = FakeWhisper()
    samples = [int(12000 * math.sin(2 * math.pi * 220 * i / 16000)) for i in range(16000)]
    text = transcribe_wav_bytes(_wav(samples), whisper=whisper)
    assert whisper.called is True
    assert text == "open terminal"
