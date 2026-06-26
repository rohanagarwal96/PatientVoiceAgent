import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_transcribe_produces_txt_and_json(tmp_path):
    fake_mp3 = tmp_path / "01_simple_scheduling_20260625_120000_CAtest.mp3"
    fake_mp3.write_bytes(b"fake mp3 data")

    # ch0 = AGENT (called party), ch1 = PATIENT (calling party)
    fake_seg_agent = {"id": 0, "seek": 0, "start": 1.0, "end": 3.0, "text": " Hello there"}
    fake_seg_patient = {"id": 0, "seek": 0, "start": 4.0, "end": 6.0, "text": " How can I help"}

    ch0 = tmp_path / "ch0.wav"
    ch1 = tmp_path / "ch1.wav"
    ch0.write_bytes(b"")
    ch1.write_bytes(b"")

    with (
        patch("src.transcriber._split_channels", return_value=(ch0, ch1)),
        patch("src.transcriber.whisper") as mock_whisper,
        patch("src.transcriber._TRANSCRIPTS_DIR", tmp_path),
    ):
        mock_model = MagicMock()
        mock_whisper.load_model.return_value = mock_model
        mock_model.transcribe.side_effect = [
            {"segments": [fake_seg_agent]},   # ch0 → AGENT
            {"segments": [fake_seg_patient]}, # ch1 → PATIENT
        ]

        from src.transcriber import transcribe
        txt_path, json_path = transcribe(fake_mp3)

    assert txt_path.exists()
    assert json_path.exists()

    content = txt_path.read_text(encoding="utf-8")
    assert "PATIENT" in content
    assert "AGENT" in content
    assert "Hello there" in content

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert len(data) == 2
    assert data[0]["speaker"] == "AGENT"
    assert data[0]["start"] < data[1]["start"]


def test_transcribe_segments_sorted_by_time(tmp_path):
    fake_mp3 = tmp_path / "test_recording.mp3"
    fake_mp3.write_bytes(b"fake")

    ch0 = tmp_path / "ch0.wav"
    ch1 = tmp_path / "ch1.wav"
    ch0.write_bytes(b"")
    ch1.write_bytes(b"")

    # Agent speaks first (start=1.0), patient responds (start=5.0)
    fake_seg_agent = {"id": 0, "seek": 0, "start": 1.0, "end": 3.0, "text": " Agent speaks first"}
    fake_seg_patient = {"id": 0, "seek": 0, "start": 5.0, "end": 7.0, "text": " Patient responds"}

    with (
        patch("src.transcriber._split_channels", return_value=(ch0, ch1)),
        patch("src.transcriber.whisper") as mock_whisper,
        patch("src.transcriber._TRANSCRIPTS_DIR", tmp_path),
    ):
        mock_model = MagicMock()
        mock_whisper.load_model.return_value = mock_model
        # ch0 = AGENT, ch1 = PATIENT
        mock_model.transcribe.side_effect = [
            {"segments": [fake_seg_agent]},   # ch0
            {"segments": [fake_seg_patient]}, # ch1
        ]

        from src.transcriber import transcribe
        _, json_path = transcribe(fake_mp3)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data[0]["speaker"] == "AGENT"
    assert data[1]["speaker"] == "PATIENT"
