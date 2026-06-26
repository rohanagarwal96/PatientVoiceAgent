import argparse
import json
import subprocess
import tempfile
from pathlib import Path

import whisper

_TRANSCRIPTS_DIR = Path(__file__).parent.parent / "transcripts"
_CHANNEL_LABELS = {0: "PATIENT", 1: "AGENT"}


def _split_channels(mp3_path: Path, tmp_dir: str) -> tuple[Path, Path]:
    ch0 = Path(tmp_dir) / "ch0.wav"
    ch1 = Path(tmp_dir) / "ch1.wav"
    proc = subprocess.run(
        [
            "ffmpeg", "-i", str(mp3_path), "-y",
            "-filter_complex", "[0:a]channelsplit=channel_layout=stereo[left][right]",
            "-map", "[left]", str(ch0),
            "-map", "[right]", str(ch1),
        ],
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg channel split failed: {proc.stderr.decode()}")
    return ch0, ch1


def transcribe(recording_path: Path) -> tuple[Path, Path]:
    """Transcribe a dual-channel mp3. Returns (txt_path, json_path)."""
    model = whisper.load_model("small")
    _TRANSCRIPTS_DIR.mkdir(exist_ok=True)
    stem = recording_path.stem

    with tempfile.TemporaryDirectory() as tmp_dir:
        ch0, ch1 = _split_channels(recording_path, tmp_dir)

        segments: list[dict] = []
        for channel_idx, wav_path in enumerate((ch0, ch1)):
            result = model.transcribe(str(wav_path), language="en")
            label = _CHANNEL_LABELS[channel_idx]
            for seg in result["segments"]:
                segments.append({
                    "speaker": label,
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"].strip(),
                })

    segments.sort(key=lambda s: s["start"])

    txt_path = _TRANSCRIPTS_DIR / f"{stem}.txt"
    json_path = _TRANSCRIPTS_DIR / f"{stem}.json"

    with txt_path.open("w", encoding="utf-8") as f:
        for seg in segments:
            mm = int(seg["start"]) // 60
            ss = int(seg["start"]) % 60
            f.write(f"[{mm:02d}:{ss:02d}] {seg['speaker']}: {seg['text']}\n")

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(segments, f, indent=2)

    print(f"[transcriber] wrote {txt_path} and {json_path}", flush=True)
    return txt_path, json_path


def transcribe_all() -> list[tuple[Path, Path]]:
    recordings_dir = Path(__file__).parent.parent / "recordings"
    results = []
    for mp3 in sorted(recordings_dir.glob("*.mp3")):
        json_path = _TRANSCRIPTS_DIR / f"{mp3.stem}.json"
        if json_path.exists():
            print(f"[transcriber] skipping {mp3.name} (already transcribed)", flush=True)
            continue
        results.append(transcribe(mp3))
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--recording", help="Path to mp3 recording")
    group.add_argument("--all", action="store_true", help="Transcribe all untranscribed recordings")
    args = parser.parse_args()

    if args.all:
        results = transcribe_all()
        print(f"[transcriber] transcribed {len(results)} recordings")
    else:
        txt, js = transcribe(Path(args.recording))
        print(f"[transcriber] txt={txt} json={js}")
