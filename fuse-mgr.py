import os
import sys
import configparser
import json
import requests


def not_authd_mgr(email):
    post_msg = "https://webexapis.com/v1/messages/"
    pl_title = "**You don't appear to be an authorized manager of this bot. Mamma told me not to talk to strangers.**"
    payload = json.dumps(
        {
            "toPersonEmail": email,
            "markdown": pl_title,
        }
    )
    try:
        post_msg_r = requests.request(
            "POST", post_msg, headers=headers, data=payload, timeout=2
        )
        post_msg_r.raise_for_status()
        print(f"Not Authorized Manager Message sent ({post_msg_r.status_code})")
    except requests.exceptions.Timeout:
        print("Timeout error. Try again.")
    except requests.exceptions.TooManyRedirects:
        print("Bad URL")
    except requests.exceptions.HTTPError as nc_err:
        raise SystemExit(nc_err) from nc_err
    except requests.exceptions.RequestException as nc_cat_exception:
        raise SystemExit(nc_cat_exception) from nc_cat_exception


def mgr_control():
    payload = json.dumps(
        {
            "toPersonEmail": person_email,
            "markdown": "Adaptive card response. Open message on a supported client to respond.",
            "attachments": mgr_card,
        }
    )
    r = requests.request("POST", post_msg_url, headers=headers, data=payload, timeout=2)
    return r


KEY = "CI"
if os.getenv(KEY):
    print("Running as GitHub Action.")
    webex_bearer = os.environ["webex_bearer"]
    person_email = os.environ["person_email"]
    auth_mgrs = os.environ["auth_mgrs"]
else:
    print("Running locally.")
    config = configparser.ConfigParser()
    config.read("./secrets/config.ini")
    webex_bearer = config["DEFAULT"]["webex_key"]
    person_email = config["DEFAULT"]["person_email"]
    auth_mgrs = config["DEFAULT"]["auth_mgrs"]

post_msg_url = "https://webexapis.com/v1/messages/"

headers = {
    "Authorization": webex_bearer,
    "Content-Type": "application/json",
}

mgr_card = {
    "contentType": "application/vnd.microsoft.card.adaptive",
    "content": {
        "type": "AdaptiveCard",
        "body": [
            {
                "type": "ColumnSet",
                "columns": [
                    {
                        "type": "Column",
                        "items": [
                            {
                                "type": "Image",
                                "url": "https://user-images.githubusercontent.com/10964629/216710865-00ba284d-b9b1-4b8a-a8a0-9f3f07b7d962.jpg",
                                "height": "100px",
                                "width": "400px",
                            }
                        ],
                    }
                ],
            },
            {
                "type": "TextBlock",
                "text": "Fuse Bot Mission Control",
                "wrap": True,
                "horizontalAlignment": "Center",
                "fontType": "Monospace",
                "size": "Large",
                "color": "Default",
                "weight": "Bolder",
                "spacing": "Small",
            },
            {
                "type": "ColumnSet",
                "columns": [
                    {
                        "type": "Column",
                        "width": "stretch",
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": "What can I do for you?",
                                "wrap": True,
                                "horizontalAlignment": "Center",
                                "size": "Medium",
                            }
                        ],
                    },
                    {
                        "type": "Column",
                        "width": "stretch",
                        "items": [
                            {
                                "type": "Input.ChoiceSet",
                                "choices": [
                                    {
                                        "title": "Attendee Report",
                                        "value": "attend_report",
                                    },
                                    {
                                        "title": "Send Nudge",
                                        "value": "noncomit_reminders",
                                    },
                                    {
                                        "title": "Send Pre FUSE Reminders",
                                        "value": "pre_reminder",
                                    },
                                    {
                                        "title": "Send Survey Message",
                                        "value": "survey_msg",
                                    },
                                ],
                                "id": "Action_Choice",
                            }
                        ],
                    },
                ],
            },
            {
                "type": "ColumnSet",
                "columns": [
                    {"type": "Column", "width": "stretch"},
                    {"type": "Column", "width": "stretch"},
                    {
                        "type": "Column",
                        "width": "stretch",
                        "items": [
                            {
                                "type": "ActionSet",
                                "actions": [
                                    {
                                        "type": "Action.Submit",
                                        "title": "Submit",
                                        "id": "Action.Submit",
                                    }
                                ],
                                "horizontalAlignment": "Right",
                            }
                        ],
                    },
                ],
            },
        ],
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.2",
    },
}


if person_email in auth_mgrs:
    print("Authorized manager.")
else:
    print("Not an authorized manager.")
    not_authd_mgr(person_email)
    sys.exit()


mgr_ctl_response = mgr_control()

"""
noncommited = df2[
    (df2["Response"] == "None") & (df2["Attendance"] == "Required Attendee")
]
num_noncommited = len(noncommited)
print(f"\nNoncommited Attendees: {num_noncommited}")
noncommited_string = noncommited[["Full Name"]].to_string(index=False, header=False)

post_noncommited(noncommited_string, num_noncommited, person_email)

NONCOMMITED_LST = noncommited["Alias"].values.tolist()



"""
