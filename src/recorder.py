import argparse
import os
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

_RECORDINGS_DIR = Path(__file__).parent.parent / "recordings"
_POLL_INTERVAL = 5
_CALL_TIMEOUT = 600   # 10 min — wait for the call itself to end
_POLL_TIMEOUT = 180   # 3 min — wait for recording to appear after call ends

_TERMINAL_CALL_STATUSES = {"completed", "failed", "busy", "no-answer", "canceled"}


def fetch_recording(call_sid: str, scenario_id: str) -> Path:
    """Wait for call to complete, then poll for recording and convert to dual-channel mp3."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    client = Client(account_sid, auth_token)

    # Wait for the call to reach a terminal status before looking for a recording.
    print(f"[recorder] waiting for call {call_sid} to complete...", flush=True)
    deadline = time.time() + _CALL_TIMEOUT
    while time.time() < deadline:
        call_status = client.calls(call_sid).fetch().status
        if call_status in _TERMINAL_CALL_STATUSES:
            print(f"[recorder] call ended (status={call_status})", flush=True)
            break
        print(f"[recorder] call in progress (status={call_status}), checking in {_POLL_INTERVAL}s...", flush=True)
        time.sleep(_POLL_INTERVAL)
    else:
        raise TimeoutError(f"Call {call_sid} did not complete within {_CALL_TIMEOUT}s")

    if call_status != "completed":
        raise RuntimeError(f"Call ended with non-completed status: {call_status}")

    recording = None
    deadline = time.time() + _POLL_TIMEOUT
    while time.time() < deadline:
        recs = client.recordings.list(call_sid=call_sid)
        if recs:
            recording = recs[0]
            break
        print(f"[recorder] waiting for recording... (retry in {_POLL_INTERVAL}s)", flush=True)
        time.sleep(_POLL_INTERVAL)

    if recording is None:
        raise TimeoutError(f"No recording found for {call_sid} after {_POLL_TIMEOUT}s")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    _RECORDINGS_DIR.mkdir(exist_ok=True)
    out_path = _RECORDINGS_DIR / f"{scenario_id}_{ts}_{call_sid}.mp3"

    media_url = f"https://api.twilio.com{recording.uri.replace('.json', '.wav')}"
    print(f"[recorder] downloading {media_url}", flush=True)
    resp = requests.get(media_url, auth=(account_sid, auth_token))
    resp.raise_for_status()

    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found in PATH. Open a new terminal to refresh PATH, then re-run.")

    proc = subprocess.run(
        ["ffmpeg", "-i", "pipe:0", "-ac", "2", "-ar", "44100", "-q:a", "2", str(out_path)],
        input=resp.content,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr.decode()}")

    print(f"[recorder] saved {out_path}", flush=True)
    return out_path


def backfill(limit: int = 10) -> list[Path]:
    """Download recent recordings not yet converted."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    client = Client(account_sid, auth_token)

    _RECORDINGS_DIR.mkdir(exist_ok=True)
    results = []
    for rec in client.recordings.list(limit=limit):
        call_sid = rec.call_sid

        # Skip if already downloaded (any file ending in _{call_sid}.mp3)
        if list(_RECORDINGS_DIR.glob(f"*_{call_sid}.mp3")):
            print(f"[recorder] skipping {call_sid} (already downloaded)", flush=True)
            continue

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = _RECORDINGS_DIR / f"backfill_{ts}_{call_sid}.mp3"

        media_url = f"https://api.twilio.com{rec.uri.replace('.json', '.wav')}"
        try:
            resp = requests.get(media_url, auth=(account_sid, auth_token))
            resp.raise_for_status()
        except Exception as exc:
            print(f"[recorder] download failed for {call_sid}: {exc}", flush=True)
            continue

        proc = subprocess.run(
            ["ffmpeg", "-i", "pipe:0", "-ac", "2", "-ar", "44100", "-q:a", "2", str(out_path)],
            input=resp.content,
            capture_output=True,
        )
        if proc.returncode != 0:
            print(f"[recorder] ffmpeg failed for {call_sid}: {proc.stderr.decode()}", flush=True)
            continue

        print(f"[recorder] saved {out_path}", flush=True)
        results.append(out_path)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--call-sid", help="Fetch recording for this Call SID")
    group.add_argument("--backfill", action="store_true", help="Download recent recordings")
    parser.add_argument("--scenario", default="unknown", help="Scenario ID (used in filename)")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    if args.backfill:
        paths = backfill(args.limit)
        print(f"[recorder] backfilled {len(paths)} recordings")
    else:
        path = fetch_recording(args.call_sid, args.scenario)
        print(f"[recorder] output: {path}")
