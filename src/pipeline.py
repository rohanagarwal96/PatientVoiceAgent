import argparse

from src.evaluator import evaluate
from src.recorder import fetch_recording
from src.transcriber import transcribe
from src.trigger import place_call


def run_pipeline(scenario_id: str, run_eval: bool = True) -> None:
    """Place call, fetch recording, transcribe, and optionally evaluate."""
    call_sid = place_call(scenario_id)
    recording_path = fetch_recording(call_sid, scenario_id)
    _, json_path = transcribe(recording_path)
    if run_eval:
        evaluate(json_path, scenario_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the full PatientVoiceAgent pipeline for a scenario."
    )
    parser.add_argument("--scenario", default="01_simple_scheduling", help="Scenario ID")
    parser.add_argument(
        "--no-evaluate",
        action="store_true",
        help="Skip the bug evaluator step",
    )
    args = parser.parse_args()
    run_pipeline(args.scenario, run_eval=not args.no_evaluate)
