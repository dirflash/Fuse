import os
import sys
import configparser
import json
from datetime import datetime, timezone
import requests
import certifi
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure


KEY = "CI"
if os.getenv(KEY):
    print("Running as GitHub Action.")
    webex_bearer = os.environ["webex_bearer"]
    person_email = os.environ["person_email"]
    auth_mgrs = os.environ["auth_mgrs"]
    # mongo_addr = os.environ["MONGO_ADDR"]
    # mongo_db = os.environ["MONGO_DB"]
    # bridge_collect = os.environ["BRIDGE_COLLECT"]
    # response_collect = os.environ["RESPONSE_COLLECT"]
    # mongo_un = os.environ["MONGO_UN"]
    # mongo_pw = os.environ["MONGO_PW"]
    # ts = os.environ["ts"]
    # attachment = os.environ["attachment"]
else:
    print("Running locally.")
    config = configparser.ConfigParser()
    config.read("./secrets/config.ini")
    webex_bearer = config["DEFAULT"]["webex_key"]
    person_email = config["DEFAULT"]["person_email"]
    auth_mgrs = config["DEFAULT"]["auth_mgrs"]
    # mongo_addr = config["MONGO"]["MONGO_ADDR"]
    # mongo_db = config["MONGO"]["MONGO_DB"]
    # bridge_collect = config["MONGO"]["BRIDGE_COLLECT"]
    # response_collect = config["MONGO"]["RESPONSE_COLLECT"]
    # mongo_un = config["MONGO"]["MONGO_UN"]
    # mongo_pw = config["MONGO"]["MONGO_PW"]
    # ts = timestamp()
    # attachment = config["DEFAULT"]["attachment"]

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
                "type": "ImageSet",
                "images": [
                    {
                        "type": "Image",
                        "size": "Medium",
                        "id": "fuse_image",
                        "url": "https://user-images.githubusercontent.com/10964629/216710865-00ba284d-b9b1-4b8a-a8a0-9f3f07b7d962.jpg",
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


def date_card():
    payload = json.dumps(
        {
            "toPersonEmail": person_email,
            "markdown": "Adaptive card response. Open message on a supported client to respond.",
            "attachments": mgr_card,
        }
    )
    r = requests.request("POST", post_msg_url, headers=headers, data=payload, timeout=2)
    return r


mgr_ctl_response = date_card()
