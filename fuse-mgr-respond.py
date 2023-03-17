import os
import sys
import json
import re
import configparser
import requests
import pandas as pd
import certifi
from pymongo import MongoClient, DESCENDING, errors
from datetime import datetime

# import validators

KEY = "CI"
if os.getenv(KEY):
    print("Running as GitHub Action.")
    webex_bearer = os.environ["webex_bearer"]
    person_id = os.environ["person_id"]
    person_name = os.environ["person_name"]
    first_name = os.environ["first_name"]
    person_guid = os.environ["person_guid"]
    action = os.environ["action"]
    survey_url = os.environ["survey_url"]
    session_date = os.environ["session_date"]
    auth_mgrs = os.environ["auth_mgrs"]
    mongo_addr = os.environ["MONGO_ADDR"]
    mongo_db = os.environ["MONGO_DB"]
    bridge_collect = os.environ["BRIDGE_COLLECT"]
    response_collect = os.environ["RESPONSE_COLLECT"]
    date_collect = os.environ["DATE_COLLECT"]
    survey_collect = os.environ["SURVEY_COLLECT"]
    rsvp_collect = os.environ["RSVP_COLLECT"]
    status_collect = os.environ["STATUS_COLLECT"]
    mongo_un = os.environ["MONGO_UN"]
    mongo_pw = os.environ["MONGO_PW"]
    fuse_date = os.environ["FUSE_DATE"]
    github_pat = os.environ["GITHUB_PAT"]
    rsvp_response = os.environ["rsvp_response"]
    fuse_rsvp_date = os.environ["fuse_rsvp_date"]
    msg_txt = os.environ["msg_txt"]
else:
    print("Running locally.")
    config = configparser.ConfigParser()
    config.read("./secrets/config.ini")
    webex_bearer = config["DEFAULT"]["webex_key"]
    person_id = "jamarsh@cisco.com"  # config["DEFAULT"]["person_id"]
    first_name = "Jim"
    person_name = "Jim Marsh"
    person_guid = config["DEFAULT"]["person_guid"]
    auth_mgrs = config["DEFAULT"]["auth_mgrs"]
    action = "survey_msg"
    survey_url = "NA"
    session_date = "NA"
    mongo_addr = config["MONGO"]["MONGO_ADDR"]
    mongo_db = config["MONGO"]["MONGO_DB"]
    bridge_collect = config["MONGO"]["BRIDGE_COLLECT"]
    date_collect = config["MONGO"]["DATE_COLLECT"]
    response_collect = config["MONGO"]["RESPONSE_COLLECT"]
    survey_collect = config["MONGO"]["SURVEY_COLLECT"]
    rsvp_collect = config["MONGO"]["RSVP_COLLECT"]
    status_collect = config["MONGO"]["STATUS_COLLECT"]
    mongo_un = config["MONGO"]["MONGO_UN"]
    mongo_pw = config["MONGO"]["MONGO_PW"]
    fuse_date = "NA"
    github_pat = config["DEFAULT"]["FUSE_PAT"]
    rsvp_response = ""
    fuse_rsvp_date = ""
    msg_txt = ""


MAX_MONGODB_DELAY = 500

Mongo_Client = MongoClient(
    f"mongodb+srv://{mongo_un}:{mongo_pw}@{mongo_addr}/{mongo_db}?retryWrites=true&w=majority",
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=MAX_MONGODB_DELAY,
)

db = Mongo_Client[mongo_db]
bridge_collection = db[bridge_collect]
response_collection = db[response_collect]
date_collection = db[date_collect]
survey_collection = db[survey_collect]
rsvp_collection = db[rsvp_collect]
status_collection = db[status_collect]

post_msg_url = "https://webexapis.com/v1/messages/"

headers = {
    "Authorization": webex_bearer,
    "Content-Type": "application/json",
}

RAW_FILE_NAME = ""
NONCOMMITED_LST = []


def manager_card(set_date):
    mgr_card = {
        "contentType": "application/vnd.microsoft.card.adaptive",
        "content": {
            "type": "AdaptiveCard",
            "body": [
                {
                    "type": "ImageSet",
                    "images": [
                        {
                            "type": "Image",
                            "size": "Medium",
                            "url": "https://user-images.githubusercontent.com/10964629/225653491-e3c2920c-419d-45ab-ba9f-b0add6138e33.png",
                            "height": "100px",
                            "width": "400px",
                        }
                    ],
                },
                {
                    "type": "Container",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "Fuse Bot Mission Control",
                            "wrap": True,
                            "horizontalAlignment": "Center",
                            "fontType": "Monospace",
                            "size": "Large",
                            "weight": "Bolder",
                        },
                        {
                            "type": "TextBlock",
                            "text": "What can I do for you?",
                            "wrap": True,
                            "horizontalAlignment": "Left",
                            "fontType": "Monospace",
                            "size": "Medium",
                            "weight": "Bolder",
                        },
                        {
                            "type": "Input.ChoiceSet",
                            "choices": [
                                {"title": "Set Date", "value": "fuse_date"},
                                {"title": "Attendee Report", "value": "attend_report"},
                                {
                                    "title": "RSVP Requests",
                                    "value": "noncomit_reminders",
                                },
                                {
                                    "title": "Pre-FUSE Reminders",
                                    "value": "pre_reminder",
                                },
                                {"title": "Survey Message", "value": "survey_msg"},
                            ],
                            "id": "Action_Choice",
                        },
                    ],
                },
                {
                    "type": "Container",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "First step: Set or verify the FUSE date. Then upload a CSV of calendar invite tracking data.",
                            "wrap": True,
                            "fontType": "Monospace",
                            "weight": "Bolder",
                        }
                    ],
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
                                    "text": set_date,
                                    "wrap": True,
                                    "fontType": "Monospace",
                                    "size": "Small",
                                    "weight": "Bolder",
                                }
                            ],
                        },
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
                                            "id": "submit",
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
    return mgr_card


def set_date_card(date_msg):
    setdate_card = {
        "contentType": "application/vnd.microsoft.card.adaptive",
        "content": {
            "type": "AdaptiveCard",
            "body": [
                {
                    "type": "ImageSet",
                    "images": [
                        {
                            "type": "Image",
                            "size": "Medium",
                            "id": "fuse_image",
                            "url": "https://user-images.githubusercontent.com/10964629/225653491-e3c2920c-419d-45ab-ba9f-b0add6138e33.png",
                            "height": "100px",
                            "width": "400px",
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
                    "weight": "Bolder",
                    "color": "Default",
                },
                {
                    "type": "TextBlock",
                    "text": date_msg,
                    "wrap": True,
                    "horizontalAlignment": "Center",
                    "size": "Medium",
                    "weight": "Bolder",
                    "color": "Warning",
                    "fontType": "Monospace",
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
                                    "text": "When is the next Fuse?",
                                    "wrap": True,
                                    "horizontalAlignment": "Center",
                                    "size": "Medium",
                                }
                            ],
                        },
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [{"type": "Input.Date", "id": "fuse_date"}],
                        },
                    ],
                },
                {
                    "type": "ColumnSet",
                    "columns": [
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
                                            "id": "fuse_date_submit",
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
    return setdate_card


def mgr_control(card):
    payload = json.dumps(
        {
            "toPersonEmail": person_id,
            "markdown": "Adaptive card response. Open message on a supported client to respond.",
            "attachments": card,
        }
    )
    r = requests.request("POST", post_msg_url, headers=headers, data=payload, timeout=3)
    return r


def survey_submit_card():
    survey_card = {
        "contentType": "application/vnd.microsoft.card.adaptive",
        "content": {
            "type": "AdaptiveCard",
            "body": [
                {
                    "type": "ImageSet",
                    "images": [
                        {
                            "type": "Image",
                            "url": "https://user-images.githubusercontent.com/10964629/225653491-e3c2920c-419d-45ab-ba9f-b0add6138e33.png",
                            "height": "100px",
                            "width": "400px",
                            "size": "Medium",
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
                    "weight": "Bolder",
                },
                {
                    "type": "Container",
                    "items": [
                        {
                            "type": "Container",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "wrap": True,
                                    "fontType": "Monospace",
                                    "text": "Post Session Survey Request",
                                    "horizontalAlignment": "Center",
                                    "size": "Medium",
                                    "color": "Default",
                                    "weight": "Bolder",
                                }
                            ],
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
                                            "text": "Date of last Fuse session:",
                                            "wrap": True,
                                            "fontType": "Monospace",
                                            "size": "Default",
                                            "horizontalAlignment": "Right",
                                        }
                                    ],
                                },
                                {
                                    "type": "Column",
                                    "width": "stretch",
                                    "items": [
                                        {"type": "Input.Date", "id": "session_date"}
                                    ],
                                },
                            ],
                        },
                    ],
                },
                {
                    "type": "Container",
                    "items": [
                        {
                            "type": "ColumnSet",
                            "columns": [
                                {
                                    "type": "Column",
                                    "width": "stretch",
                                    "items": [
                                        {
                                            "type": "TextBlock",
                                            "wrap": True,
                                            "fontType": "Monospace",
                                            "size": "Default",
                                            "text": "Survey Link:",
                                            "horizontalAlignment": "Right",
                                        }
                                    ],
                                },
                                {
                                    "type": "Column",
                                    "width": "stretch",
                                    "items": [
                                        {
                                            "type": "Input.Text",
                                            "placeholder": "Survey URL",
                                            "style": "Url",
                                            "id": "survey_url",
                                        }
                                    ],
                                },
                            ],
                        }
                    ],
                },
                {
                    "type": "Container",
                    "items": [
                        {
                            "type": "ColumnSet",
                            "columns": [
                                {"type": "Column", "width": "stretch"},
                                {
                                    "type": "Column",
                                    "width": "stretch",
                                    "items": [
                                        {
                                            "type": "Input.Text",
                                            "placeholder": "survey_submit",
                                            "isVisible": False,
                                            "id": "postevent_survey",
                                            "value": "survey_submit",
                                        }
                                    ],
                                },
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
                                                    "id": "survey_submit",
                                                }
                                            ],
                                        }
                                    ],
                                },
                            ],
                        }
                    ],
                },
            ],
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.2",
        },
    }
    return survey_card


def post_survey_card(fir_name, sess_date, surv_url):
    day_fix = datetime.strptime(sess_date, "%Y-%m-%d").strftime("%m-%d-%Y")
    main_msg = f"Hello, {fir_name}!\n\nThank you for participating in the Fuse session on {day_fix}. Your feedback is important. It would be great if you could complete this post event survey."
    post_surv_card = {
        "contentType": "application/vnd.microsoft.card.adaptive",
        "content": {
            "type": "AdaptiveCard",
            "body": [
                {
                    "type": "ImageSet",
                    "images": [
                        {
                            "type": "Image",
                            "url": "https://user-images.githubusercontent.com/10964629/225653491-e3c2920c-419d-45ab-ba9f-b0add6138e33.png",
                            "height": "100px",
                            "width": "400px",
                            "size": "Medium",
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
                    "weight": "Bolder",
                },
                {
                    "type": "Container",
                    "items": [
                        {
                            "type": "Container",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "wrap": True,
                                    "fontType": "Monospace",
                                    "text": "Post Session Survey Request",
                                    "horizontalAlignment": "Center",
                                    "size": "Medium",
                                    "color": "Default",
                                    "weight": "Bolder",
                                }
                            ],
                        }
                    ],
                },
                {
                    "type": "Container",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": main_msg,
                            "wrap": True,
                            "fontType": "Monospace",
                            "size": "Small",
                            "weight": "Bolder",
                        },
                        {
                            "type": "Container",
                            "items": [
                                {
                                    "type": "ColumnSet",
                                    "columns": [
                                        {"type": "Column", "width": "stretch"},
                                        {
                                            "type": "Column",
                                            "width": "stretch",
                                            "items": [
                                                {
                                                    "type": "ActionSet",
                                                    "actions": [
                                                        {
                                                            "type": "Action.OpenUrl",
                                                            "id": "survey_url",
                                                            "title": "Launch Survey",
                                                            "url": surv_url,
                                                        }
                                                    ],
                                                }
                                            ],
                                        },
                                        {"type": "Column", "width": "stretch"},
                                    ],
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
    return post_surv_card


def send_survey(s_date, s_url):
    meta_msg = f"{s_date}, {s_url}"
    msg = "Please confirm the message above for accuracy. If everything looks good and you would like to send it to all the participants, click below."
    send_survey_card = {
        "contentType": "application/vnd.microsoft.card.adaptive",
        "content": {
            "type": "AdaptiveCard",
            "body": [
                {
                    "type": "ImageSet",
                    "images": [
                        {
                            "type": "Image",
                            "url": "https://user-images.githubusercontent.com/10964629/225653491-e3c2920c-419d-45ab-ba9f-b0add6138e33.png",
                            "height": "100px",
                            "width": "400px",
                            "size": "Medium",
                        }
                    ],
                },
                {
                    "type": "Container",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "Fuse Bot Mission Control",
                            "wrap": True,
                            "horizontalAlignment": "Center",
                            "fontType": "Monospace",
                            "weight": "Bolder",
                            "size": "Large",
                        },
                        {
                            "type": "TextBlock",
                            "wrap": True,
                            "text": "Survey Request Proof Confirmation",
                            "horizontalAlignment": "Center",
                            "fontType": "Monospace",
                            "weight": "Bolder",
                            "size": "Medium",
                        },
                    ],
                },
                {
                    "type": "TextBlock",
                    "text": msg,
                    "wrap": True,
                    "horizontalAlignment": "Left",
                    "fontType": "Monospace",
                    "weight": "Bolder",
                    "size": "Small",
                },
                {
                    "type": "ColumnSet",
                    "columns": [
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {
                                    "type": "Input.Text",
                                    "id": "post_survey_send",
                                    "value": "post_survey_send",
                                    "isVisible": False,
                                }
                            ],
                        },
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {
                                    "type": "Input.Text",
                                    "id": "post_survey_data",
                                    "value": meta_msg,
                                    "isVisible": False,
                                }
                            ],
                        },
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {
                                    "type": "ActionSet",
                                    "actions": [
                                        {
                                            "type": "Action.Submit",
                                            "title": "Yes",
                                            "id": "send_post_survey",
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
    return send_survey_card


def pre_event_card(pre_name):
    pre_msg = f"Hello, {pre_name}! We look forward to another great FUSE session on Friday. THANK YOU for participating and contributing to the strengthening of the best group of SAs at Cisco."
    send_preevent_card = {
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
                            "size": "Medium",
                            "url": "https://user-images.githubusercontent.com/10964629/225653491-e3c2920c-419d-45ab-ba9f-b0add6138e33.png",
                            "height": "100px",
                            "width": "400px",
                        }
                    ],
                },
                {
                    "type": "Container",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "Fuse Bot Mission Control",
                            "wrap": True,
                            "horizontalAlignment": "Center",
                            "fontType": "Monospace",
                            "size": "Large",
                            "weight": "Bolder",
                        },
                        {
                            "type": "TextBlock",
                            "text": "Fuse Session Reminder",
                            "wrap": True,
                            "spacing": "Medium",
                            "horizontalAlignment": "Center",
                            "fontType": "Monospace",
                            "size": "Medium",
                            "weight": "Bolder",
                        },
                        {
                            "type": "TextBlock",
                            "text": pre_msg,
                            "wrap": True,
                            "fontType": "Monospace",
                            "weight": "Bolder",
                        },
                    ],
                },
            ],
        },
    }
    return send_preevent_card


def fix_lst(part_list):
    parts = []
    for nme in part_list:
        name_person = nme["name"]
        parts.append(name_person)
    parts_substr = str(parts)
    parts_substr = (
        parts_substr.replace("[", "")
        .replace("]", "")
        .replace("'", "")
        .replace(", ", "\n")
    )
    return parts_substr


def attend_report_card(m_lst, n_lst, y_lst, f_date, no_none, no_yes, no_no):
    maybes_substr = fix_lst(m_lst)
    noes_substr = fix_lst(n_lst)
    yes_substr = fix_lst(y_lst)
    day_f = datetime.strptime(f_date, "%Y-%m-%d").strftime("%m-%d-%Y")
    report_subhead = f"Attendee Report from CSV for {day_f}"
    attendance_report = f"Number of noncommitted attendees: {no_none}\nNumber of confirmed attendees: {no_yes}\nNumber of declined attendees: {no_no}"
    send_attend_report_card = {
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
                            "url": "https://user-images.githubusercontent.com/10964629/225653491-e3c2920c-419d-45ab-ba9f-b0add6138e33.png",
                            "height": "100px",
                            "width": "400px",
                            "size": "Medium",
                        }
                    ],
                },
                {
                    "type": "Container",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "Fuse Bot Mission Control",
                            "wrap": True,
                            "horizontalAlignment": "Center",
                            "fontType": "Monospace",
                            "size": "Large",
                            "weight": "Bolder",
                        },
                        {
                            "type": "TextBlock",
                            "text": "report_subhead",
                            "wrap": True,
                            "horizontalAlignment": "Center",
                            "fontType": "Monospace",
                            "size": "Medium",
                            "weight": "Bolder",
                        },
                        {
                            "type": "TextBlock",
                            "text": "attendance_report",
                            "wrap": True,
                            "horizontalAlignment": "Left",
                            "fontType": "Monospace",
                            "size": "Small",
                            "weight": "Bolder",
                        },
                    ],
                },
            ],
            "actions": [
                {
                    "type": "Action.ShowCard",
                    "title": "Accepted",
                    "card": {
                        "type": "AdaptiveCard",
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "version": "1.2",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": "Joe 1\n Joe 2\n Joe 3\n Joe 4\n Joe 5",
                                "size": "Small",
                                "wrap": False,
                            }
                        ],
                    },
                    "id": "Accepted.ShowCard",
                },
                {
                    "type": "Action.ShowCard",
                    "title": "Declined",
                    "card": {
                        "type": "AdaptiveCard",
                        "version": "1.2",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": "Joe 1\nJoe 2\nJoe 3\nJoe 4\nJoe 5",
                                "size": "Small",
                                "wrap": False,
                            }
                        ],
                    },
                    "id": "Declined.ShowCard",
                },
                {
                    "type": "Action.ShowCard",
                    "title": "Noncommitted",
                    "card": {
                        "type": "AdaptiveCard",
                        "version": "1.2",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": "Joe 1\nJoe 2\nJoe 3\nJoe 4\nJoe 5",
                                "size": "Small",
                                "wrap": False,
                            }
                        ],
                    },
                    "id": "Noncom.ShowCard",
                },
            ],
        },
    }
    return send_attend_report_card


def attend_report_msg(ar_card, p_id):
    post_msg = "https://webexapis.com/v1/messages/"
    payload = json.dumps(
        {
            "toPersonEmail": p_id,
            "markdown": "Adaptive card response. Open message on a supported client to respond.",
            "attachments": ar_card,
        }
    )
    try:
        post_msg_r = requests.request(
            "POST", post_msg, headers=headers, data=payload, timeout=3
        )
        post_msg_r.raise_for_status()
        anon_email = re.sub(r"\w{3}(?=@)", "xxx", p_id)
        print(f"Confirmation Message sent ({post_msg_r.status_code}) to {anon_email}")
    except requests.exceptions.Timeout:
        print("Timeout error. Try again.")
    except requests.exceptions.TooManyRedirects:
        print("Bad URL")
    except requests.exceptions.HTTPError as nc_err:
        raise SystemExit(nc_err) from nc_err
    except requests.exceptions.RequestException as nc_cat_exception:
        raise SystemExit(nc_cat_exception) from nc_cat_exception


def self_resp_str_fix(part):
    parts_substr = str(part)
    parts_substr = (
        parts_substr.replace("[", "")
        .replace("]", "")
        .replace("'", "")
        .replace(", ", "\n")
    )
    return parts_substr


def self_resp_report_card(n_lst, y_lst, f_date):
    if len(n_lst) > 0:
        noes_substr = self_resp_str_fix(n_lst)
    else:
        noes_substr = ""
    if len(y_lst) > 0:
        yes_substr = self_resp_str_fix(y_lst)
    else:
        yes_substr = ""
    no_cnt = str(len(n_lst))
    yes_cnt = str(len(y_lst))
    day_f = datetime.strptime(f_date, "%Y-%m-%d").strftime("%m-%d-%Y")
    report_subhead = f"Bot Attendee Report\nResponses for {day_f}"
    attendance_report = f"Number of confirmed attendees: {yes_cnt}\nNumber of declined attendees: {no_cnt}"
    send_resp_card = {
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
                            "size": "Medium",
                            "url": "https://user-images.githubusercontent.com/10964629/225653491-e3c2920c-419d-45ab-ba9f-b0add6138e33.png",
                            "height": "100px",
                            "width": "400px",
                        }
                    ],
                },
                {
                    "type": "TextBlock",
                    "text": "Fuse Bot Mission Control",
                    "wrap": True,
                    "fontType": "Monospace",
                    "size": "Large",
                    "weight": "Bolder",
                    "horizontalAlignment": "Center",
                },
                {
                    "type": "TextBlock",
                    "text": report_subhead,
                    "wrap": True,
                    "horizontalAlignment": "Center",
                    "fontType": "Monospace",
                    "size": "Medium",
                    "weight": "Bolder",
                },
                {
                    "type": "TextBlock",
                    "text": attendance_report,
                    "wrap": True,
                    "horizontalAlignment": "Left",
                    "size": "Small",
                    "fontType": "Monospace",
                    "weight": "Bolder",
                },
                {
                    "type": "ColumnSet",
                    "columns": [
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {
                                    "type": "ActionSet",
                                    "actions": [
                                        {
                                            "type": "Action.ShowCard",
                                            "title": "Accepted",
                                            "card": {
                                                "type": "AdaptiveCard",
                                                "body": [
                                                    {
                                                        "type": "TextBlock",
                                                        "text": yes_substr,
                                                        "size": "Small",
                                                        "wrap": False,
                                                    }
                                                ],
                                            },
                                        }
                                    ],
                                }
                            ],
                        },
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {
                                    "type": "ActionSet",
                                    "actions": [
                                        {
                                            "type": "Action.ShowCard",
                                            "title": "Declined",
                                            "card": {
                                                "type": "AdaptiveCard",
                                                "body": [
                                                    {
                                                        "type": "TextBlock",
                                                        "text": noes_substr,
                                                        "size": "Small",
                                                        "wrap": False,
                                                    }
                                                ],
                                            },
                                        }
                                    ],
                                }
                            ],
                        },
                        {
                            "type": "Column",
                            "width": "stretch",
                        },
                    ],
                },
            ],
        },
    }
    return send_resp_card


def pre_event_notification(prev_email, prevent_card):
    print("Proof confirmation.")
    post_msg = "https://webexapis.com/v1/messages/"
    payload = json.dumps(
        {
            "toPersonEmail": prev_email,
            "markdown": "Adaptive card response. Open message on a supported client to respond.",
            "attachments": prevent_card,
        }
    )
    try:
        post_msg_r = requests.request(
            "POST", post_msg, headers=headers, data=payload, timeout=3
        )
        post_msg_r.raise_for_status()
        anon_email = re.sub(r"\w{3}(?=@)", "xxx", prev_email)
        print(f"Confirmation Message sent ({post_msg_r.status_code}) to {anon_email}")
    except requests.exceptions.Timeout:
        print("Timeout error. Try again.")
    except requests.exceptions.TooManyRedirects:
        print("Bad URL")
    except requests.exceptions.HTTPError as nc_err:
        raise SystemExit(nc_err) from nc_err
    except requests.exceptions.RequestException as nc_cat_exception:
        raise SystemExit(nc_cat_exception) from nc_cat_exception


def post_survey_msg(p_s_c, pers_id):
    payload = json.dumps(
        {
            "toPersonEmail": pers_id,
            "markdown": "Adaptive card response. Open message on a supported client to respond.",
            "attachments": p_s_c,
        }
    )
    try:
        r = requests.request(
            "POST", post_msg_url, headers=headers, data=payload, timeout=3
        )
    except requests.exceptions.Timeout:
        print("Timeout error. Try again.")
    except requests.exceptions.TooManyRedirects:
        print("Bad URL")
    except requests.exceptions.HTTPError as err:
        raise SystemExit(err) from err
    except requests.exceptions.RequestException as cat_exception:
        raise SystemExit(cat_exception) from cat_exception
    return r


def send_confirmation(nc, nc_emails, no_nc, email):
    # Need to create confirmation card
    nnc = str(no_nc)
    post_msg = "https://webexapis.com/v1/messages/"

    for nce in nc_emails:
        pl_title = f"Hello, {nce}. You haven't confirmed."
        payload = json.dumps(
            {
                "toPersonEmail": email,
                "markdown": pl_title,
            }
        )
        try:
            post_msg_r = requests.request(
                "POST", post_msg, headers=headers, data=payload, timeout=3
            )
            post_msg_r.raise_for_status()
            print(f"Noncommited Message sent to {nce} - ({post_msg_r.status_code})")
        except requests.exceptions.Timeout:
            print(f"Timeout error. Try again. Line: {sys._getframe().f_lineno}")
        except requests.exceptions.TooManyRedirects:
            print("Bad URL")
        except requests.exceptions.HTTPError as nc_err:
            raise SystemExit(nc_err) from nc_err
        except requests.exceptions.RequestException as nc_cat_exception:
            raise SystemExit(nc_cat_exception) from nc_cat_exception


def noncomitted_reminders(no_res):
    rsvp_dict = {}
    rsvp_list = []
    print("Requested action: Send Non Committed Reminders")
    noncommited = no_res[
        (no_res["Response"] == "None") & (no_res["Attendance"] == "Required Attendee")
    ]
    num_noncommited = len(noncommited)
    print(f"\nNoncommited Attendees: {num_noncommited}")
    noncommited_alias = noncommited[["Alias"]]
    noncommited_names = noncommited[["Full Name"]]
    noncommited_names_list = noncommited_names["Full Name"].to_list()
    noncommited_alias_list = noncommited_alias["Alias"].to_list()
    for x, name in enumerate(noncommited_names_list):
        rsvp_dict["name"] = name
        rsvp_dict["email"] = noncommited_alias_list[x] + "@cisco.com"
        rsvp_list.append(rsvp_dict.copy())
    return rsvp_list


def rsvp_db_upload(nofy_emails_lst, f_day, resp="none"):
    rec_id = []
    rec_add = []
    ts = datetime.now()
    for x in nofy_emails_lst:
        x_name = x["name"]
        x_exist = rsvp_collection.find_one({"name": x_name})
        if bool(x_exist):
            # print(f"{x_name} exists")
            if x_exist["fuse_date"] != f_day:
                rsvp_collection.update_one(
                    {"name": x_name}, {"$set": {"fuse_date": f_day}}
                )
            if x_exist["response"] != resp:
                rsvp_collection.update_one(
                    {"name": x_name}, {"$set": {"response": resp}}
                )
            rec_id.append(x_name)
        else:
            record = rsvp_collection.insert_one(
                {
                    "ts": ts,
                    "fuse_date": f_day,
                    "name": x["name"],
                    "email": x["email"],
                    "response": resp,
                }
            )
            record_id = record.inserted_id
            rec_id.append(x_name)
            rec_add.append(record_id)
    if len(rec_add) == 0:
        print("Inserted no new Object IDs.")
    else:
        print(f"Inserted {len(rec_add)} Object IDs")
    return rec_id


def pre_reminder(f_date):
    send_dict = {}
    send_list = []
    print("Pre Event Reminders")
    r_exist = status_collection.find({"fuse_date": f_date, "status": "Accepted"})
    r_exist_cnt = status_collection.count_documents(
        {"fuse_date": f_date, "status": "Accepted"}
    )
    for r_e in r_exist:
        send_dict["name"] = r_e["name"]
        send_dict["email"] = r_e["email"]
        send_list.append(send_dict.copy())
    print(f"Created pre_reminder list for {len(send_list)} attendees.")
    return send_list


def survey_msg(s_card, email):
    print("Post Event Survey")
    post_msg = "https://webexapis.com/v1/messages/"
    payload = json.dumps(
        {
            "toPersonEmail": email,
            "markdown": "Adaptive card response. Open message on a supported client to respond.",
            "attachments": s_card,
        }
    )
    try:
        post_msg_r = requests.request(
            "POST", post_msg, headers=headers, data=payload, timeout=3
        )
        post_msg_r.raise_for_status()
        print(f"Post Event Message sent ({post_msg_r.status_code})")
    except requests.exceptions.Timeout:
        print("Post Event Timeout error. Try again.")
    except requests.exceptions.TooManyRedirects:
        print("Post Event Bad URL")
    except requests.exceptions.HTTPError as nc_err:
        raise SystemExit(nc_err) from nc_err
    except requests.exceptions.RequestException as nc_cat_exception:
        raise SystemExit(nc_cat_exception) from nc_cat_exception


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
            "POST", post_msg, headers=headers, data=payload, timeout=3
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


def header_check(dframe):
    print("Checking for corrupted header names.")
    idx0 = dframe.columns[0]
    if idx0 != "Name":
        print(f"Corruption detected in Index 0: {idx0}")
        dframe.rename(columns={idx0: "Name"}, inplace=True)
        print("Index 0 has been corrected.")
        print(f"Header names: {list(df.columns.values)}")
    else:
        print("Index 0 is correct.")


def alias_format(dframe):
    """Pull the full name and alias from the "name" column and put them in separate columns.

    Args:
        dframe (dataframe): Pandas dataframe

    Returns:
        dataframe: dataframe with new 'Full Name' and 'Alias' column
    """
    dframe[["Full Name", "Alias"]] = dframe["Name"].apply(
        lambda x: pd.Series(str(x).split("("))
    )
    dframe["Alias"] = dframe["Alias"].str.replace(r"\)", "", regex=True)
    dframe["Full Name"] = dframe["Full Name"].str.rstrip()
    dframe["Full Name"] = dframe["Full Name"].str.lstrip()
    # print(dframe.head())
    print(f"{len(dframe)} entries.")
    return dframe


def x_dups(dframe):
    duplicateRows = dframe[dframe.duplicated(["Name"])]
    print(f"Found {len(duplicateRows)} duplicate entries.")
    dframe = dframe.drop_duplicates(subset="Name", keep="first")
    dups = len(dframe[dframe.duplicated(["Name"])])
    if dups == 0:
        print("Duplicate rows removed.")
    else:
        print(f"Unable to remove {dups} duplicate rows.")
    return dframe


def responses(dframe):
    no_respond = dframe[dframe["Response"] == "None"]
    # print(f"Not responded: {len(no_respond)}")
    y_respond = dframe[dframe["Response"] == "Accepted"]
    d_respond = dframe[dframe["Response"] == "Declined"]
    return (no_respond, y_respond, d_respond)


def chat_record(per_id):
    r_recent_cnt = bridge_collection.count_documents({"person_email": per_id})
    if r_recent_cnt == 0:
        last_chat = bridge_collection.find().sort("_id", -1).limit(1)
        for x in last_chat:
            doc_id = {"_id": x["_id"]}
            doc_per_email = per_id
            doc_src_email = x["person_email"]
            doc_attach_url = x["attachment"]
            print(f"No bridge record for {per_id}")
            print(f"Found most recent request from {doc_src_email}...")
            print(f"with attachment URL: {doc_attach_url}")
    else:
        recent_chat = (
            bridge_collection.find({"person_email": per_id})
            .sort("ts", DESCENDING)
            .limit(1)
        )
        for _ in recent_chat:
            doc_id = {"_id": _["_id"]}
            doc_per_email = _["person_email"]
            doc_attach_url = _["attachment"]
            print(f"Found most recent request from {doc_per_email}...")
            print(f"with attachment URL: {doc_attach_url}")
    return (doc_id, doc_per_email, doc_attach_url)


def set_fuse_date(day, p_id, collect):
    day_fs = datetime.strptime(day, "%Y-%m-%d").strftime(
        "%m-%d-%Y"
    )  # formatted date as str
    # day_fd = datetime.strptime(day_fs, "%m-%d-%Y")  # date str as type(date) as Y-m-d & zero time
    record = collect.insert_one({"person_email": p_id, "date": day})
    record_id = record.inserted_id
    print(f"Inserted Object ID into date collection: {record_id}")
    return day_fs


def get_fuse_date(date_dbcollection):
    try:
        documents = date_dbcollection.find().sort("_id", -1).limit(1)
        for _ in documents:
            print(_)
            time_id = _["_id"]
            time_value = _["date"]
            print(f"Found most recent id {time_id}...")
            print(f"with value of : {time_value}")
    except:
        print("No date record found.")
        time_value = "NA"
    return time_value


def mgr_card(fss_date):
    day_ar = datetime.strptime(fss_date, "%Y-%m-%d").strftime("%m-%d-%Y")
    date_msg = f"Next Fuse date: {day_ar}"
    fdc = manager_card(date_msg)
    mgr_control(fdc)


def failed_msg(email):
    post_msg = "https://webexapis.com/v1/messages/"
    pl_title = (
        "**Something unusual happened. Please wait a few minutes and try again.**"
    )
    payload = json.dumps(
        {
            "toPersonEmail": email,
            "markdown": pl_title,
        }
    )
    try:
        post_msg_r = requests.request(
            "POST", post_msg, headers=headers, data=payload, timeout=3
        )
        post_msg_r.raise_for_status()
        print(f"Failed Message sent ({post_msg_r.status_code})")
    except requests.exceptions.Timeout:
        print("Timeout error. Try again.")
    except requests.exceptions.TooManyRedirects:
        print("Bad URL")
    except requests.exceptions.HTTPError as nc_err:
        raise SystemExit(nc_err) from nc_err
    except requests.exceptions.RequestException as nc_cat_exception:
        raise SystemExit(nc_cat_exception) from nc_cat_exception


def proof_confirmation(email, attach_card):
    print("Proof confirmation.")
    post_msg = "https://webexapis.com/v1/messages/"
    payload = json.dumps(
        {
            "toPersonEmail": email,
            "markdown": "Adaptive card response. Open message on a supported client to respond.",
            "attachments": attach_card,
        }
    )
    try:
        post_msg_r = requests.request(
            "POST", post_msg, headers=headers, data=payload, timeout=3
        )
        post_msg_r.raise_for_status()
        print(f"Confirmation Message sent ({post_msg_r.status_code})")
    except requests.exceptions.Timeout:
        print("Timeout error. Try again.")
    except requests.exceptions.TooManyRedirects:
        print("Bad URL")
    except requests.exceptions.HTTPError as nc_err:
        raise SystemExit(nc_err) from nc_err
    except requests.exceptions.RequestException as nc_cat_exception:
        raise SystemExit(nc_cat_exception) from nc_cat_exception


def surveys(noes, yesses):
    survey_email = []
    print("Create list of email address for survey request.")
    noncommited = noes[
        (noes["Response"] == "None") & (noes["Attendance"] == "Required Attendee")
    ]
    commited = yesses[
        (yesses["Response"] == "Accepted")
        & (yesses["Attendance"] == "Required Attendee")
    ]
    num_noncommited = len(noncommited)
    num_commited = len(commited)
    print(f"Noncommited Attendees: {num_noncommited}")
    print(f"Commited Attendees: {num_commited}")
    # The following 3 lines takes the "Full Name" column, converts it to a list, then to
    # a string to solve formatting issues in the "send_confirmation" function.
    noncommited_names = noncommited[["Full Name"]]
    noncommited_list = noncommited_names["Full Name"].to_list()
    # noncommited_list2str = "\n".join(str(e) for e in noncommited_list)
    noncommited_alias_lst = noncommited[
        "Alias"
    ].values.tolist()  # list of email addresses to send reminder.
    commited_names = commited[["Full Name"]]
    commited_list = commited_names["Full Name"].to_list()
    # commited_list2str = "\n".join(str(e) for e in commited_list)
    commited_alias_lst = commited[
        "Alias"
    ].values.tolist()  # list of email addresses to send reminder.
    for _ in noncommited_alias_lst:
        survey_email.append(_ + "@cisco.com")
    for _ in commited_alias_lst:
        survey_email.append(_ + "@cisco.com")
    return survey_email


def send_survey_gh(p_id, f_name, p_guid, act, sess_date, surv_url, mong_id):
    gh_headers = {
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "Authorization": github_pat,
    }
    gh_payload = json.dumps(
        {
            "event_type": "FUSE_SEND_SURVEYS",
            "client_payload": {
                "person_id": p_id,
                "first_name": f_name,
                "person_guid": p_guid,
                "action": act,
                "session_date": sess_date,
                "survey_url": surv_url,
                "mongo_id": mong_id,
            },
        }
    )

    gh_webhook_url = "https://api.github.com/repos/dirflash/fuse/dispatches"
    try:
        gh_webhook_response = requests.request(
            "POST", gh_webhook_url, headers=gh_headers, data=gh_payload, timeout=3
        )
        gh_webhook_response.raise_for_status()
        print(f"Confirmation Message sent ({gh_webhook_response.status_code})")
    except requests.exceptions.Timeout:
        print("GitHub Action punt timed out. Try again.")
    except requests.exceptions.TooManyRedirects:
        print("Bad URL")
    except requests.exceptions.HTTPError as nc_err:
        raise SystemExit(nc_err) from nc_err
    except requests.exceptions.RequestException as nc_cat_exception:
        raise SystemExit(nc_cat_exception) from nc_cat_exception


def survey_to_mongo(surv_lst, pern_id, p_guid):
    ts = datetime.now()
    record = survey_collection.insert_one(
        {
            "ts": ts,
            "person_email": pern_id,
            "person_guid": p_guid,
            "survey_lst": surv_lst,
        }
    )
    record_id = record.inserted_id
    print(f"Inserted Object ID: {record_id}")
    return str(record_id)


def send_rsvps_gh(rsvp_nameid):
    name_id = str(rsvp_nameid)
    gh_headers = {
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "Authorization": github_pat,
    }
    gh_payload = json.dumps(
        {
            "event_type": "FUSE_RSVPs",
            "client_payload": {"rsvp_nameId": name_id},
        }
    )

    gh_webhook_url = "https://api.github.com/repos/dirflash/fuse/dispatches"
    try:
        gh_webhook_response = requests.request(
            "POST", gh_webhook_url, headers=gh_headers, data=gh_payload, timeout=3
        )
        gh_webhook_response.raise_for_status()
        print(f"Confirmation Message sent ({gh_webhook_response.status_code})")
    except requests.exceptions.Timeout:
        print("GitHub Action punt timed out. Try again.")
    except requests.exceptions.TooManyRedirects:
        print("Bad URL")
    except requests.exceptions.HTTPError as nc_err:
        raise SystemExit(nc_err) from nc_err
    except requests.exceptions.RequestException as nc_cat_exception:
        raise SystemExit(nc_cat_exception) from nc_cat_exception


def rsvp_to_mongo(pn_id, pn_name, fus_date, act):
    ts = datetime.now()
    anon_name = re.sub(r".{3}$", "xxx", pn_name)
    r_exist = response_collection.find({"pn_name": pn_name, fus_date: {"$exists": 1}})
    r_exist_cnt = response_collection.count_documents(
        {"pn_name": pn_name, fus_date: {"$exists": 1}}
    )
    if r_exist_cnt > 0:
        for entry in r_exist:
            print("record exists")
            if entry[fus_date] == act:
                print("Response hasn't changed.")
            else:
                print("Updated response. Change record.")
                try:
                    update_rsvp_rec = response_collection.update_one(
                        {"pn_name": pn_name}, {"$set": {fus_date: act}}
                    )
                    if update_rsvp_rec.modified_count == 1:
                        print(f"{anon_name} db record updated with new response")
                except errors.OperationFailure as op_fail:
                    print(f"rsvp_to_mongo update failure ({op_fail}) for {anon_name}.")
    else:
        record = response_collection.insert_one(
            {
                "ts": ts,
                "person_email": pn_id,
                "pn_name": pn_name,
                fus_date: act,
            }
        )
        if bool(record.inserted_id) is True:
            record_id = record.inserted_id
            print(f"ObjectId {str(record_id)} created for {anon_name}")
            return


def maybe_rsvps(maybe_r, r_ts, fuse_d):
    print("Create list of no responses")
    maybe_go_dict = {}
    status_list = []
    maybe_goes = maybe_r[
        (maybe_r["Response"] == "None") & (maybe_r["Attendance"] == "Required Attendee")
    ]
    maybe_go_alias = maybe_goes[["Alias"]]
    no_go_alias_lst = maybe_go_alias["Alias"].to_list()
    maybe_go_name = maybe_goes[["Full Name"]]
    maybe_go_name_lst = maybe_go_name["Full Name"].to_list()
    for idx, name in enumerate(maybe_go_name_lst):
        maybe_go_dict["name"] = name
        maybe_go_dict["email"] = no_go_alias_lst[idx] + "@cisco.com"
        maybe_go_dict["status"] = "None"
        maybe_go_dict["fuse_date"] = fuse_d
        maybe_go_dict["ts"] = r_ts
        status_list.append(maybe_go_dict.copy())
    print(f"Number of no responses: {len(status_list)}")
    return status_list


def no_rsvps(no_r, r_ts, fuse_d):
    print("Create list of declined responses")
    no_go_dict = {}
    status_list = []
    no_goes = no_r[
        (no_r["Response"] == "Declined") & (no_r["Attendance"] == "Required Attendee")
    ]
    no_go_alias = no_goes[["Alias"]]
    no_go_alias_lst = no_go_alias["Alias"].to_list()
    no_go_name = no_goes[["Full Name"]]
    no_go_name_lst = no_go_name["Full Name"].to_list()
    for idx, name in enumerate(no_go_name_lst):
        no_go_dict["name"] = name
        no_go_dict["email"] = no_go_alias_lst[idx] + "@cisco.com"
        no_go_dict["status"] = "Declined"
        no_go_dict["fuse_date"] = fuse_d
        no_go_dict["ts"] = r_ts
        status_list.append(no_go_dict.copy())
    print(f"Number of declined responses: {len(status_list)}")
    return status_list


def yes_rsvps(yes_r, r_ts, fuse_d):
    print("Create list of accepted responses")
    yes_go_dict = {}
    status_list = []
    yes_goes = yes_r[
        (yes_r["Response"] == "Accepted") & (yes_r["Attendance"] == "Required Attendee")
    ]
    yes_go_alias = yes_goes[["Alias"]]
    yes_go_alias_lst = yes_go_alias["Alias"].to_list()
    yes_go_name = yes_goes[["Full Name"]]
    yes_go_name_lst = yes_go_name["Full Name"].to_list()
    for idx, name in enumerate(yes_go_name_lst):
        yes_go_dict["name"] = name
        yes_go_dict["email"] = yes_go_alias_lst[idx] + "@cisco.com"
        yes_go_dict["status"] = "Accepted"
        yes_go_dict["fuse_date"] = fuse_d
        yes_go_dict["ts"] = r_ts
        status_list.append(yes_go_dict.copy())
    print(f"Number of accepted responses: {len(status_list)}")
    return status_list


def status_records(x_lst, setting):
    print(f"Update status records for {setting}.")
    for x in x_lst:
        name = x["name"]
        email = x["email"]
        status = x["status"]
        fuse_date = x["fuse_date"]
        ts = x["ts"]
        anon_name = re.sub(r".{3}$", "xxx", name)
        r_exist = status_collection.find({"name": name, "fuse_date": fuse_date})
        r_exist_cnt = status_collection.count_documents(
            {"name": name, "fuse_date": fuse_date}
        )
        if r_exist_cnt > 0:
            for r in r_exist:
                if status != r["status"]:
                    r_id = r["_id"]
                    print(f"Status does not match for {r_id}. Updating...")
                    try:
                        status_update_db = status_collection.update_one(
                            {"name": name, "fuse_date": fuse_date},
                            {"$set": {"status": status}},
                        )
                        if status_update_db.modified_count == 1:
                            print(
                                f"{anon_name} db record updated with new response of {status}."
                            )
                    except errors.OperationFailure as op_fail:
                        print(
                            f"status_update_db update failure ({op_fail}) for {anon_name}."
                        )
        else:
            record = status_collection.insert_one(
                {
                    "name": name,
                    "email": email,
                    "status": status,
                    "fuse_date": fuse_date,
                    "ts": ts,
                }
            )
            if bool(record.inserted_id) is True:
                record_id = record.inserted_id
                print(
                    f"ObjectId {str(record_id)} created for {anon_name} in status collection"
                )


def on_it_message(person_id):
    on_it_msg = "That process has been kicked off and will take a couple of minutes to complete."
    on_it_payload = json.dumps({"toPersonEmail": person_id, "markdown": on_it_msg})
    try:
        on_it_note = requests.request(
            "POST", post_msg_url, headers=headers, data=on_it_payload, timeout=3
        )
        on_it_note.raise_for_status()
        print(f"On it message sent ({on_it_note.status_code})")
    except requests.exceptions.Timeout:
        print("On it message timed out. Try again.")
    except requests.exceptions.TooManyRedirects:
        print("Bad URL")
    except requests.exceptions.HTTPError as nc_err:
        raise SystemExit(nc_err) from nc_err
    except requests.exceptions.RequestException as nc_cat_exception:
        raise SystemExit(nc_cat_exception) from nc_cat_exception


def self_report(fuses_date):
    r_up_list = []
    r_up_dict = {}
    r_updates_cnt = rsvp_collection.count_documents({"fuse_date": fuses_date})
    if r_updates_cnt > 0:
        r_updates = rsvp_collection.find({"fuse_date": fuses_date})
        for r_up in r_updates:
            r_up_name = r_up["name"]
            r_up_status = r_up["response"]
            r_up_dict["name"] = r_up_name
            r_up_dict["response"] = r_up_status
            r_up_list.append(r_up_dict.copy())
    return r_up_list


def self_report_sort(r_updates):
    n_lst = []
    y_lst = []
    for ups in r_updates:
        if ups["response"] == "rsvp.yes":
            y_lst.append(ups["name"])
        elif ups["response"] == "rsvp.no":
            n_lst.append(ups["name"])
    return (y_lst, n_lst)


def help_me(p_id):
    print("Somebody has a question.")
    herder_payload = json.dumps(
        {
            "toPersonEmail": p_id,
            "markdown": "Got a question? Need to report a bot problem? Contact the bot herders [here](webexteams://im?space=7a97b910-c443-11ed-9a0a-47c2acdafc72).",
        }
    )
    try:
        post_msg_r = requests.request(
            "POST", post_msg_url, headers=headers, data=herder_payload, timeout=3
        )
        post_msg_r.raise_for_status()
        print(f"Confirmation Message sent ({post_msg_r.status_code})")
    except requests.exceptions.Timeout:
        print("Timeout error. Try again.")
    except requests.exceptions.TooManyRedirects:
        print("Bad URL")
    except requests.exceptions.HTTPError as nc_err:
        raise SystemExit(nc_err) from nc_err
    except requests.exceptions.RequestException as nc_cat_exception:
        raise SystemExit(nc_cat_exception) from nc_cat_exception


if action != "rsvp.yes":
    if action != "rsvp.no":
        if msg_txt == "?":
            help_me(person_id)
            sys.exit()
        if person_id in auth_mgrs:
            print("Authorized manager.")
            if msg_txt != "":
                set_date = get_fuse_date(date_collection)
                mgr_card(set_date)
                kill_switch = True
                sys.exit()
        chat_id, chat_email, chat_url = chat_record(person_id)
        try:
            # get file attachment
            get_attach_response = requests.request(
                "GET", chat_url, headers=headers, timeout=3
            )
            get_attach_response.raise_for_status()
            print(f"Attachment received: ({get_attach_response.status_code})")
            cnt_disp = get_attach_response.headers.get("content-disposition")
            if bool(cnt_disp) is True:
                print(
                    "'content-disposition' exists in the headers. Pulling out filename."
                )
                RAW_FILE_NAME = get_attach_response.headers.get("content-disposition")
                file = RAW_FILE_NAME.split('"')[1::2]
                file_name = file[0]
                print(f"Attachment filename: {file_name}")
            else:
                print(
                    "'content-disposition' metadata not available. Defaulting file name."
                )
                file_name = "csv.csv"
        except requests.exceptions.Timeout:
            print("Timeout error. Try again.")
        except requests.exceptions.TooManyRedirects:
            print("Bad URL")
        except requests.exceptions.HTTPError as err:
            failed_msg(person_id)
            raise SystemExit(err) from err
        except requests.exceptions.RequestException as cat_exception:
            failed_msg(person_id)
            raise SystemExit(cat_exception) from cat_exception

        try:
            attach = get_attach_response.text
            with open(file_name, "w", newline="\r\n", encoding="utf-8") as out:
                out.write(attach)
        except:
            print("Unable to convert attachment to file.")
            raise SystemExit()

        try:
            df = pd.read_csv(file_name, header=0)
            print(df.head(2))
        except OSError as e:
            sys.exit("CSV file not found!")

        print(f"Imported header names: {list(df.columns.values)}")
        header_check(df)

        df1 = alias_format(df)
        df2 = x_dups(df1)
        no_resp, yes_respond, declined_respond = responses(df2)

        # print(f"no_resp: \n {no_resp}\n")
        # print(f"yes_respond: \n {yes_respond}\n")
        # print(f"declined_respond: \n {declined_respond}\n")

        print(f"Requested action: {action}")

        if action != "survey_submit":
            set_date = get_fuse_date(date_collection)
            if set_date == "NA":
                date_msg = f"Fuse date not set."
                sdc = set_date_card(date_msg)
                mgr_control(sdc)
                print("Fuse date not set. Requested date and exited.")
                os._exit(1)
            else:
                fuses_date = set_date

        rsvp_ts = datetime.now()
        maybe_lst = maybe_rsvps(no_resp, rsvp_ts, fuses_date)
        no_lst = no_rsvps(declined_respond, rsvp_ts, fuses_date)
        yes_lst = yes_rsvps(yes_respond, rsvp_ts, fuses_date)
        status_records(maybe_lst, "Unknown")
        status_records(no_lst, "Declined")
        status_records(yes_lst, "Accepted")

print(f"Action: {action}")

if action == "attend_report":
    num_none = len(no_resp)
    num_yes = len(yes_respond)
    num_no = len(declined_respond)
    att_rep_card = attend_report_card(
        maybe_lst, no_lst, yes_lst, fuses_date, num_none, num_yes, num_no
    )
    attend_report_msg(att_rep_card, person_id)
    response_updates = self_report(fuses_date)
    if len(response_updates) > 0:
        print("Responses received")
        print("Sort through responses")
        self_yes, self_no = self_report_sort(response_updates)
        srrc = self_resp_report_card(self_no, self_yes, fuses_date)
        attend_report_msg(srrc, person_id)
    else:
        print("No responses")
        pl_title = "**No participant updates from Fuse bot.**"
        payload = json.dumps(
            {
                "toPersonEmail": person_id,
                "markdown": pl_title,
            }
        )
        try:
            post_msg_r = requests.request(
                "POST", post_msg_url, headers=headers, data=payload, timeout=3
            )
            post_msg_r.raise_for_status()
            print(f"No participant updates message sent ({post_msg_r.status_code})")
        except requests.exceptions.Timeout:
            print("Timeout error. Try again.")
    mgr_card(fuses_date)
elif action == "noncomit_reminders":
    notify_emails_lst = noncomitted_reminders(no_resp)
    recs = rsvp_db_upload(notify_emails_lst, fuses_date)
    print("noncomit_reminders set")
    send_rsvps_gh(recs)
    on_it_message(person_id)
    mgr_card(fuses_date)
elif action == "pre_reminder":
    send_to = pre_reminder(fuses_date)
    m_cnt = 0
    for peeps in send_to:
        m_cnt += 1
        pr_email = peeps["email"]
        pr_name = peeps["name"]
        pr_f_name = pr_name.split(" ", 1)[0]
        pe_card = pre_event_card(pr_f_name)
        pre_event_notification(pr_email, pe_card)
    print(f"Attempted to send {str(m_cnt)} pre-event message reminders.")
    mgr_card(fuses_date)
elif action == "survey_msg":
    sur_card = survey_submit_card()
    survey_msg(sur_card, person_id)
elif action == "fuse_date":
    if fuse_date == "NA":
        print("Send change date card")
        date_msg = "Select the new date"
        sdc = set_date_card(date_msg)
        mgr_control(sdc)
    else:
        fuse_day = set_fuse_date(fuse_date, person_id, date_collection)
        date_msg = f"Fuse date changed to: {fuse_day}"
        fdc = manager_card(date_msg)
        mgr_control(fdc)
elif action == "survey_submit":  # Need to validate survey_url here.
    print("Survey submit action.")
    # if validators.url(survey_url) is True:
    # print(f"Valid survey URL: {survey_url}")
    # else:
    # print(f"Invalid survey URL: {survey_url}")
    print(f"Session date for survey: {session_date}")
    pst_survey_card = post_survey_card(first_name, session_date, survey_url)
    post_survey_msg(pst_survey_card, person_id)
    attach_survey_card = send_survey(session_date, survey_url)
    proof_confirmation(person_id, attach_survey_card)
elif action == "post_survey_send":
    print("Post Survey Send")
    survey_lst = surveys(no_resp, yes_respond)
    mongo_id = survey_to_mongo(survey_lst, person_id, person_guid)
    print(f"Total number of surveys to send: {len(survey_lst)}")
    print("Kick off send surveys dispatch")
    send_survey_gh(
        person_id, first_name, person_guid, action, session_date, survey_url, mongo_id
    )
    on_it_message(person_id)
    mgr_card(fuses_date)
elif action == "rsvp.yes" or action == "rsvp.no":
    rsvp_package = []
    rsvp_date = []
    rsvp_respond = (
        rsvp_response.replace("[", "")
        .replace("]", "")
        .replace("'", "")
        .replace(", ", ",")
    )
    rsvp_package = rsvp_respond.split(",")
    rsvp_date_un = str(rsvp_package[1])
    rsvp_date = rsvp_date_un.split("-")
    rsvp_d = str(rsvp_date[2]) + "-" + str(rsvp_date[0]) + "-" + str(rsvp_date[1])
    rsvp_to_mongo(person_id, person_name, rsvp_d, action)  # Response Collection
    update_lst = []
    update_dict = {}
    update_dict["name"] = person_name
    update_dict["email"] = person_id
    if action == "rsvp.yes":
        update_dict["status"] = "Accepted"
        update_response = "Accepted"
    else:
        update_dict["status"] = "Declined"
        update_response = "Declined"
    update_dict["fuse_date"] = rsvp_d
    update_dict["ts"] = datetime.now()
    update_lst.append(update_dict.copy())
    print(update_lst)
    # status_records(update_lst, update_response)
else:
    print("Unknown action.")
    failed_msg(person_id)
    if person_id in auth_mgrs:
        mgr_card(fuses_date)
