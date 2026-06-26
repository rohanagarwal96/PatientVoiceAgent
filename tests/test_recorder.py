import os

os.environ.setdefault("TWILIO_ACCOUNT_SID", "ACtest")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "test_token")

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _make_client_mock(call_status="completed", recordings=None):
    """Return a mock Twilio Client with call status and recordings pre-configured."""
    mock_client = MagicMock()
    mock_call = MagicMock()
    mock_call.status = call_status
    mock_client.calls.return_value.fetch.return_value = mock_call
    mock_client.recordings.list.return_value = recordings or []
    return mock_client


def test_fetch_recording_timeout():
    """TimeoutError when no recording appears after call completes."""
    with patch("src.recorder.Client") as mock_client_class:
        mock_client_class.return_value = _make_client_mock(call_status="completed", recordings=[])
        with patch("src.recorder._POLL_INTERVAL", 0), patch("src.recorder._POLL_TIMEOUT", 0):
            from src.recorder import fetch_recording
            with pytest.raises(TimeoutError):
                fetch_recording("CAtest123", "01_simple_scheduling")


def test_fetch_recording_names_file_correctly(tmp_path):
    """Output file has correct naming pattern: {scenario_id}_{ts}_{call_sid}.mp3"""
    mock_rec = MagicMock()
    mock_rec.uri = "/2010-04-01/Accounts/ACtest/Recordings/REtest.json"

    with (
        patch("src.recorder.Client") as mock_client_class,
        patch("src.recorder.requests") as mock_requests,
        patch("src.recorder.subprocess.run") as mock_run,
        patch("src.recorder._RECORDINGS_DIR", tmp_path),
    ):
        mock_client_class.return_value = _make_client_mock(call_status="completed", recordings=[mock_rec])

        mock_resp = MagicMock()
        mock_resp.content = b"fake audio"
        mock_requests.get.return_value = mock_resp
        mock_run.return_value = MagicMock(returncode=0)

        from src.recorder import fetch_recording
        out = fetch_recording("CAtest123", "01_simple_scheduling")

    assert out.suffix == ".mp3"
    assert "01_simple_scheduling" in out.name
    assert "CAtest123" in out.name
