import os
import sys
import json
import configparser
import requests
import pandas as pd
import certifi
from pymongo import MongoClient

KEY = "CI"
if os.getenv(KEY):
    print("Running as GitHub Action.")
    webex_bearer = os.environ["webex_bearer"]
    person_id = os.environ["person_id"]
    first_name = os.environ["first_name"]
    action = os.environ["action"]
    survey_url = os.environ["survey_url"]
    session_date = os.environ["session_date"]
    mongo_addr = os.environ["MONGO_ADDR"]
    mongo_db = os.environ["MONGO_DB"]
    survey_collect = os.environ["SURVEY_COLLECT"]
    mongo_un = os.environ["MONGO_UN"]
    mongo_pw = os.environ["MONGO_PW"]
    mongo_rec_id = os.environ["MONGO_ID"]
else:
    print("Running locally.")
    config = configparser.ConfigParser()
    config.read("./secrets/config.ini")
    webex_bearer = config["DEFAULT"]["webex_key"]
    person_id = config["DEFAULT"]["person_id"]
    first_name = "Bob"
    action = "survey_submit"
    survey_url = "https://www.cisco.com"
    session_date = "2023-03-15"
    mongo_addr = config["MONGO"]["MONGO_ADDR"]
    mongo_db = config["MONGO"]["MONGO_DB"]
    mongo_un = config["MONGO"]["MONGO_UN"]
    mongo_pw = config["MONGO"]["MONGO_PW"]
    survey_collect = config["MONGO"]["SURVEY_COLLECT"]
    mongo_rec_id = "640126f547e18815668ae480"

MAX_MONGODB_DELAY = 500

Mongo_Client = MongoClient(
    f"mongodb+srv://{mongo_un}:{mongo_pw}@{mongo_addr}/{mongo_db}?retryWrites=true&w=majority",
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=MAX_MONGODB_DELAY,
)

db = Mongo_Client[mongo_db]
survey_collection = db[survey_collect]


print("Hello Fuse Manager")

g = survey_collection.find().sort("_id", -1).limit(1)
for _ in g:
    if str(_["_id"]) == mongo_rec_id:
        id_check = True
        emails = _["survey_lst"]
        print(f"Number of messages to send: {len(emails)}")
    else:
        id_check = False
        sys.exit(1)

"""
if id_check is True:
    for _ in emails:
        rate_limited_msg(_)
"""
