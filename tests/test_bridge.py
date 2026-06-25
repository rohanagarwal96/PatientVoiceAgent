import os

os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "https://myresource.openai.azure.com")
os.environ.setdefault("AZURE_OPENAI_API_KEY", "test_key")
os.environ.setdefault("AZURE_OPENAI_DEPLOYMENT", "gpt-realtime")
os.environ.setdefault("AZURE_OPENAI_API_VERSION", "2024-10-01-preview")


def test_azure_ws_url_format():
    from src.bridge import _azure_ws_url

    url = _azure_ws_url()
    assert url.startswith("wss://"), f"Expected wss:// prefix, got: {url}"
    assert "/openai/realtime" in url
    assert "api-version=2024-10-01-preview" in url
    assert "deployment=gpt-realtime" in url


def test_session_config_structure():
    from src.bridge import _build_session_config

    config = _build_session_config("You are a patient.")
    assert config["type"] == "session.update"
    session = config["session"]
    assert session["input_audio_format"] == "g711_ulaw"
    assert session["output_audio_format"] == "g711_ulaw"
    assert session["instructions"] == "You are a patient."
    assert session["turn_detection"]["type"] == "server_vad"
