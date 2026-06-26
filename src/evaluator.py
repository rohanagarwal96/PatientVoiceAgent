import argparse
import json
import os
import re
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from openai import AzureOpenAI
from pydantic import BaseModel

from src.scenarios import get_scenario

_REPORT_PATH = Path(__file__).parent.parent / "bug_report.md"


class Finding(BaseModel):
    title: str
    severity: Literal["low", "medium", "high", "critical"]
    scenario_id: str
    call_sid: str
    timestamp: str
    description: str


def _extract_call_sid(json_path: Path) -> str:
    parts = json_path.stem.rsplit("_", 1)
    return parts[-1] if len(parts) > 1 else "unknown"


def _build_prompt(transcript: list[dict], trap: str, scenario_id: str, call_sid: str) -> str:
    lines = "\n".join(
        f"[{s['start']:.1f}s] {s['speaker']}: {s['text']}" for s in transcript
    )
    return f"""You are a QA evaluator for a healthcare AI voice agent.

Scenario ID: {scenario_id}
Call SID: {call_sid}
Known trap (what the agent MUST do correctly): {trap}

Transcript:
{lines}

Identify any bugs or failures where the agent did NOT handle the situation correctly.
For each bug, respond with a JSON array of objects with these exact fields:
- title: short bug title
- severity: one of "low", "medium", "high", "critical"
- scenario_id: "{scenario_id}"
- call_sid: "{call_sid}"
- timestamp: "MM:SS" of when the failure occurs
- description: 1-2 sentences explaining what went wrong

If no bugs are found, respond with an empty array [].
Respond with ONLY the JSON array, no other text."""


def evaluate(transcript_path: Path, scenario_id: str) -> list[Finding]:
    """Run LLM evaluation with human gate. Returns confirmed findings."""
    load_dotenv()
    scenario = get_scenario(scenario_id)
    call_sid = _extract_call_sid(transcript_path)

    with transcript_path.open(encoding="utf-8") as f:
        transcript = json.load(f)

    client = AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
        api_version="2024-08-01-preview",
    )
    deployment = os.getenv("AZURE_OPENAI_EVAL_DEPLOYMENT", "gpt-4o")

    prompt = _build_prompt(transcript, scenario.trap, scenario_id, call_sid)
    response = client.chat.completions.create(
        model=deployment,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)

    candidates = [Finding(**item) for item in json.loads(raw)]
    if not candidates:
        print("[evaluator] No bugs found.", flush=True)
        return []

    confirmed: list[Finding] = []
    for finding in candidates:
        print(f"\n--- Candidate Finding ---")
        print(f"Title:       {finding.title}")
        print(f"Severity:    {finding.severity}")
        print(f"Timestamp:   {finding.timestamp}")
        print(f"Description: {finding.description}")
        choice = input("[k]eep / [e]dit / [d]rop: ").strip().lower()

        if choice == "k":
            confirmed.append(finding)
        elif choice == "e":
            new_desc = input(f"New description [{finding.description}]: ").strip()
            if new_desc:
                finding = finding.model_copy(update={"description": new_desc})
            new_sev = input(f"New severity [{finding.severity}]: ").strip().lower()
            if new_sev in ("low", "medium", "high", "critical"):
                finding = finding.model_copy(update={"severity": new_sev})
            confirmed.append(finding)
        # "d" or anything else: drop

    if confirmed:
        _append_to_report(confirmed)

    return confirmed


def _append_to_report(findings: list[Finding]) -> None:
    existing = ""
    if _REPORT_PATH.exists():
        existing = _REPORT_PATH.read_text(encoding="utf-8", errors="replace")
    bug_count = existing.count("## Bug ")

    new_content = existing
    for finding in findings:
        bug_count += 1
        new_content += f"\n## Bug {bug_count} — {finding.title} · severity: {finding.severity}\n"
        new_content += f"**Scenario:** {finding.scenario_id}\n"
        new_content += f"**Call SID:** {finding.call_sid}\n"
        new_content += f"**Timestamp:** {finding.timestamp}\n\n"
        new_content += f"{finding.description}\n"

    _REPORT_PATH.write_text(new_content, encoding="utf-8")
    print(f"[evaluator] appended {len(findings)} finding(s) to {_REPORT_PATH}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--transcript", required=True, help="Path to transcript .json file")
    parser.add_argument("--scenario", required=True, help="Scenario ID")
    args = parser.parse_args()

    confirmed = evaluate(Path(args.transcript), args.scenario)
    print(f"[evaluator] {len(confirmed)} finding(s) confirmed")
