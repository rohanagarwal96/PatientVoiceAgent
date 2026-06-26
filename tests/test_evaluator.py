import os

os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com")
os.environ.setdefault("AZURE_OPENAI_API_KEY", "test_key")
os.environ.setdefault("AZURE_OPENAI_EVAL_DEPLOYMENT", "gpt-4o")

from pathlib import Path
from unittest.mock import patch

import pytest

from src.evaluator import Finding, _append_to_report, _build_prompt, _extract_call_sid, _fmt_ts, _validate_timestamp
from src.scenarios import get_scenario


def _make_finding(**overrides) -> Finding:
    defaults = dict(
        title="Test finding",
        severity="medium",
        severity_justification="Moderate impact on patient experience.",
        scenario_id="01_simple_scheduling",
        call_sid="CAtest",
        timestamp="00:30",
        evidence_quote="AGENT: Sorry, could you spell that again?",
        description="What happened: agent looped. Why it's a problem: frustrating. What should have happened: accepted the spelling.",
        confidence="high",
        possible_state_artifact=False,
    )
    defaults.update(overrides)
    return Finding(**defaults)


def test_finding_rejects_invalid_severity():
    with pytest.raises(Exception):
        _make_finding(severity="extreme")


def test_finding_accepts_all_valid_severities():
    for sev in ("low", "medium", "high", "critical"):
        f = _make_finding(severity=sev)
        assert f.severity == sev


def test_finding_accepts_all_valid_confidences():
    for conf in ("low", "medium", "high"):
        f = _make_finding(confidence=conf)
        assert f.confidence == conf


def test_extract_call_sid_from_filename():
    path = Path("transcripts/01_simple_scheduling_20260625_120000_CAabc123.json")
    assert _extract_call_sid(path) == "CAabc123"


def test_fmt_ts_formats_seconds_correctly():
    assert _fmt_ts(0.0) == "00:00"
    assert _fmt_ts(65.44) == "01:05"
    assert _fmt_ts(127.7) == "02:07"
    assert _fmt_ts(317.1) == "05:17"


def test_validate_timestamp_passes_valid():
    assert _validate_timestamp("01:05", 200.0) == "01:05"


def test_validate_timestamp_flags_impossible():
    result = _validate_timestamp("65:54", 130.0)
    assert "WARNING" in result or "exceeds" in result.lower()


def test_append_to_report_creates_file(tmp_path):
    report = tmp_path / "bug_report.md"
    findings = [
        _make_finding(
            title="Agent did not confirm cancellation",
            severity="high",
            scenario_id="04_cancel",
            call_sid="CAtest",
            timestamp="01:23",
        )
    ]
    with patch("src.evaluator._REPORT_PATH", report):
        _append_to_report(findings)

    content = report.read_text(encoding="utf-8")
    assert "## Bug 1" in content
    assert "severity: high" in content
    assert "CAtest" in content
    assert "01:23" in content
    assert "Confidence:" in content
    assert "Evidence:" in content


def test_append_to_report_increments_bug_number(tmp_path):
    report = tmp_path / "bug_report.md"
    report.write_text("## Bug 1 — Prior Bug · severity: low\n**Scenario:** 01\n\ndesc\n")
    findings = [
        _make_finding(
            title="New Bug",
            severity="medium",
            scenario_id="05_controlled_substance",
            call_sid="CAtest2",
            timestamp="00:45",
        )
    ]
    with patch("src.evaluator._REPORT_PATH", report):
        _append_to_report(findings)

    content = report.read_text(encoding="utf-8")
    assert "## Bug 2" in content


def test_build_prompt_includes_trap_and_scenario():
    scenario = get_scenario("01_simple_scheduling")
    prompt = _build_prompt([], scenario, "CAtest")
    assert "01_simple_scheduling" in prompt
    assert scenario.trap in prompt


def test_build_prompt_uses_mm_ss_timestamps():
    transcript = [{"speaker": "AGENT", "start": 65.44, "end": 68.0, "text": "You already have an appointment."}]
    scenario = get_scenario("01_simple_scheduling")
    prompt = _build_prompt(transcript, scenario, "CAtest")
    assert "[01:05]" in prompt
    assert "65.44" not in prompt
