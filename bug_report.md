# Bug Report

Confirmed findings from PatientVoiceAgent evaluation runs.
Each bug was reviewed and accepted through the human-in-the-loop evaluator (`src/evaluator.py`).

## Bug 1 — Incorrectly stated that the patient already had an appointment · severity: high
**Scenario:** 01_simple_scheduling  
**Call SID:** CA358dd230a45b77c707a1784384773a2b  
**Timestamp:** 01:05  
**Confidence:** high  *(possible state artifact)*  
**Severity justification:** This caused confusion for the patient and led to an unnecessary transfer, disrupting the scheduling process.  

**Evidence:** AGENT: It looks like you already have a general checkup appointment booked. AGENT: I can help you reschedule or cancel your existing appointment or transfer you to a team member for further assistance.

What happened: At 01:05 the agent informed the patient that a general checkup was already on file and offered only to reschedule, cancel, or transfer — not to book a new one. When the patient said they didn't recall booking it and wanted to schedule fresh, the agent doubled down rather than offering to proceed. Why it is a problem: The agent had no path for "patient disputes prior booking and wants a new one," leaving the call unresolved. What should have happened: The agent should have acknowledged the prior booking, confirmed whether it was still wanted, and offered to keep it or book an additional appointment as the patient requested. Note: this is flagged as a possible state artifact — the prior booking was created during an earlier test call from the same number and is real data in the agent's system.

## Bug 2 — Failed to proceed after patient disputed existing appointment · severity: high
**Scenario:** 01_simple_scheduling  
**Call SID:** CA358dd230a45b77c707a1784384773a2b  
**Timestamp:** 01:15  
**Confidence:** high  *(possible state artifact)*  
**Severity justification:** The primary goal of the call — scheduling an appointment — was never completed despite the patient explicitly restating the request.  

**Evidence:** PATIENT: I don't recall booking an appointment yet. I'd prefer to schedule a new one. AGENT: Since the system shows an existing appointment for a general checkup, would you like to reschedule it, cancel it, or speak with a team member to clarify?

What happened: After the patient explicitly said they wanted to schedule a new appointment, the agent repeated the same three-option loop (reschedule / cancel / transfer) and never offered to book. Why it is a problem: The call ended in a transfer without the patient's goal being addressed. What should have happened: When the patient disputed the record and asked for a new booking, the agent should have offered to place a new appointment or escalate with that intent stated clearly.

## Bug 3 — Incomplete transfer with garbled confirmation · severity: medium
**Scenario:** 01_simple_scheduling  
**Call SID:** CA358dd230a45b77c707a1784384773a2b  
**Timestamp:** 02:05  
**Confidence:** high  
**Severity justification:** The agent transferred the patient without confirming it was connecting them or explaining why.  

**Evidence:** AGENT: An act you to a representative. Please wait. Hello. You've reached the pretty good AI test line. Goodbye.

What happened: The agent initiated a transfer using unclear language and the call ended on the test-line termination message with no handoff summary or confirmation. Why it is a problem: The patient received no acknowledgment of their original request before being disconnected, leaving the call fully unresolved. What should have happened: The agent should have stated clearly why it was transferring, what the representative would help with, and confirmed the patient was on hold before connecting.

## Bug 4 — Infinite loop asking patient to spell name after it was already provided · severity: high
**Scenario:** 02_after_hours  
**Call SID:** CA47f68896b84217e9b51c0a5884cd3a7a  
**Timestamp:** 01:11  
**Confidence:** high  
**Severity justification:** The agent made at least 10 redundant spelling requests over roughly 3 minutes despite the patient providing the full phonetic spelling each time, making the call unusable.  

**Evidence:** AGENT: Please spell your first and last name for me. PATIENT: Sure, it's S as in Sierra, A as in Alpha, M as in Mike. AGENT: Please spell your first and last name letter by letter. [Pattern repeated from 01:11 to 04:10.]

What happened: From 01:11 to approximately 04:10, the agent looped on a single spelling-verification step, issuing variants of "please spell your first and last name" more than 10 times. The patient provided the full phonetic spelling (SAM PATEL, letter by letter) multiple times. The agent never acknowledged a completed spelling or advanced past this step. Why it is a problem: The entire call was consumed by this loop; no scheduling work was done. This reflects a broken state machine in the agent's identity-verification flow. What should have happened: After the patient spelled their name once completely (first + last), the agent should have acknowledged the spelling and moved to the next verification step or to scheduling.

## Bug 5 — Call ended without scheduling or providing next steps after identity verification failed · severity: medium
**Scenario:** 02_after_hours  
**Call SID:** CA47f68896b84217e9b51c0a5884cd3a7a  
**Timestamp:** 05:10  
**Confidence:** high  
**Severity justification:** The patient received no resolution and was left uncertain about what to do next.  

**Evidence:** AGENT: I'm unable to verify your information right now, so I'll connect you to our patient support team for health. Please stand on the line, connecting you to a representative.

What happened: After the spelling loop exhausted itself, the agent stated it could not verify the patient's identity and transferred to a representative without explaining what the patient should expect or do next. The call ended on the test-line termination message. Why it is a problem: The patient (who had spent over 3 minutes spelling their name) received no appointment, no explanation, and no concrete callback instruction. What should have happened: When identity verification fails, the agent should state clearly what the transfer is for, give the patient an alternative path (call back, online portal, etc.), and confirm that their original request (scheduling an appointment) will be handled.
