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
    msg_txt = os.environ["msg_txt"]
    person_email = os.environ["person_email"]
    person_guid = os.environ["person_guid"]
    auth_mgrs = os.environ["auth_mgrs"]
    mongo_addr = os.environ["MONGO_ADDR"]
    mongo_db = os.environ["MONGO_DB"]
    bridge_collect = os.environ["BRIDGE_COLLECT"]
    response_collect = os.environ["RESPONSE_COLLECT"]
    date_collect = os.environ["DATE_COLLECT"]
    mongo_un = os.environ["MONGO_UN"]
    mongo_pw = os.environ["MONGO_PW"]
    ts = os.environ["ts"]
    attachment = os.environ["attachment"]
else:
    print("Running locally.")
    config = configparser.ConfigParser()
    config.read("./secrets/config.ini")
    webex_bearer = config["DEFAULT"]["webex_key"]
    msg_txt = "?"
    person_email = config["DEFAULT"]["person_email"]
    person_guid = config["DEFAULT"]["person_guid"]
    auth_mgrs = config["DEFAULT"]["auth_mgrs"]
    mongo_addr = config["MONGO"]["MONGO_ADDR"]
    mongo_db = config["MONGO"]["MONGO_DB"]
    bridge_collect = config["MONGO"]["BRIDGE_COLLECT"]
    response_collect = config["MONGO"]["RESPONSE_COLLECT"]
    date_collect = config["MONGO"]["DATE_COLLECT"]
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


def manager_card(n_date):
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
                                    "text": n_date,
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


def set_date_card():
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
                    "text": "Date not set",
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


def mgr_control(c_card, p_email):
    payload = json.dumps(
        {
            "toPersonEmail": p_email,
            "markdown": "Adaptive card response. Open message on a supported client to respond.",
            "attachments": c_card,
        }
    )
    r = requests.request("POST", post_msg_url, headers=headers, data=payload, timeout=3)
    return r


def fix_ts(rec_id: str, tmstmp: str):
    try:
        tmsp = datetime.strptime(tmstmp, "%Y-%m-%dT%H:%M:%S.%fZ")
        bridge_collection.update_one({"_id": rec_id}, {"$set": {"ts": tmsp}})
        print("Timestamp record converted from str to date and updated.")
    except ConnectionFailure as key_error:
        print(key_error)


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

fs = date.today()
form_fs = fs.strftime("%m/%d/%Y")
fuse_date = f"Fuse date: {str(fs + timedelta(days=7))}"

post_msg_url = "https://webexapis.com/v1/messages/"

headers = {
    "Authorization": webex_bearer,
    "Content-Type": "application/json",
}


if msg_txt == "?":
    help_me(person_email)
    sys.exit()

if person_email in auth_mgrs:
    print("Authorized manager.")
else:
    print("Not an authorized manager.")
    not_authd_mgr(person_email)
    sys.exit()

if msg_txt == "":
    record = bridge_collection.insert_one(
        {"ts": ts, "person_email": person_email, "attachment": attachment}
    )
    record_id = record.inserted_id
    print(f"Inserted Object ID: {record_id}")

    fix_ts(record_id, ts)
else:
    print("Manual request for manager interface.")
    print("Skip bridge record add.")

set_date = get_fuse_date(date_collection)
if set_date == "NA":
    sdc = set_date_card()
    mgr_control(sdc, person_email)
    print("Fuse date not set. Requested date and exited.")
    os._exit(1)
else:
    day_fs = datetime.strptime(set_date, "%Y-%m-%d").strftime("%m-%d-%Y")

next_date = f"Next Fuse Date: {day_fs}"

card = manager_card(next_date)

mgr_ctl_response = mgr_control(card, person_email)
print(f"Manager control card sent with: {mgr_ctl_response}")
