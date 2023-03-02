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
    person_id = os.environ["person_id"]
    first_name = os.environ["first_name"]
    action = os.environ["action"]
    survey_url = os.environ["survey_url"]
    session_date = os.environ["session_date"]
    github_pat = os.environ["GITHUB_PAT"]
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
    github_pat = config["DEFAULT"]["FUSE_PAT"]
    person_id = config["DEFAULT"]["person_id"]
    first_name = "Bob"
    action = "survey_submit"
    survey_url = "https://www.cisco.com"
    session_date = "2023-03-15"


def send_survey_gh(p_id, act, sess_date, surv_url):
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
                "action": act,
                "session_date": sess_date,
                "survey_url": surv_url,
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


send_survey_gh(person_id, action, session_date, survey_url)
