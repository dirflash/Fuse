# Webex actions

import os
import json
import requests
import configparser

KEY = "CI"
environ = os.getenv(KEY, default="LOCAL")

if environ == "true":
    webex_key = os.environ["webex_key"]
else:
    config = configparser.ConfigParser()
    config.read("./secrets/config.ini")
    webex_key = config["DEFAULT"]["webex_key"]

url = "https://webexapis.com/v1/messages/"

headers = {
    "Authorization": webex_key,
    "Content-Type": "application/json",
}

card = {
    "contentType": "application/vnd.microsoft.card.adaptive",
    "content": {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.2",
        "body": [
            {
                "type": "ImageSet",
                "images": [
                    {
                        "type": "Image",
                        "id": "fuse_image",
                        "url": "https://user-images.githubusercontent.com/10964629/216710865-00ba284d-b9b1-4b8a-a8a0-9f3f07b7d962.jpg",
                        "height": "100px",
                        "width": "400px",
                    }
                ],
            },
            {
                "type": "RichTextBlock",
                "inlines": [
                    {
                        "type": "TextRun",
                        "text": "The next FUSE session is on February 17th. It doesn't look like you have accepted the invitation. Your acceptance is used to pair you with a fellow SE. But we know sometimes Outlook doesn't properly update your response. So, let us know if you plan on attending.",
                    }
                ],
                "id": "fyi",
            },
            {
                "type": "Input.ChoiceSet",
                "choices": [
                    {"title": "Yes", "value": "Yes"},
                    {"title": "No", "value": "No"},
                ],
                "id": "rsvp",
                "value": "Yes",
            },
            {
                "type": "ActionSet",
                "horizontalAlignment": "Left",
                "spacing": "None",
                "actions": [{"type": "Action.Submit", "title": "Submit"}],
                "id": "Submit",
            },
        ],
    },
}


def send_msg(x):
    payload = json.dumps(
        {
            "toPersonEmail": x,
            "markdown": "Adaptive card response. Open message on a supported client to respond.",
            "attachments": card,
        }
    )
    print(payload)
    r = requests.request("POST", url, headers=headers, data=payload, timeout=2)
    return r


def msg(alias):
    for x in alias:
        email = f"{x}@cisco.com"
        print(email)
        if email == "aarodavi@cisco.com":
            try:
                # response = requests.request("POST", url, headers=headers, data=payload, timeout=2)
                response = send_msg(email)
                response.raise_for_status()
                print(f"Message sent ({response.status_code})")
                # print(response.text)
            except requests.exceptions.Timeout:
                print("Timeout error. Try again.")
            except requests.exceptions.TooManyRedirects:
                print("Bad URL")
            except requests.exceptions.HTTPError as err:
                raise SystemExit(err) from err
            except requests.exceptions.RequestException as cat_exception:
                raise SystemExit(cat_exception) from cat_exception
        print(f"send_msg {alias}")
