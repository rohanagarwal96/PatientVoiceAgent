import argparse

from src.evaluator import evaluate
from src.recorder import fetch_recording
from src.scenarios import SCENARIOS, get_chain, get_scenario
from src.transcriber import transcribe
from src.trigger import place_call


def run_pipeline(scenario_id: str, run_eval: bool = True) -> None:
    """Place one call, fetch recording, transcribe, and optionally evaluate."""
    call_sid = place_call(scenario_id)
    recording_path = fetch_recording(call_sid, scenario_id)
    _, json_path = transcribe(recording_path)
    if run_eval:
        evaluate(json_path, scenario_id)


def run_chain(run_eval: bool = True) -> None:
    """Run chained scenarios in order, pausing for confirmation between each call."""
    chain = get_chain()
    if not chain:
        print("[pipeline] No chained scenarios defined.", flush=True)
        return

    print("[pipeline] Appointment-lifecycle chain:", flush=True)
    for s in chain:
        dep = f"  (depends on {s.depends_on})" if s.depends_on else "  (chain start)"
        print(f"  {s.order}. {s.id} — {s.name}{dep}", flush=True)
    print(flush=True)

    for i, scenario in enumerate(chain):
        if i > 0:
            try:
                input(f"Press Enter to run scenario {scenario.order} ({scenario.id}) or Ctrl+C to stop: ")
            except KeyboardInterrupt:
                print("\n[pipeline] Chain stopped.", flush=True)
                return
        if scenario.depends_on:
            print(
                f"[pipeline] Note: {scenario.id} depends on {scenario.depends_on} having run "
                "successfully in a prior call. If you are re-running this scenario alone, "
                f"make sure {scenario.depends_on} was already completed.",
                flush=True,
            )
        run_pipeline(scenario.id, run_eval=run_eval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run a single PatientVoiceAgent scenario, or step through the chained sequence."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--scenario", help="Scenario ID to run (primary mode)")
    group.add_argument(
        "--chain",
        action="store_true",
        help="Run the chained appointment-lifecycle scenarios in order, pausing between each",
    )
    parser.add_argument("--no-evaluate", action="store_true", help="Skip the bug evaluator step")
    args = parser.parse_args()

    run_eval = not args.no_evaluate
    if args.chain:
        run_chain(run_eval=run_eval)
    else:
        run_pipeline(args.scenario, run_eval=run_eval)
