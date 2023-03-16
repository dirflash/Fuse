import os
import sys
import json
import configparser
import requests
import certifi
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
from time import sleep

KEY = "CI"
if os.getenv(KEY):
    print("Running as GitHub Action.")
    webex_bearer = os.environ["webex_bearer"]
    person_id = os.environ["person_id"]
    first_name = os.environ["first_name"]
    person_guid = os.environ["person_guid"]
    action = os.environ["action"]
    survey_url = os.environ["survey_url"]
    session_date = os.environ["session_date"]
    mongo_addr = os.environ["MONGO_ADDR"]
    mongo_db = os.environ["MONGO_DB"]
    survey_collect = os.environ["SURVEY_COLLECT"]
    mongo_un = os.environ["MONGO_UN"]
    mongo_pw = os.environ["MONGO_PW"]
    mongo_rec_id = os.environ["mongo_id"]
else:
    print("Running locally.")
    config = configparser.ConfigParser()
    config.read("./secrets/config.ini")
    webex_bearer = config["DEFAULT"]["webex_key"]
    person_id = config["DEFAULT"]["person_id"]
    first_name = ""
    person_guid = config["DEFAULT"]["person_guid"]
    action = "post_survey_send"
    survey_url = "https://www.cisco.com"
    session_date = "2023-03-24"
    mongo_addr = config["MONGO"]["MONGO_ADDR"]
    mongo_db = config["MONGO"]["MONGO_DB"]
    mongo_un = config["MONGO"]["MONGO_UN"]
    mongo_pw = config["MONGO"]["MONGO_PW"]
    survey_collect = config["MONGO"]["SURVEY_COLLECT"]
    mongo_rec_id = "640d1ebe1b724590dca8c3ed"

MAX_MONGODB_DELAY = 500

Mongo_Client = MongoClient(
    f"mongodb+srv://{mongo_un}:{mongo_pw}@{mongo_addr}/{mongo_db}?retryWrites=true&w=majority",
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=MAX_MONGODB_DELAY,
)

db = Mongo_Client[mongo_db]
survey_collection = db[survey_collect]

post_msg_url = "https://webexapis.com/v1/messages/"

headers = {
    "Authorization": webex_bearer,
    "Content-Type": "application/json",
}


def survey_card(fst_name, sess_date, surv_url):
    day_fix = datetime.strptime(sess_date, "%Y-%m-%d").strftime("%m-%d-%Y")
    print(f"Need to fix first name {fst_name}")
    main_msg = f"Hello, Engineer!\n\nThank you for participating in the Fuse session on {day_fix}. Your feedback is important. It would be great if you could complete this post event survey."
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
    return send_survey_card


def throttle_back(header_to):
    if "Retry-After" in header_to:
        pause_429 = int(header_to["Retry-After"])
    else:
        pause_429 = 300
    print(f"Oh no. Sending too many requests. Pause send for {pause_429} seconds.")
    sleep(pause_429)
    return 429


def send_survey_msgs(ind, per, f_name, ttl, s_date, s_url):
    print(f"Message {ind} of {ttl} to be sent to {per}.")
    ss_card = survey_card(f_name, s_date, s_url)
    # Send the test card
    payload = json.dumps(
        {
            "toPersonEmail": per,
            "markdown": "Adaptive card response. Open message on a supported client to respond.",
            "attachments": ss_card,
        }
    )
    try:
        r = requests.request(
            "POST", post_msg_url, headers=headers, data=payload, timeout=2
        )
        if r.status_code == 429:
            delay_header = r.headers
            throttle_back(delay_header)
    except requests.exceptions.Timeout:
        print("Timeout error. Try again.")
    except requests.exceptions.TooManyRedirects:
        print("Bad URL")
    except requests.exceptions.HTTPError as err:
        raise SystemExit(err) from err
    except requests.exceptions.RequestException as cat_exception:
        raise SystemExit(cat_exception) from cat_exception
    return r.status_code


print(f"mongo_rec_id: {mongo_rec_id}")

g = survey_collection.find({"_id": ObjectId(mongo_rec_id)})

for _ in g:
    if str(_["person_guid"]) == person_guid:
        print(f"Found record ...{person_guid[len(person_guid) - 8:]}")
        id_check = True
        emails = _["survey_lst"]
        for inx, person in enumerate(emails):
            inx_plus = inx + 1
            num_emails = len(emails)
            msg_stat = send_survey_msgs(
                inx_plus,
                person,
                first_name,
                num_emails,
                session_date,
                survey_url,
            )
            if msg_stat == 429:
                print("Retry send after 429 pause.")
                msg_stat = send_survey_msgs(
                    inx_plus,
                    person,
                    first_name,
                    num_emails,
                    session_date,
                    survey_url,
                )
            print(f"Message sent to {person}: {msg_stat}")
    else:
        id_check = False
        print("Failed db record lookup.")
        sys.exit(1)
