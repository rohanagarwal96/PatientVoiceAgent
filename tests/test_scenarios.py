import pytest
from src.scenarios import Scenario, get_scenario, SCENARIOS


def test_scenario_model_fields():
    s = Scenario(
        id="test",
        name="Test",
        persona="A test patient",
        goal="Test goal",
        trap="Test trap",
        opening_hint="Hello",
        system_prompt="You are a test patient.",
    )
    assert s.id == "test"
    assert s.system_prompt == "You are a test patient."


def test_scenario_default_strategy_is_lean_into_memory():
    s = Scenario(
        id="test",
        name="Test",
        persona="A test patient",
        goal="Test goal",
        trap="Test trap",
        opening_hint="Hello",
        system_prompt="You are a test patient.",
    )
    assert s.returning_patient_strategy == "lean_into_memory"


def test_get_system_prompt_appends_returning_patient_section():
    s = Scenario(
        id="test",
        name="Test",
        persona="A test patient",
        goal="Test goal",
        trap="Test trap",
        opening_hint="Hello",
        system_prompt="You are a test patient.",
        returning_patient_strategy="lean_into_memory",
    )
    full = s.get_system_prompt()
    assert full.startswith("You are a test patient.")
    assert "Returning patient awareness" in full
    assert "lean into the memory" in full.lower() or "lean" in full.lower()


def test_correct_the_record_strategy_text():
    s = Scenario(
        id="test",
        name="Test",
        persona="A test patient",
        goal="Test goal",
        trap="Test trap",
        opening_hint="Hello",
        system_prompt="Base prompt.",
        returning_patient_strategy="correct_the_record",
    )
    full = s.get_system_prompt()
    assert "correct the record" in full.lower() or "correct" in full.lower()
    assert "don't think I have anything booked" in full or "gently push back" in full


def test_01_simple_scheduling_uses_correct_the_record():
    s = get_scenario("01_simple_scheduling")
    assert s.returning_patient_strategy == "correct_the_record"


def test_get_scenario_returns_correct_scenario():
    s = get_scenario("01_simple_scheduling")
    assert s.id == "01_simple_scheduling"
    assert len(s.system_prompt) > 50


def test_get_scenario_raises_on_unknown_id():
    with pytest.raises(ValueError, match="Unknown scenario"):
        get_scenario("99_nonexistent")


def test_scenarios_dict_has_01():
    assert "01_simple_scheduling" in SCENARIOS


_ALL_IDS = [
    "01_simple_scheduling",
    "02_after_hours",
    "03_reschedule",
    "04_cancel",
    "05_controlled_substance",
    "06_refill_no_pharmacy",
    "07_unverifiable_insurance",
    "08_location_hours",
    "09_barge_in",
    "10_unclear_mind_change",
    "11_multi_intent",
    "12_emergency",
]


def test_all_12_scenarios_resolve():
    for sid in _ALL_IDS:
        s = get_scenario(sid)
        assert s.id == sid
        assert len(s.system_prompt) > 100, f"{sid} system_prompt too short"
        assert s.trap, f"{sid} missing trap"
        full = s.get_system_prompt()
        assert "Returning patient awareness" in full, f"{sid} missing returning-patient section"


def test_scenarios_dict_has_exactly_12():
    assert len(SCENARIOS) == 12
