import os

os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com")
os.environ.setdefault("AZURE_OPENAI_API_KEY", "test_key")
os.environ.setdefault("AZURE_OPENAI_EVAL_DEPLOYMENT", "gpt-4o")

from pathlib import Path
from unittest.mock import patch

import pytest

from src.evaluator import Finding, _append_to_report, _build_prompt, _extract_call_sid
from src.scenarios import get_scenario


def test_finding_rejects_invalid_severity():
    with pytest.raises(Exception):
        Finding(
            title="Test",
            severity="extreme",
            scenario_id="01_simple_scheduling",
            call_sid="CAtest",
            timestamp="00:30",
            description="desc",
        )


def test_finding_accepts_all_valid_severities():
    for sev in ("low", "medium", "high", "critical"):
        f = Finding(
            title="Test",
            severity=sev,
            scenario_id="01_simple_scheduling",
            call_sid="CAtest",
            timestamp="00:30",
            description="desc",
        )
        assert f.severity == sev


def test_extract_call_sid_from_filename():
    path = Path("transcripts/01_simple_scheduling_20260625_120000_CAabc123.json")
    assert _extract_call_sid(path) == "CAabc123"


def test_append_to_report_creates_file(tmp_path):
    report = tmp_path / "bug_report.md"
    findings = [
        Finding(
            title="Agent did not confirm cancellation",
            severity="high",
            scenario_id="04_cancel",
            call_sid="CAtest",
            timestamp="01:23",
            description="The agent acknowledged but never confirmed cancellation.",
        )
    ]
    with patch("src.evaluator._REPORT_PATH", report):
        _append_to_report(findings)

    content = report.read_text(encoding="utf-8")
    assert "## Bug 1" in content
    assert "severity: high" in content
    assert "CAtest" in content
    assert "01:23" in content


def test_append_to_report_increments_bug_number(tmp_path):
    report = tmp_path / "bug_report.md"
    report.write_text("## Bug 1 — Prior Bug · severity: low\n**Scenario:** 01\n\ndesc\n")
    findings = [
        Finding(
            title="New Bug",
            severity="medium",
            scenario_id="05_controlled_substance",
            call_sid="CAtest2",
            timestamp="00:45",
            description="Agent promised refill without routing to provider review.",
        )
    ]
    with patch("src.evaluator._REPORT_PATH", report):
        _append_to_report(findings)

    content = report.read_text(encoding="utf-8")
    assert "## Bug 2" in content


def test_build_prompt_includes_trap_and_scenario():
    scenario = get_scenario("01_simple_scheduling")
    prompt = _build_prompt([], scenario.trap, "01_simple_scheduling", "CAtest")
    assert "01_simple_scheduling" in prompt
    assert scenario.trap in prompt
