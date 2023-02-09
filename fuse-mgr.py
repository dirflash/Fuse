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


post_msg = "https://webexapis.com/v1/messages/"

headers = {
    "Authorization": webex_bearer,
    "Content-Type": "application/json",
}

message = "Attachment ID: " + attachment + " from " + person_id

payload = json.dumps(
    {
        "toPersonEmail": "aarodavi@cisco.com",
        "markdown": message,
    }
)
print(payload)
post_msg_r = requests.request(
    "POST", post_msg, headers=headers, data=payload, timeout=2
)
post_msg_r.raise_for_status()
print(f"Message sent ({post_msg_r.status_code})")


get_attach_url = "https://webexapis.com/v1/contents/" + attachment

get_attach_response = requests.request(
    "GET", get_attach_url, headers=headers, timeout=2
)
get_attach_response.raise_for_status()
print(f"Message sent ({get_attach_response.status_code})")

print(get_attach_response.text)
