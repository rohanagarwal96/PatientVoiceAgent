import argparse
import os
import sys

from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

_TO_NUMBER = "+18054398008"


def place_call(scenario_id: str = "01_simple_scheduling") -> str:
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_FROM_NUMBER")
    public_base_url = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

    missing = [
        name
        for name, val in [
            ("TWILIO_ACCOUNT_SID", account_sid),
            ("TWILIO_AUTH_TOKEN", auth_token),
            ("TWILIO_FROM_NUMBER", from_number),
            ("PUBLIC_BASE_URL", public_base_url),
        ]
        if not val
    ]
    if missing:
        print(f"[trigger] ERROR: missing env vars: {', '.join(missing)}", flush=True)
        sys.exit(1)

    client = Client(account_sid, auth_token)
    call = client.calls.create(
        to=_TO_NUMBER,
        from_=from_number,
        url=f"{public_base_url}/twiml?scenario={scenario_id}",
        record=True,
        recording_channels="dual",
    )
    print(f"[trigger] call placed — SID: {call.sid}", flush=True)
    return call.sid


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="01_simple_scheduling")
    args = parser.parse_args()
    place_call(args.scenario)
