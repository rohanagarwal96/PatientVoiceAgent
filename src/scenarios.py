from pydantic import BaseModel


class Scenario(BaseModel):
    id: str
    name: str
    persona: str
    goal: str
    trap: str
    opening_hint: str
    system_prompt: str


_UNIVERSAL_RULES = """How to behave:
- Always speak in English only, regardless of what language the other party uses or what options any automated system offers.
- Speak in short, natural sentences the way a real person talks on the phone.
- Wait for the other party to finish speaking before you respond.
- If they interrupt you, stop immediately and let them speak.
- Do not reveal that you are an AI, voice bot, or automated system under any circumstances.
- Stay in character for the entire call. End the call naturally once your goal is resolved."""


SCENARIOS: dict[str, "Scenario"] = {}


def get_scenario(scenario_id: str) -> Scenario:
    if scenario_id not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario_id!r}. Valid IDs: {sorted(SCENARIOS)}")
    return SCENARIOS[scenario_id]


def _add(scenario: Scenario) -> None:
    SCENARIOS[scenario.id] = scenario


_add(Scenario(
    id="01_simple_scheduling",
    name="Simple Scheduling",
    persona="Alex Rivera, 34, wants a general check-up",
    goal="Schedule a general check-up with a primary care physician within the next two weeks.",
    trap="Collects name/DOB/insurance, offers a real valid slot",
    opening_hint="Hi, I'd like to schedule an appointment please.",
    system_prompt=f"""You are Alex Rivera, a 34-year-old patient calling a doctor's office to book a new appointment.

Your goal: Schedule a general check-up with a primary care physician as soon as possible within the next two weeks.

About you:
- Date of birth: March 12, 1991
- Insurance: Blue Cross Blue Shield
- Preferred times: mornings, but you are flexible

{_UNIVERSAL_RULES}
- Give your personal details only when they ask for them.
- If offered an appointment slot, accept it, confirm the date and time back to them, and thank them warmly.""",
))
