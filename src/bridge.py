import asyncio
import json
import os

import websockets
from dotenv import load_dotenv
from fastapi import WebSocket

from src.scenarios import Scenario, get_scenario

load_dotenv()

_AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
_AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
_AZURE_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-realtime")
_AZURE_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-01-preview")


def _azure_ws_url() -> str:
    base = _AZURE_ENDPOINT.replace("https://", "wss://").replace("http://", "ws://")
    return (
        f"{base}/openai/realtime"
        f"?api-version={_AZURE_API_VERSION}"
        f"&deployment={_AZURE_DEPLOYMENT}"
    )


def _build_session_config(instructions: str) -> dict:
    return {
        "type": "session.update",
        "session": {
            "modalities": ["audio", "text"],
            "instructions": instructions,
            "voice": "alloy",
            "input_audio_format": "g711_ulaw",
            "output_audio_format": "g711_ulaw",
            "input_audio_transcription": None,
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.5,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 800,
            },
        },
    }


class AudioBridge:
    def __init__(self, twilio_ws: WebSocket):
        self.twilio_ws = twilio_ws
        self.stream_sid: str = ""
        self._azure_ws = None

    async def run(self) -> None:
        url = _azure_ws_url()
        headers = {"api-key": _AZURE_API_KEY}
        print(f"[bridge] connecting to Azure: {url}", flush=True)
        try:
            async with websockets.connect(url, additional_headers=headers) as azure_ws:
                self._azure_ws = azure_ws
                await asyncio.gather(
                    self._relay_twilio_to_azure(),
                    self._relay_azure_to_twilio(),
                )
        except Exception as exc:
            print(f"[bridge] fatal error: {exc}", flush=True)
        finally:
            try:
                await self.twilio_ws.close()
            except Exception:
                pass

    async def _configure_session(self, scenario: Scenario) -> None:
        await self._azure_ws.send(json.dumps(_build_session_config(scenario.system_prompt)))
        print(f"[bridge] session configured scenario={scenario.id}", flush=True)

    async def _relay_twilio_to_azure(self) -> None:
        async for raw in self.twilio_ws.iter_text():
            msg = json.loads(raw)
            event = msg.get("event")
            if event == "start":
                self.stream_sid = msg["start"]["streamSid"]
                scenario_id = msg["start"].get("customParameters", {}).get(
                    "scenario", "01_simple_scheduling"
                )
                scenario = get_scenario(scenario_id)
                await self._configure_session(scenario)
                print(f"[bridge] stream started sid={self.stream_sid}", flush=True)
            elif event == "media":
                await self._azure_ws.send(json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": msg["media"]["payload"],
                }))
            elif event == "stop":
                print("[bridge] stream stopped", flush=True)
                await self._azure_ws.close()
                break

    async def _relay_azure_to_twilio(self) -> None:
        async for raw in self._azure_ws:
            msg = json.loads(raw)
            msg_type = msg.get("type", "")
            if msg_type == "response.audio.delta":
                await self.twilio_ws.send_text(json.dumps({
                    "event": "media",
                    "streamSid": self.stream_sid,
                    "media": {"payload": msg["delta"]},
                }))
            elif msg_type == "input_audio_buffer.speech_started":
                await self.twilio_ws.send_text(json.dumps({
                    "event": "clear",
                    "streamSid": self.stream_sid,
                }))
            elif msg_type == "error":
                print(f"[bridge] azure error: {msg}", flush=True)
