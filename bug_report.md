# Bug Report

Confirmed findings from PatientVoiceAgent evaluation runs.
Each bug was reviewed and accepted through the human-in-the-loop evaluator (`src/evaluator.py`).

## Bug 1 — Failed to collect date of birth in a logical sequence · severity: medium
**Scenario:** 01_simple_scheduling  
**Call SID:** CA59ddaab7822ae64dbf22d76d2492f613  
**Timestamp:** 00:23  
**Confidence:** high  
**Severity justification:** This caused confusion and disrupted the flow of the interaction, which could lead to errors in patient identification or scheduling.  

**Evidence:** AGENT: Please provide your date of birth.

What happened: The agent asked for the date of birth after the patient had already provided it ('March 12, 1991'). Why it is a problem: This creates unnecessary repetition and confusion, as the patient had already answered the question. What should have happened: The agent should have acknowledged the provided date of birth and moved on to the next step.

## Bug 2 — Incorrectly stated that a routine checkup appointment was already booked · severity: high
**Scenario:** 01_simple_scheduling  
**Call SID:** CA59ddaab7822ae64dbf22d76d2492f613  
**Timestamp:** 00:59  
**Confidence:** high  *(possible state artifact)*  
**Severity justification:** This miscommunication could prevent the patient from scheduling a needed appointment, directly impacting patient care.  

**Evidence:** AGENT: It looks like you already have a routine checkup appointment booked.

What happened: The agent incorrectly informed the patient that they already had a routine checkup appointment booked. Why it is a problem: This could lead to the patient not receiving the care they need if they believe an appointment is already scheduled. What should have happened: The agent should have verified the patient's records more carefully or clarified the situation before making this statement.

## Bug 3 — Failed to resolve scheduling request before transferring the call · severity: medium
**Scenario:** 01_simple_scheduling  
**Call SID:** CA59ddaab7822ae64dbf22d76d2492f613  
**Timestamp:** 01:31  
**Confidence:** high  
**Severity justification:** The agent prematurely transferred the call without attempting to resolve the patient's request, leading to a poor user experience.  

**Evidence:** AGENT: Let me connect you with a team member who can review your records and help sort this out.

What happened: The agent transferred the call to another team member without making a sufficient effort to resolve the patient's request to schedule a new appointment. Why it is a problem: This creates unnecessary delays and frustration for the patient. What should have happened: The agent should have attempted to clarify the situation and schedule the appointment before resorting to a transfer.

## Bug 4 — Agent loops excessively on spelling and confirmation requests · severity: medium
**Scenario:** 02_after_hours  
**Call SID:** CA8e768b7d80a5c902480938d7a0801e6c  
**Timestamp:** 00:45  
**Confidence:** high  
**Severity justification:** This behavior creates unnecessary frustration for the caller and wastes time, but does not directly impact safety or critical scheduling outcomes.  

**Evidence:** AGENT: If so, could you please spell your first and last name for me? PATIENT: My first name is spelled S-A-M and my last name is P-A-T-E-L.

What happened: The agent repeatedly asked the patient to spell their name and confirm their date of birth, even after the patient provided this information multiple times. This occurred at least 6 times throughout the call. Why it is a problem: Excessive repetition wastes time and creates a poor user experience. What should have happened: The agent should have accepted the information after the first or second confirmation and moved on to the next step.

## Bug 5 — Agent fails to handle incomplete phone number gracefully · severity: medium
**Scenario:** 02_after_hours  
**Call SID:** CA8e768b7d80a5c902480938d7a0801e6c  
**Timestamp:** 01:37  
**Confidence:** high  
**Severity justification:** This behavior prevents the agent from progressing in the scheduling process and creates unnecessary friction for the caller.  

**Evidence:** AGENT: Go ahead and tell me the full phone number you have on file. PATIENT: I'm afraid I don't have access to the full number on file.

What happened: The agent repeatedly asked for the full phone number on file, even after the patient explained they could not provide it. This loop persisted for over 30 seconds. Why it is a problem: The agent should have acknowledged the limitation and moved forward with alternative verification methods. What should have happened: The agent should have accepted the partial information or offered another way to verify the patient's identity.

## Bug 6 — Agent fails to provide clear resolution or next steps · severity: medium
**Scenario:** 02_after_hours  
**Call SID:** CA8e768b7d80a5c902480938d7a0801e6c  
**Timestamp:** 03:14  
**Confidence:** high  
**Severity justification:** While the agent eventually routes the call to the support team, the lack of clarity and repeated loops create confusion and delay resolution.  

**Evidence:** AGENT: I can't proceed further right now, but I can make sure our clinic support team follows up with you.

What happened: The agent failed to provide a clear explanation of why they could not proceed or what the next steps would be. The patient was left uncertain about the resolution until the agent finally routed the call. Why it is a problem: Lack of clarity can frustrate callers and reduce trust in the service. What should have happened: The agent should have clearly explained the limitation and immediately offered to connect the patient to the support team without unnecessary repetition.
