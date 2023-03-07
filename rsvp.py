import os
import sys
import json
import configparser
import requests
import certifi
from pymongo import MongoClient
from datetime import datetime
from time import sleep

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


def send_rsvp(s_date, s_url):
    body_1 = f"Hello Engineer! We noticed you have not confirmed your availability for the next Fuse session on {s_date}. Your confirmation helps us to plan the pairings."
    body_2 = "But not to worry. You can let us know if you will attend by clicking on one of the buttons below. We hope to see you there!"
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
                            "url": "https://user-images.githubusercontent.com/10964629/216710865-00ba284d-b9b1-4b8a-a8a0-9f3f07b7d962.jpg",
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


def noncomit_reminders(noes):
    no_rsvp_email = []
    print("Requested action: Send Non Committed Reminders")
    noncommited = noes[
        (noes["Response"] == "None") & (noes["Attendance"] == "Required Attendee")
    ]
    num_noncommited = len(noncommited)
    print(f"\nNoncommited Attendees: {num_noncommited}")
    # The following 3 lines takes the "Full Name" column, converts it to a list, then to
    # a string to solve formatting issues in the "send_confirmation" function.
    noncommited_names = noncommited[["Full Name"]]
    noncommited_list = noncommited_names["Full Name"].to_list()
    noncommited_list2str = "\n".join(str(e) for e in noncommited_list)
    noncommited_alias_lst = noncommited[
        "Alias"
    ].values.tolist()  # list of email addresses to send reminder.
    for _ in noncommited_alias_lst:
        no_rsvp_email.append(_ + "@cisco.com")
    send_confirmation(noncommited_list2str, no_rsvp_email, num_noncommited, person_id)
    return no_rsvp_email


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
                "POST", post_msg, headers=headers, data=payload, timeout=2
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


def send_survey_gh(p_id, f_name, act, sess_date, surv_url, mong_id):
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
            "POST", gh_webhook_url, headers=gh_headers, data=gh_payload, timeout=2
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


def survey_to_mongo(surv_lst, pern_id):
    ts = datetime.now()
    record = survey_collection.insert_one(
        {"ts": ts, "person_email": pern_id, "survey_lst": surv_lst}
    )
    record_id = record.inserted_id
    print(f"Inserted Object ID: {record_id}")
    return str(record_id)


print("Made it to RSVP.py")

"""
g = rsvp_collection.find().sort("_id", -1).limit(1)
for _ in g:
    if str(_["_id"]) == mongo_rec_id:
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
        sys.exit(1)
"""
