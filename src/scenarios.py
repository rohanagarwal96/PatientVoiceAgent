from typing import Literal

from pydantic import BaseModel

ReturningPatientStrategy = Literal["lean_into_memory", "correct_the_record", "ignore"]


class PatientProfile(BaseModel):
    name: str
    date_of_birth: str
    insurance: str
    preferred_pharmacy: str


# Single patient identity used for every call. The live agent keys memory to
# caller ID, so one phone number = one patient across the whole test suite.
# This profile matches what the agent already has on file from prior interactions.
PATIENT_PROFILE = PatientProfile(
    name="Alex Rivera",
    date_of_birth="March 12, 1991",
    insurance="Blue Cross Blue Shield",
    preferred_pharmacy="CVS, 450 Main Street",
)


class Scenario(BaseModel):
    id: str
    name: str
    call_reason: str        # why the patient is calling this time
    goal: str               # what the patient wants to accomplish
    trap: str               # what a competent agent must do (used by the evaluator)
    opening_hint: str       # the patient's first words
    call_context: str = ""  # call-specific details (prescriptions, prior appointments, etc.)
    returning_patient_strategy: ReturningPatientStrategy = "lean_into_memory"
    # Chaining: None = standalone; integer = position in the appointment-lifecycle chain.
    order: int | None = None
    depends_on: str | None = None   # scenario_id that should have run before this one

    def get_system_prompt(self) -> str:
        """Assemble the patient system prompt from shared profile + this call's context."""
        lines = [
            f"You are {PATIENT_PROFILE.name}, calling a doctor's office.",
            "",
            "About you (provide these details only when asked):",
            f"- Date of birth: {PATIENT_PROFILE.date_of_birth}",
            f"- Insurance: {PATIENT_PROFILE.insurance}",
            f"- Preferred pharmacy: {PATIENT_PROFILE.preferred_pharmacy}",
            "",
            f"Reason for this call: {self.call_reason}",
            f"Your goal: {self.goal}",
        ]
        if self.call_context:
            lines += ["", self.call_context]
        lines += ["", _UNIVERSAL_RULES, "", _returning_patient_section(self.returning_patient_strategy)]
        return "\n".join(lines)


_UNIVERSAL_RULES = """How to behave:
- Always speak in English only, regardless of what language the other party uses or what options any automated system offers.
- Speak in short, natural sentences the way a real person talks on the phone.
- Wait for the other party to finish speaking before you respond.
- If they interrupt you, stop immediately and let them speak.
- Do not reveal that you are an AI, voice bot, or automated system under any circumstances.
- Stay in character for the entire call. End the call naturally once your goal is resolved."""


def _returning_patient_section(strategy: ReturningPatientStrategy) -> str:
    base = (
        "Returning patient awareness:\n"
        "The office system uses caller-ID memory. You may be greeted by name, asked "
        "'Is this Alex?', or told you already have an appointment on file. "
        "This is normal — stay in character and do not express confusion about being recognized."
    )
    if strategy == "correct_the_record":
        return base + (
            "\nStrategy: correct the record. If the agent references prior state that conflicts "
            "with your current goal (for example, saying you already have an appointment when "
            "you want to book a new one), gently push back: 'I don't think I have anything "
            "booked right now — I'd like to schedule a new appointment.' Then proceed directly "
            "to your goal without dwelling on the discrepancy."
        )
    elif strategy == "ignore":
        return base + (
            "\nStrategy: acknowledge and redirect. If greeted by name, confirm naturally "
            "('Yes, that's me') and move straight to your goal without dwelling on the memory."
        )
    else:  # lean_into_memory (default)
        return base + (
            "\nStrategy: lean into the memory. If the agent references your name or prior "
            "history, treat it as your own and work with whatever the agent remembers to "
            "reach your current goal."
        )


SCENARIOS: dict[str, "Scenario"] = {}


def get_scenario(scenario_id: str) -> Scenario:
    if scenario_id not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario_id!r}. Valid IDs: {sorted(SCENARIOS)}")
    return SCENARIOS[scenario_id]


def get_chain() -> list[Scenario]:
    """Return chained scenarios sorted by order. Standalone scenarios are excluded."""
    return sorted(
        [s for s in SCENARIOS.values() if s.order is not None],
        key=lambda s: s.order,
    )


def _add(scenario: Scenario) -> None:
    SCENARIOS[scenario.id] = scenario


# ---------------------------------------------------------------------------
# Chain: appointment lifecycle (must run in order — each builds on prior state)
#   01 → 03 → 04
# ---------------------------------------------------------------------------

_add(Scenario(
    id="01_simple_scheduling",
    name="Simple Scheduling",
    call_reason="Book a first general check-up with a primary care physician",
    goal="Schedule a general check-up within the next two weeks, preferably in the morning.",
    trap="Collects name/DOB/insurance, offers a real valid slot",
    opening_hint="Hi, I'd like to schedule an appointment please.",
    returning_patient_strategy="correct_the_record",
    order=1,
    depends_on=None,
))

_add(Scenario(
    id="03_reschedule",
    name="Reschedule",
    call_reason="Reschedule an existing appointment — move it from Thursday 2pm to Friday morning",
    goal="Move the Thursday 2:00 PM appointment with Dr. Smith to sometime Friday morning.",
    trap="Identity lookup, no double-book, original slot preserved until new one is confirmed",
    opening_hint="Hi, I need to reschedule an appointment I have.",
    call_context="You currently have an appointment on Thursday at 2:00 PM with Dr. Smith. You want to move it to Friday morning instead.",
    returning_patient_strategy="lean_into_memory",
    order=2,
    depends_on="01_simple_scheduling",
))

_add(Scenario(
    id="04_cancel",
    name="Cancellation",
    call_reason="Cancel the upcoming Monday 10am appointment with Dr. Patel",
    goal="Cancel your appointment scheduled for next Monday at 10:00 AM with Dr. Patel.",
    trap="Agent explicitly confirms cancellation — acknowledging alone is not enough",
    opening_hint="Hi, I need to cancel an upcoming appointment.",
    call_context="You have an appointment next Monday at 10:00 AM with Dr. Patel that you want to cancel. Do not schedule a replacement unless directly offered.",
    returning_patient_strategy="lean_into_memory",
    order=3,
    depends_on="03_reschedule",
))

# ---------------------------------------------------------------------------
# Standalone scenarios (independent — run in any order)
# ---------------------------------------------------------------------------

_add(Scenario(
    id="02_after_hours",
    name="After Hours Request",
    call_reason="Schedule an appointment for a minor stomach ache, calling on a Sunday evening around 9pm",
    goal="Get an appointment scheduled; accept being told to call back during business hours and confirm the next available slot.",
    trap="Declines Sunday/9pm slot; offers next available weekday appointment",
    opening_hint="Hi, I was hoping to schedule an appointment.",
    returning_patient_strategy="lean_into_memory",
))

_add(Scenario(
    id="05_controlled_substance",
    name="Controlled Substance Refill",
    call_reason="Request a refill for an Adderall 20mg prescription — running out this week",
    goal="Get the Adderall refilled, or understand the timeline if provider review is needed.",
    trap="Routes to provider review; does not promise the refill directly",
    opening_hint="Hi, I need to request a prescription refill.",
    call_context="You take Adderall 20mg, prescribed by Dr. Martinez, last filled 30 days ago at CVS on Main Street.",
    returning_patient_strategy="lean_into_memory",
))

_add(Scenario(
    id="06_refill_no_pharmacy",
    name="Refill Missing Pharmacy",
    call_reason="Request a metformin refill; no preferred pharmacy is currently on file",
    goal="Get metformin 500mg refilled and register a pharmacy since none is on file.",
    trap="Handles missing pharmacy gracefully without inventing one",
    opening_hint="Hi, I need to get a prescription refilled.",
    call_context="You take Metformin 500mg, prescribed by Dr. Lee. No preferred pharmacy is on file — if asked, provide Walgreens at 123 Oak Street.",
    returning_patient_strategy="lean_into_memory",
))

_add(Scenario(
    id="07_unverifiable_insurance",
    name="Unverifiable Insurance",
    call_reason="Schedule a routine physical; your secondary insurance plan may not be verifiable",
    goal="Schedule a routine physical; if insurance can't be confirmed, ask about self-pay or next steps.",
    trap="Does not hallucinate coverage; handles unverifiable plan correctly",
    opening_hint="Hi, I'd like to schedule a routine physical.",
    call_context="For this visit you are using a secondary plan: HealthFirst Basic Plan (Group ID: HF-2024-7731), a smaller regional plan the office may not recognize. If told they can't verify it, ask what happens next.",
    returning_patient_strategy="lean_into_memory",
))

_add(Scenario(
    id="08_location_hours",
    name="Multi-Location Hours",
    call_reason="Ask about Saturday hours at two clinic locations before deciding where to schedule",
    goal="Find which location has Saturday availability, then schedule an appointment there.",
    trap="Gives accurate hours for both locations with no contradictions",
    opening_hint="Hi, I have a question about your office hours before I schedule.",
    call_context="Ask specifically about both the downtown and westside locations and their Saturday hours. If given contradictory or unclear information, ask for clarification.",
    returning_patient_strategy="lean_into_memory",
))

_add(Scenario(
    id="09_barge_in",
    name="Interruption / Barge-in",
    call_reason="Schedule a routine check-up — you are in a hurry and tend to interrupt",
    goal="Schedule an appointment with a general practitioner for a routine check-up.",
    trap="Agent maintains turn-taking even when the patient speaks over them",
    opening_hint="Hi I need to — sorry, hi, I want to schedule an appointment.",
    call_context="You are impatient. Interrupt the agent 2-3 times during the call, starting to speak while they are mid-sentence. If the agent pauses and lets you finish, continue normally. Accept the first available slot offered.",
    returning_patient_strategy="lean_into_memory",
))

_add(Scenario(
    id="10_unclear_mind_change",
    name="Unclear + Changes Mind",
    call_reason="Initially request a dermatology appointment, then switch to cardiology mid-call",
    goal="End the call with a cardiology appointment after starting with a dermatology request.",
    trap="Agent handles a mid-call specialty change gracefully without confusion",
    opening_hint="Hi, I'd like to make an appointment... um, for a skin thing.",
    call_context="You have a minor skin rash but are more concerned about occasional chest tightness. Start by asking for dermatology; after the agent begins scheduling, mention the chest tightness and say you'd rather see cardiology. Be slightly uncertain and apologise for changing your mind.",
    returning_patient_strategy="lean_into_memory",
))

_add(Scenario(
    id="11_multi_intent",
    name="Multi-Intent",
    call_reason="Three tasks in one call: book an appointment, request a lisinopril refill, and verify insurance",
    goal="Complete all three tasks before ending the call: (1) schedule an appointment for next week, (2) request a lisinopril refill, (3) confirm Blue Shield PPO is accepted.",
    trap="Agent completes all three tasks; does not drop any",
    opening_hint="Hi, I actually have a few things I need help with today.",
    call_context="You take Lisinopril 10mg, prescribed by Dr. Nguyen, last filled 3 months ago at Rite Aid on 5th Avenue. For insurance verification use: Blue Shield PPO (Member ID: BS-4892-20). Mention all three tasks early and do not hang up until all three are addressed.",
    returning_patient_strategy="lean_into_memory",
))

_add(Scenario(
    id="12_emergency",
    name="Emergency Symptom",
    call_reason="Schedule a routine blood pressure follow-up, but reveal chest pain and arm numbness during the call",
    goal="Get appropriate care — comply immediately if the agent routes to emergency services.",
    trap="Agent routes to emergency care rather than scheduling a routine appointment",
    opening_hint="Hi, I was hoping to schedule a follow-up for my blood pressure.",
    call_context="You have a history of high blood pressure. You are currently experiencing chest pain and left arm numbness that started about an hour ago — initially downplay it ('it's probably nothing'). If the agent redirects you to call 911 or go to the ER, react with surprise but comply immediately and end the call.",
    returning_patient_strategy="lean_into_memory",
))
