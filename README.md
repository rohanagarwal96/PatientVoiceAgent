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
