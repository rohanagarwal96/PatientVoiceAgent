import os

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from fastapi.responses import Response

load_dotenv()

app = FastAPI()


def _ws_base_url() -> str:
    base = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    if not base:
        raise RuntimeError("PUBLIC_BASE_URL is not set")
    return base.replace("https://", "wss://").replace("http://", "ws://")


@app.post("/twiml")
async def twiml_webhook():
    ws_url = _ws_base_url()
    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        "<Connect>"
        f'<Stream url="{ws_url}/media" />'
        "</Connect>"
        "</Response>"
    )
    return Response(content=twiml, media_type="application/xml")


@app.websocket("/media")
async def media_websocket(websocket: WebSocket):
    await websocket.accept()
    from src.bridge import AudioBridge

    bridge = AudioBridge(websocket)
    await bridge.run()
