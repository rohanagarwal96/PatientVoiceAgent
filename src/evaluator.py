import argparse
import json
import os
import re
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from openai import AzureOpenAI
from pydantic import BaseModel

from src.scenarios import Scenario, get_scenario

_REPORT_PATH = Path(__file__).parent.parent / "bug_report.md"


class Finding(BaseModel):
    title: str
    severity: Literal["low", "medium", "high", "critical"]
    severity_justification: str
    scenario_id: str
    call_sid: str
    timestamp: str
    evidence_quote: str
    description: str
    confidence: Literal["low", "medium", "high"]
    possible_state_artifact: bool


def _fmt_ts(seconds: float) -> str:
    mm = int(seconds) // 60
    ss = int(seconds) % 60
    return f"{mm:02d}:{ss:02d}"


def _validate_timestamp(ts: str, max_seconds: float) -> str:
    """Flag a timestamp that exceeds the call duration so it never reaches the report silently."""
    try:
        mm, ss = ts.split(":")
        total = int(mm) * 60 + int(ss)
        if total > max_seconds + 30:
            return f"{ts} [WARNING: exceeds call duration {_fmt_ts(max_seconds)}]"
    except (ValueError, AttributeError):
        return f"[unparseable timestamp: {ts}]"
    return ts


def _extract_call_sid(json_path: Path) -> str:
    parts = json_path.stem.rsplit("_", 1)
    return parts[-1] if len(parts) > 1 else "unknown"


def _build_prompt(transcript: list[dict], scenario: Scenario, call_sid: str) -> str:
    duration = max((s.get("end", s["start"]) for s in transcript), default=0.0) if transcript else 0.0
    lines = "\n".join(
        f"[{_fmt_ts(s['start'])}] {s['speaker']}: {s['text']}" for s in transcript
    )
    return f"""You are a QA evaluator assessing the performance of a healthcare voice scheduling agent.

Context:
- Scenario: {scenario.id} — {scenario.name}
- Known failure mode to watch for: {scenario.trap}
- Call SID: {call_sid}
- Call duration: approximately {_fmt_ts(duration)}
- Transcript key: AGENT = the scheduling agent under evaluation (called party); PATIENT = the automated test caller

Transcript (MM:SS):
{lines}

---
Your task: identify REAL bugs in the AGENT's behavior — things a competent human scheduling agent should NOT do.

DO NOT flag:
- Behavior that is reasonable even if it deviates from the test script (e.g., not asking for insurance for a quick booking may be fine in context).
- The AGENT recalling or referencing prior-call history for a returning patient — our test line reuses the same caller ID, so the agent may have real memory of prior appointments. Responding to that memory is NOT a bug.
- Anything the PATIENT (test caller) did wrong — only evaluate the AGENT.
- Test-environment artifacts (e.g., transfer reaching a test line saying "Goodbye" is not a real transfer failure).

DO flag:
- Booking appointments outside business hours or making false promises about availability.
- Giving incorrect, contradictory, or fabricated information (wrong hours, wrong locations, hallucinated coverage).
- Promising a controlled-substance refill without routing to provider review.
- Looping on the same question after the caller clearly answered it — include specific counts and duration.
- Failing to confirm a cancellation explicitly (acknowledging is not confirming).
- Failing to route clear emergency symptoms to emergency services.
- Any other clear competency failure that a reasonable scheduling agent should not make.

For each real bug, output a JSON object with EXACTLY these fields:
{{
  "title": "Precise, specific title — what went wrong (not a vague category)",
  "severity": "low | medium | high | critical",
  "severity_justification": "One sentence explaining why this severity",
  "scenario_id": "{scenario.id}",
  "call_sid": "{call_sid}",
  "timestamp": "MM:SS — copy DIRECTLY from the transcript line where the failure begins",
  "evidence_quote": "1-3 lines from the transcript showing the failure (exact or close paraphrase)",
  "description": "What happened: [specifics with counts where relevant]. Why it is a problem: [impact]. What should have happened: [correct behavior].",
  "confidence": "high (certain real bug) | medium (may be state artifact or script deviation) | low (speculative)",
  "possible_state_artifact": true if this might be explained by the agent's memory of a prior call from this number; false otherwise
}}

Output a JSON array. If no real bugs are found, output [].
IMPORTANT: Copy MM:SS timestamps verbatim from the transcript. Do not compute or convert them."""


def evaluate(transcript_path: Path, scenario_id: str, dry_run: bool = False) -> list[Finding]:
    """Run LLM evaluation with human gate. Returns confirmed findings.

    dry_run: print candidates and return them without prompting or writing to report.
    """
    load_dotenv()
    scenario = get_scenario(scenario_id)
    call_sid = _extract_call_sid(transcript_path)

    with transcript_path.open(encoding="utf-8") as f:
        transcript = json.load(f)

    duration = max((s.get("end", s["start"]) for s in transcript), default=0.0) if transcript else 0.0

    client = AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
        api_version="2024-08-01-preview",
    )
    deployment = os.getenv("AZURE_OPENAI_EVAL_DEPLOYMENT", "gpt-4o")

    prompt = _build_prompt(transcript, scenario, call_sid)
    response = client.chat.completions.create(
        model=deployment,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)

    raw_items = json.loads(raw)
    candidates: list[Finding] = []
    for item in raw_items:
        item["timestamp"] = _validate_timestamp(item.get("timestamp", "?"), duration)
        candidates.append(Finding(**item))

    if not candidates:
        print("[evaluator] No bugs found.", flush=True)
        return []

    if dry_run:
        print(f"\n[evaluator] DRY RUN — {len(candidates)} candidate(s) for {scenario_id} / {call_sid}\n")
        for i, finding in enumerate(candidates, 1):
            _print_finding(finding, index=i)
        return candidates

    confirmed: list[Finding] = []
    for finding in candidates:
        _print_finding(finding)
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


def _print_finding(finding: Finding, index: int = 0) -> None:
    prefix = f"--- Candidate {index} ---" if index else "--- Candidate Finding ---"
    artifact = "YES (possible state artifact)" if finding.possible_state_artifact else "no"
    print(f"\n{prefix}")
    print(f"Title:        {finding.title}")
    print(f"Severity:     {finding.severity} -- {finding.severity_justification}")
    print(f"Timestamp:    {finding.timestamp}")
    print(f"Confidence:   {finding.confidence}")
    print(f"State artifact: {artifact}")
    print(f"Evidence:     {finding.evidence_quote}")
    print(f"Description:  {finding.description}")


def _append_to_report(findings: list[Finding]) -> None:
    existing = ""
    if _REPORT_PATH.exists():
        existing = _REPORT_PATH.read_text(encoding="utf-8", errors="replace")
    bug_count = existing.count("## Bug ")

    new_content = existing
    for finding in findings:
        bug_count += 1
        artifact_flag = "  *(possible state artifact)*" if finding.possible_state_artifact else ""
        new_content += f"\n## Bug {bug_count} — {finding.title} · severity: {finding.severity}\n"
        new_content += f"**Scenario:** {finding.scenario_id}  \n"
        new_content += f"**Call SID:** {finding.call_sid}  \n"
        new_content += f"**Timestamp:** {finding.timestamp}  \n"
        new_content += f"**Confidence:** {finding.confidence}{artifact_flag}  \n"
        new_content += f"**Severity justification:** {finding.severity_justification}  \n\n"
        new_content += f"**Evidence:** {finding.evidence_quote}\n\n"
        new_content += f"{finding.description}\n"

    _REPORT_PATH.write_text(new_content, encoding="utf-8")
    print(f"[evaluator] appended {len(findings)} finding(s) to {_REPORT_PATH}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--transcript", required=True, help="Path to transcript .json file")
    parser.add_argument("--scenario", required=True, help="Scenario ID")
    parser.add_argument("--dry-run", action="store_true", help="Print candidates only; do not prompt or write report")
    args = parser.parse_args()

    confirmed = evaluate(Path(args.transcript), args.scenario, dry_run=args.dry_run)
    if not args.dry_run:
        print(f"[evaluator] {len(confirmed)} finding(s) confirmed")
