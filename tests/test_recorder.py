import os

os.environ.setdefault("TWILIO_ACCOUNT_SID", "ACtest")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "test_token")

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_fetch_recording_timeout():
    with patch("src.recorder.Client") as mock_client_class:
        mock_client_class.return_value.recordings.list.return_value = []
        with patch("src.recorder._POLL_INTERVAL", 0), patch("src.recorder._POLL_TIMEOUT", 0):
            from src.recorder import fetch_recording
            with pytest.raises(TimeoutError):
                fetch_recording("CAtest123", "01_simple_scheduling")


def test_fetch_recording_names_file_correctly(tmp_path):
    with (
        patch("src.recorder.Client") as mock_client_class,
        patch("src.recorder.requests") as mock_requests,
        patch("src.recorder.subprocess.run") as mock_run,
        patch("src.recorder._RECORDINGS_DIR", tmp_path),
    ):
        mock_rec = MagicMock()
        mock_rec.uri = "/2010-04-01/Accounts/ACtest/Recordings/REtest.json"
        mock_client_class.return_value.recordings.list.return_value = [mock_rec]

        mock_resp = MagicMock()
        mock_resp.content = b"fake audio"
        mock_requests.get.return_value = mock_resp

        mock_run.return_value = MagicMock(returncode=0)

        from src.recorder import fetch_recording
        out = fetch_recording("CAtest123", "01_simple_scheduling")

        assert out.suffix == ".mp3"
        assert "01_simple_scheduling" in out.name
        assert "CAtest123" in out.name
