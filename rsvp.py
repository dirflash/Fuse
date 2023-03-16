import os
import sys
import re
import json
import configparser
import requests
import certifi
from pymongo import MongoClient
from datetime import datetime
from time import sleep

TEST = True

KEY = "CI"
if os.getenv(KEY):
    print("Running as GitHub Action.")
    webex_bearer = os.environ["webex_bearer"]
    mongo_addr = os.environ["MONGO_ADDR"]
    mongo_db = os.environ["MONGO_DB"]
    mongo_un = os.environ["MONGO_UN"]
    mongo_pw = os.environ["MONGO_PW"]
    rsvp_collect = os.environ["RSVP_COLLECT"]
    rsvp_list = os.environ["rsvp_list"]
else:
    print("Running locally.")
    config = configparser.ConfigParser()
    config.read("./secrets/config.ini")
    webex_bearer = config["DEFAULT"]["webex_key"]
    mongo_addr = config["MONGO"]["MONGO_ADDR"]
    mongo_db = config["MONGO"]["MONGO_DB"]
    mongo_un = config["MONGO"]["MONGO_UN"]
    mongo_pw = config["MONGO"]["MONGO_PW"]
    rsvp_collect = config["MONGO"]["RSVP_COLLECT"]
    rsvp_list = str(
        [
            "Aaron Hagen",
            "Darrell Lee",
            "Khoi Pham",
        ]
    )


MAX_MONGODB_DELAY = 500

Mongo_Client = MongoClient(
    f"mongodb+srv://{mongo_un}:{mongo_pw}@{mongo_addr}/{mongo_db}?retryWrites=true&w=majority",
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=MAX_MONGODB_DELAY,
)

db = Mongo_Client[mongo_db]
rsvp_collection = db[rsvp_collect]

post_msg_url = "https://webexapis.com/v1/messages/"

headers = {
    "Authorization": webex_bearer,
    "Content-Type": "application/json",
}


def send_rsvp(s_name, s_date):
    body_1 = f"Hello {s_name}! We noticed you have not confirmed your availability for the next Fuse session on {s_date}. Your confirmation helps us to plan the pairings."
    body_2 = "But not to worry. You can let us know if you will attend by clicking on one of the buttons below. We hope to see you there!"
    y_meta_data = f"[rsvp.yes, {s_date}]"
    n_meta_data = f"[rsvp.no, {s_date}]"
    send_rsvp_card = {
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
                            "text": "Fuse Session RSVP Request",
                            "wrap": True,
                            "horizontalAlignment": "Center",
                            "fontType": "Monospace",
                            "size": "Large",
                            "weight": "Bolder",
                        },
                        {
                            "type": "TextBlock",
                            "text": body_1,
                            "wrap": True,
                            "fontType": "Monospace",
                            "size": "Default",
                            "weight": "Bolder",
                        },
                        {
                            "type": "TextBlock",
                            "wrap": True,
                            "text": body_2,
                            "fontType": "Monospace",
                            "weight": "Bolder",
                            "size": "Default",
                        },
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
                                    "type": "ActionSet",
                                    "actions": [
                                        {
                                            "type": "Action.Submit",
                                            "title": "I'll be there!",
                                            "id": "rsvp.yes",
                                            "style": "positive",
                                            "data": y_meta_data,
                                        }
                                    ],
                                    "horizontalAlignment": "Right",
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
                                            "title": "Dang it! I can't make it.",
                                            "id": "rsvp.no",
                                            "style": "destructive",
                                            "data": n_meta_data,
                                        }
                                    ],
                                    "horizontalAlignment": "Left",
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
    return send_rsvp_card


def send_rsvp_msg(x_rsvp_card, x_email, x_name):
    payload = json.dumps(
        {
            "toPersonEmail": x_email,
            "markdown": "Adaptive card response. Open message on a supported client to respond.",
            "attachments": x_rsvp_card,
        }
    )
    try:
        pattern = r".{3}(?=@)"
        anon_email = re.sub(pattern, "xxxx", x_email)
        print(f"Sending message to {anon_email}")
        r = requests.request(
            "POST", post_msg_url, headers=headers, data=payload, timeout=2
        )
        if r.status_code == 200:
            sent_ts = datetime.now()
            update_rsvp_rec = rsvp_collection.update_one(
                {"name": x_name}, {"$set": {"reminder_sent": sent_ts}}
            )
            if update_rsvp_rec.modified_count == 1:
                print(f"{anon_email} db record updated with timestamp")
        if r.status_code == 429:
            delay_header = r.headers
            throttle_back(delay_header)
            return 429
    except requests.exceptions.Timeout:
        print("Timeout error. Try again.")
    except requests.exceptions.TooManyRedirects:
        print("Bad URL")
    except requests.exceptions.HTTPError as err:
        raise SystemExit(err) from err
    except requests.exceptions.RequestException as cat_exception:
        raise SystemExit(cat_exception) from cat_exception


def throttle_back(header_to):
    if "Retry-After" in header_to:
        pause_429 = int(header_to["Retry-After"])
    else:
        pause_429 = 300
    print(f"Oh no. Sending too many requests. Pause send for {pause_429} seconds.")
    sleep(pause_429)
    return 429


def failed_msg_mgr():
    post_msg = "https://webexapis.com/v1/messages/"
    pl_title = (
        "**Something unusual happened sending rsvp messages. Please check the logs.**"
    )
    payload = json.dumps(
        {
            "toPersonEmail": "aarodavi@cisco.com",  # ---- Need to fix this to send to send to mgr
            "markdown": pl_title,
        }
    )
    try:
        post_msg_r = requests.request(
            "POST", post_msg, headers=headers, data=payload, timeout=2
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


print("Made it to RSVP.py")

if isinstance(rsvp_list, str):
    rsvp_list = rsvp_list.replace("[", "").replace("]", "").replace("'", "")
    rsvp_l_list = rsvp_list.split(", ")
else:
    rsvp_l_list = rsvp_list

rsvp_list_cnt = len(rsvp_l_list)
# if TEST is True:
# del rsvp_l_list[5:]

for x in rsvp_l_list:
    try:
        x_exist_cnt = rsvp_collection.count_documents({"name": x})
        # print(f"x_exist_cnt: {x_exist_cnt}")
        x_exist = rsvp_collection.find_one({"name": x})
        # print(f"x_exist: {x_exist}")
        anon_per = re.sub(r".{3}$", "xxx", x)
        print(f"Found {anon_per}")
        rsvp_email = x_exist["email"]
        rsvp_fuse_date = x_exist["fuse_date"]
        day_ar = datetime.strptime(rsvp_fuse_date, "%Y-%m-%d").strftime("%m-%d-%Y")
        rsvp_card = send_rsvp(x, day_ar)
        throt_back = send_rsvp_msg(rsvp_card, rsvp_email, x)
        if throt_back == 429:
            thrott_back = send_rsvp_msg(rsvp_card, rsvp_email, x)
            print("Requested to throttle back twice. Something is wrong.")
            failed_msg_mgr()
            sys.exit(1)
    except:
        print("Didn't find record in db.")
        failed_msg_mgr()
        sys.exit(1)
