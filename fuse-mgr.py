import os
import requests
import json

print("Hello World!")

webex_bearer = os.environ["webex_bearer"]
attachment = os.environ["attachment"]
room_id = os.environ["room_id"]
room_type = os.environ["room_type"]
person_id = os.environ["person_id"]
person_email = os.environ["person_email"]


url = "https://webexapis.com/v1/messages/"

headers = {
    "Authorization": webex_bearer,
    "Content-Type": "application/json",
}

payload = json.dumps(
    {
        "toPersonEmail": "aarodavi@cisco.com",
        "markdown": "Test message.",
    }
)
print(payload)
r = requests.request("POST", url, headers=headers, data=payload, timeout=2)
r.raise_for_status()
print(f"Message sent ({r.status_code})")
