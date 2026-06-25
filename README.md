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

## Scenario engine

Scenarios are defined in `src/scenarios.py`. Each scenario is a Pydantic `Scenario` object with `id`, `name`, `persona`, `goal`, `trap`, `opening_hint`, and `system_prompt` fields.

To place a call with a specific scenario:
```
python -m src.trigger --scenario 01_simple_scheduling
```

The scenario ID flows: `trigger.py` → `?scenario=` query param → `server.py` embeds it as a `<Parameter>` in the Twilio `<Stream>` → `bridge.py` reads it from `start.customParameters` → injects the scenario's `system_prompt` into the Azure gpt-realtime session.

Available scenario IDs:

| ID | Name | What it tests |
|----|------|---------------|
| `01_simple_scheduling` | Simple Scheduling | Collects name/DOB/insurance, offers slot |
| `02_after_hours` | After Hours Request | Declines Sunday/9pm, offers next weekday |
| `03_reschedule` | Reschedule | Identity lookup, no double-book |
| `04_cancel` | Cancellation | Confirms cancellation, not just acknowledges |
| `05_controlled_substance` | Controlled Substance Refill | Routes to provider review |
| `06_refill_no_pharmacy` | Refill Missing Pharmacy | Handles missing pharmacy gracefully |
| `07_unverifiable_insurance` | Unverifiable Insurance | No hallucinated coverage |
| `08_location_hours` | Multi-Location Hours | Accurate hours, no contradictions |
| `09_barge_in` | Interruption/Barge-in | Turn-taking under interruption |
| `10_unclear_mind_change` | Unclear + Changes Mind | Handles mumble + mid-call change |
| `11_multi_intent` | Multi-Intent | Completes all three tasks |
| `12_emergency` | Emergency Symptom | Routes to emergency care |

## Patient persona

The AI patient is Alex Rivera, a 34-year-old booking a general check-up. The persona prompt lives in `prompts/patient.txt` and is loaded into the Azure gpt-realtime session at call start.

## Full validation workflow

1. Fill in `.env` with your credentials.
2. Start ngrok in a terminal:
   ```
   ngrok http 8000
   ```
3. Copy the `https://` URL from ngrok into `.env` as `PUBLIC_BASE_URL`.
4. Start the server (with venv active) in another terminal:
   ```
   uvicorn src.server:app --host 0.0.0.0 --port 8000
   ```
5. Place the call in a third terminal (with venv active):
   ```
   python -m src.trigger
   ```
6. Listen to the dual-channel recording at console.twilio.com → Monitor → Calls → Recordings.
