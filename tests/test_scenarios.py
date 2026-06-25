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


def test_get_scenario_returns_correct_scenario():
    s = get_scenario("01_simple_scheduling")
    assert s.id == "01_simple_scheduling"
    assert len(s.system_prompt) > 50


def test_get_scenario_raises_on_unknown_id():
    with pytest.raises(ValueError, match="Unknown scenario"):
        get_scenario("99_nonexistent")


def test_scenarios_dict_has_01():
    assert "01_simple_scheduling" in SCENARIOS
