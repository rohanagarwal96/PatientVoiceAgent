# PatientVoiceAgent

An AI voice bot that places outbound phone calls via Twilio and plays a realistic patient persona powered by Azure OpenAI gpt-realtime. The patient's first scenario is booking a new appointment with a doctor's office.

## Status

Repo scaffolded. Server, audio bridge, and call trigger are in progress.

## Prerequisites

- Python 3.11+
- ffmpeg
- ngrok (free account + authtoken required before the validation call)
- Twilio account with a phone number
- Azure OpenAI deployment of gpt-realtime

## Setup

1. Clone the repo.
2. Copy `.env.example` to `.env` and fill in your credentials.
3. Create and activate a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate    # Windows
   pip install -r requirements.txt
   ```

## Running the server

With venv active, from the project root:

```
uvicorn src.server:app --host 0.0.0.0 --port 8000
```

Endpoints:
- `POST /twiml` — Twilio calls this webhook; returns TwiML opening a media stream to `/media`
- `WS /media` — Twilio connects here to stream audio

Set `PUBLIC_BASE_URL` in `.env` to your ngrok https URL before starting.

## Audio bridge

`src/bridge.py` contains `AudioBridge`, which relays audio between Twilio and Azure gpt-realtime.

Key design decisions:
- **g711_ulaw end-to-end:** Twilio sends 8kHz mu-law audio; Azure is configured to accept and emit the same format. No resampling, no codec conversion.
- **Barge-in:** Azure's server-side VAD detects when the human speaks mid-response. When it does, `input_audio_buffer.speech_started` fires and the bridge immediately sends Twilio a `clear` event to cut playback.
- **Session config** (voice, turn detection, patient prompt) is defined in `_build_session_config()` — one place to tune all session parameters.

## Placing a call

With the server running and ngrok active:

```
python -m src.trigger
```

This calls +1-805-439-8008 from `TWILIO_FROM_NUMBER`, records both channels (dual-channel), and prints the Call SID. Find the recording at console.twilio.com → Monitor → Calls → Recordings.
