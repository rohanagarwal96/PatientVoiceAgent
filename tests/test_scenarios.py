import pytest
from src.scenarios import PATIENT_PROFILE, PatientProfile, Scenario, get_chain, get_scenario, SCENARIOS


def test_patient_profile_has_required_fields():
    assert PATIENT_PROFILE.name
    assert PATIENT_PROFILE.date_of_birth
    assert PATIENT_PROFILE.insurance
    assert PATIENT_PROFILE.preferred_pharmacy


def test_patient_profile_is_alex_rivera():
    assert PATIENT_PROFILE.name == "Alex Rivera"
    assert "1991" in PATIENT_PROFILE.date_of_birth


def test_scenario_model_fields():
    s = Scenario(
        id="test",
        name="Test",
        call_reason="Test the agent",
        goal="Complete the test",
        trap="Test trap",
        opening_hint="Hello",
    )
    assert s.id == "test"
    assert s.call_reason == "Test the agent"
    assert s.order is None
    assert s.depends_on is None


def test_scenario_default_strategy_is_lean_into_memory():
    s = Scenario(
        id="test",
        name="Test",
        call_reason="Test the agent",
        goal="Complete the test",
        trap="Test trap",
        opening_hint="Hello",
    )
    assert s.returning_patient_strategy == "lean_into_memory"


def test_get_system_prompt_includes_patient_name():
    s = get_scenario("01_simple_scheduling")
    prompt = s.get_system_prompt()
    assert "Alex Rivera" in prompt


def test_get_system_prompt_includes_profile_details():
    s = get_scenario("01_simple_scheduling")
    prompt = s.get_system_prompt()
    assert PATIENT_PROFILE.date_of_birth in prompt
    assert PATIENT_PROFILE.insurance in prompt


def test_get_system_prompt_includes_call_reason():
    s = get_scenario("01_simple_scheduling")
    prompt = s.get_system_prompt()
    assert s.call_reason in prompt


def test_get_system_prompt_includes_returning_patient_section():
    s = get_scenario("01_simple_scheduling")
    prompt = s.get_system_prompt()
    assert "Returning patient awareness" in prompt


def test_get_system_prompt_correct_the_record_text():
    s = get_scenario("01_simple_scheduling")
    assert s.returning_patient_strategy == "correct_the_record"
    prompt = s.get_system_prompt()
    assert "correct the record" in prompt.lower() or "gently push back" in prompt.lower()


def test_get_system_prompt_includes_call_context():
    s = get_scenario("05_controlled_substance")
    assert s.call_context
    prompt = s.get_system_prompt()
    assert s.call_context in prompt


def test_01_simple_scheduling_uses_correct_the_record():
    s = get_scenario("01_simple_scheduling")
    assert s.returning_patient_strategy == "correct_the_record"


def test_get_scenario_returns_correct_scenario():
    s = get_scenario("01_simple_scheduling")
    assert s.id == "01_simple_scheduling"
    assert s.call_reason
    assert s.goal
    assert s.trap


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
        assert s.call_reason, f"{sid} missing call_reason"
        assert s.goal, f"{sid} missing goal"
        assert s.trap, f"{sid} missing trap"
        prompt = s.get_system_prompt()
        assert "Alex Rivera" in prompt, f"{sid} prompt missing patient name"
        assert "Returning patient awareness" in prompt, f"{sid} missing returning-patient section"


def test_scenarios_dict_has_exactly_12():
    assert len(SCENARIOS) == 12


def test_chained_scenarios():
    chain = get_chain()
    assert len(chain) == 3
    ids = [s.id for s in chain]
    assert ids == ["01_simple_scheduling", "03_reschedule", "04_cancel"]


def test_chain_order_is_correct():
    chain = get_chain()
    orders = [s.order for s in chain]
    assert orders == sorted(orders)
    assert chain[0].depends_on is None
    assert chain[1].depends_on == "01_simple_scheduling"
    assert chain[2].depends_on == "03_reschedule"


def test_standalone_scenarios_have_no_order():
    standalone_ids = {"02_after_hours", "05_controlled_substance", "06_refill_no_pharmacy",
                      "07_unverifiable_insurance", "08_location_hours", "09_barge_in",
                      "10_unclear_mind_change", "11_multi_intent", "12_emergency"}
    for sid in standalone_ids:
        s = get_scenario(sid)
        assert s.order is None, f"{sid} should be standalone (order=None)"
        assert s.depends_on is None, f"{sid} should have no depends_on"
