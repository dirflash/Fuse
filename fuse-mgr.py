import os
import sys
import configparser
import json
from datetime import datetime, timezone, date, timedelta
import requests
import certifi
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure


def timestamp():
    now = datetime.now(timezone.utc)
    dt_str = now.strftime("%Y-%m-%dT%H:%M:%S.%f")
    dt_form_ms = dt_str[:-2]
    dt_form = dt_form_ms + "Z"
    return dt_form


KEY = "CI"
if os.getenv(KEY):
    print("Running as GitHub Action.")
    webex_bearer = os.environ["webex_bearer"]
    person_email = os.environ["person_email"]
    auth_mgrs = os.environ["auth_mgrs"]
    mongo_addr = os.environ["MONGO_ADDR"]
    mongo_db = os.environ["MONGO_DB"]
    bridge_collect = os.environ["BRIDGE_COLLECT"]
    response_collect = os.environ["RESPONSE_COLLECT"]
    mongo_un = os.environ["MONGO_UN"]
    mongo_pw = os.environ["MONGO_PW"]
    ts = os.environ["ts"]
    attachment = os.environ["attachment"]
else:
    print("Running locally.")
    config = configparser.ConfigParser()
    config.read("./secrets/config.ini")
    webex_bearer = config["DEFAULT"]["webex_key"]
    person_email = config["DEFAULT"]["person_email"]
    auth_mgrs = config["DEFAULT"]["auth_mgrs"]
    mongo_addr = config["MONGO"]["MONGO_ADDR"]
    mongo_db = config["MONGO"]["MONGO_DB"]
    bridge_collect = config["MONGO"]["BRIDGE_COLLECT"]
    response_collect = config["MONGO"]["RESPONSE_COLLECT"]
    mongo_un = config["MONGO"]["MONGO_UN"]
    mongo_pw = config["MONGO"]["MONGO_PW"]
    ts = timestamp()
    attachment = config["DEFAULT"]["attachment"]


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


def fix_ts(rec_id: str, tmstmp: str):
    try:
        tmsp = datetime.strptime(tmstmp, "%Y-%m-%dT%H:%M:%S.%fZ")
        bridge_collection.update_one({"_id": rec_id}, {"$set": {"ts": tmsp}})
        print("Timestamp record converted from str to date and updated.")
    except ConnectionFailure as key_error:
        print(key_error)


fs = date.today()
form_fs = fs.strftime("%m/%d/%Y")
fuse_date = f"Fuse date: {str(fs + timedelta(days=7))}"

MAX_MONGODB_DELAY = 500

Mongo_Client = MongoClient(
    f"mongodb+srv://{mongo_un}:{mongo_pw}@{mongo_addr}/{mongo_db}?retryWrites=true&w=majority",
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=MAX_MONGODB_DELAY,
)

db = Mongo_Client[mongo_db]
bridge_collection = db[bridge_collect]
response_collection = db[response_collect]

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
                                        "title": "Set Date",
                                        "value": "fuse_date",
                                    },
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
                                        "text": fuse_date,
                                        "horizontalAlignment": "Center",
                                        "fontType": "Monospace",
                                    },
                                ],
                            },
                            {
                                "type": "Column",
                                "width": "stretch",
                                "items": [
                                    {
                                        "type": "ActionSet",
                                        "actions": [
                                            {"type": "Action.Submit", "title": "Submit"}
                                        ],
                                        "horizontalAlignment": "Right",
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


if person_email in auth_mgrs:
    print("Authorized manager.")
else:
    print("Not an authorized manager.")
    not_authd_mgr(person_email)
    sys.exit()

# Add Mongo record with data file, person_un, ts
print(attachment)
print(person_email)
print(ts)

record = bridge_collection.insert_one(
    {"ts": ts, "person_email": person_email, "attachment": attachment}
)
record_id = record.inserted_id
print(f"Inserted Object ID: {record_id}")

fix_ts(record_id, ts)

mgr_ctl_response = mgr_control()
