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

All test calls come from the same Twilio number, so the test agent keys its memory to one caller: **Alex Rivera** (DOB March 12, 1991, Blue Cross Blue Shield, CVS pharmacy). A `PATIENT_PROFILE` object in `src/scenarios.py` holds these stable details. The patient system prompt is assembled at call time from the shared profile plus the current scenario's `call_reason`, `goal`, and any optional `call_context` (e.g., prescription details). Scenarios no longer carry per-call personas — they carry reasons and goals.

To place a call with a specific scenario:
```
python -m src.pipeline --scenario 01_simple_scheduling
```

This is the **primary run mode**: one scenario, one call, you review before deciding what to run next.

The scenario ID flows: `pipeline.py` → `trigger.py` → `?scenario=` query param → `server.py` embeds it as a `<Parameter>` in the Twilio `<Stream>` → `bridge.py` reads it from `start.customParameters` → calls `scenario.get_system_prompt()` to inject the assembled patient prompt into the Azure gpt-realtime session.

### Returning-patient handling

Because all calls come from one number, the test agent remembers prior interactions and may greet by name or reference a prior appointment. This is production behavior, not a bug.

Each scenario has a `returning_patient_strategy`:

| Strategy | Effect |
|---|---|
| `lean_into_memory` | Accept the name/history and work with it toward the goal (default) |
| `correct_the_record` | Gently push back if prior state conflicts with the goal |
| `ignore` | Confirm naturally and redirect without dwelling on the memory |

`01_simple_scheduling` uses `correct_the_record` because a genuine new-booking attempt should not be blocked by a prior appointment in the agent's memory.

### Chained vs standalone scenarios

Three scenarios form an **appointment-lifecycle chain** that tests the agent's memory across calls. Run them in order:

| # | Scenario | Depends on |
|---|---|---|
| 1 | `01_simple_scheduling` | — (run first; the only true new-patient call) |
| 2 | `03_reschedule` | `01_simple_scheduling` |
| 3 | `04_cancel` | `03_reschedule` |

> **First-time-booking note:** A clean new-patient booking can only happen once per phone number. `01_simple_scheduling` is that call. All subsequent booking-type scenarios (`03_reschedule`, `04_cancel`, and any future booking tests) are explicitly returning-patient flows.

To step through the chain with a confirmation prompt between each call:
```
python -m src.pipeline --chain
```
The chain runner pauses and waits for you to press Enter before placing each subsequent call. It never batches calls unattended. If you re-run a single chained scenario in isolation, the runner warns which earlier call established the state it depends on.

The remaining nine scenarios are **standalone** and can be run in any order:

| ID | Name | What it tests |
|----|------|---------------|
| `02_after_hours` | After Hours Request | Declines Sunday/9pm, offers next weekday |
| `05_controlled_substance` | Controlled Substance Refill | Routes to provider review |
| `06_refill_no_pharmacy` | Refill Missing Pharmacy | Handles missing pharmacy gracefully |
| `07_unverifiable_insurance` | Unverifiable Insurance | No hallucinated coverage |
| `08_location_hours` | Multi-Location Hours | Accurate hours, no contradictions |
| `09_barge_in` | Interruption/Barge-in | Turn-taking under interruption |
| `10_unclear_mind_change` | Unclear + Changes Mind | Handles mid-call specialty change |
| `11_multi_intent` | Multi-Intent | Completes all three tasks |
| `12_emergency` | Emergency Symptom | Routes to emergency care |

## Recording retrieval

After a call completes, fetch and convert the Twilio recording:

```
python -m src.recorder --call-sid CA... --scenario 01_simple_scheduling
```

Polls Twilio every 5 seconds (timeout 3 min), downloads the recording, pipes through ffmpeg to produce a dual-channel 44.1kHz mp3 in `recordings/`.

To backfill recent recordings:
```
python -m src.recorder --backfill --limit 10
```

Note: `recordings/` is gitignored.

## Transcription

Transcribe a recording with speaker attribution:

```
python -m src.transcriber --recording recordings/01_simple_scheduling_20260625_120000_CAabc.mp3
```

Or transcribe all untranscribed recordings:
```
python -m src.transcriber --all
```

Uses Whisper `small` model. Splits the dual-channel mp3 into two mono wav files (channel 0 = AGENT/called party, channel 1 = PATIENT/calling party), transcribes each independently, merges segments by timestamp.

Output in `transcripts/`:
- `.txt` — human-readable with `[MM:SS] SPEAKER: text` format
- `.json` — structured array with `speaker`, `start`, `end`, `text` fields

Note: `transcripts/` is gitignored.

## Bug evaluator

After transcribing a call, run the evaluator to find and review potential bugs:

```
python -m src.evaluator --transcript transcripts/05_controlled_substance_20260625_120000_CAabc.json --scenario 05_controlled_substance
```

Add `--dry-run` to see candidate findings without being prompted and without writing to `bug_report.md`:

```
python -m src.evaluator --transcript transcripts/... --scenario 01_simple_scheduling --dry-run
```

The evaluator:
1. Reads the transcript JSON and the scenario's known failure mode (`trap`).
2. Formats the transcript with correct `MM:SS` timestamps and calls Azure OpenAI (`AZURE_OPENAI_EVAL_DEPLOYMENT`) for candidate findings.
3. Validates that each timestamp falls within the call duration — flags any that do not.
4. Grades the scheduling agent against real-world competency, not the test script. Candidates where the agent's behavior was reasonable despite not matching the script are either suppressed or flagged as low-confidence.
5. Flags possible state artifacts — cases where the agent may be responding to legitimate prior-call memory from this test number rather than making a mistake.
6. Presents each finding with a `[k]eep / [e]dit / [d]rop` prompt (interactive mode only).
7. Appends confirmed findings to `bug_report.md` with: precise title, severity + one-line justification, correct `MM:SS` timestamp, evidence quote from the transcript, structured description (what happened / why it matters / what should have happened), confidence level, and state-artifact flag.

`bug_report.md` is committed to the repo. Raw recordings and transcripts are gitignored.

`bug_report.md` is committed to the repo. Raw transcripts and recordings are gitignored.

### Full Phase 2 workflow

Run everything with one command:

```
python -m src.pipeline --scenario 12_emergency
```

This places the call, waits for the recording, transcribes it, and opens the human-in-the-loop evaluator.

To skip the evaluator:

```
python -m src.pipeline --scenario 12_emergency --no-evaluate
```

The individual steps can still be run separately if needed:

```
python -m src.trigger --scenario 12_emergency
python -m src.recorder --call-sid CA... --scenario 12_emergency
python -m src.transcriber --recording recordings/12_emergency_....mp3
python -m src.evaluator --transcript transcripts/12_emergency_....json --scenario 12_emergency
```

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
