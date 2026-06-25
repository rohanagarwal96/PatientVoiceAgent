import os

os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com")
os.environ.setdefault("AZURE_OPENAI_API_KEY", "test_key")
os.environ.setdefault("AZURE_OPENAI_DEPLOYMENT", "gpt-realtime")
os.environ.setdefault("AZURE_OPENAI_API_VERSION", "2024-10-01-preview")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "ACtest")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "test_token")
os.environ.setdefault("TWILIO_FROM_NUMBER", "+10000000000")
os.environ.setdefault("PUBLIC_BASE_URL", "https://abc123.ngrok.io")

from fastapi.testclient import TestClient
from src.server import app

client = TestClient(app)


def test_twiml_returns_xml_with_stream_url():
    response = client.post("/twiml")
    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    body = response.text
    assert "<Stream" in body
    assert "wss://abc123.ngrok.io/media" in body


def test_twiml_embeds_scenario_parameter():
    response = client.post("/twiml?scenario=01_simple_scheduling")
    assert response.status_code == 200
    body = response.text
    assert '<Parameter name="scenario" value="01_simple_scheduling"' in body
