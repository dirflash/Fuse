import os
import sys
import configparser
import json
import requests
import pandas as pd
import certifi
from pymongo import MongoClient
from datetime import datetime, timezone


def timestamp():
    now = datetime.now(timezone.utc)
    dt_str = now.strftime("%Y-%m-%dT%H-%M-%S.%f")
    dt_form_ms = dt_str[:-2]
    dt_form = dt_form_ms + "Z"
    return dt_form


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
    df[["Full Name", "Alias"]] = df["Name"].apply(
        lambda x: pd.Series(str(x).split("("))
    )
    dframe["Alias"] = dframe["Alias"].str.replace(r"\)", "", regex=True)
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
    print(f"Not responded: {len(no_respond)}")
    return no_respond


def post_noncommited(nc, no_nc, email):
    post_msg = "https://webexapis.com/v1/messages/"
    pl_title = (
        "## Number of noncommited attendees: "
        + str(no_nc)
        + "\n---\n"
        + nc
        + "\n\n### Sending reminders."
    )
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
        print(f"Noncommited List Message sent ({post_msg_r.status_code})")
    except requests.exceptions.Timeout:
        print(f"Timeout error. Try again. Line: {sys._getframe().f_lineno}")
    except requests.exceptions.TooManyRedirects:
        print("Bad URL")
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
    ts = os.environ["ts"]
    attachment = os.environ["attachment"]
    room_id = os.environ["room_id"]
    room_type = os.environ["room_type"]
    person_id = os.environ["person_id"]
    # person_un = os.environ["person_un"]
    person_display = os.environ["person_display"]
    person_email = os.environ["person_email"]
    auth_mgrs = os.environ["auth_mgrs"]
    mongo_addr = os.environ["MONGO_ADDR"]
    mongo_db = os.environ["MONGO_DB"]
    bridge_collect = os.environ["BRIDGE_COLLECT"]
    response_collect = os.environ["RESPONSE_COLLECT"]
    mongo_un = os.environ["MONGO_UN"]
    mongo_pw = os.environ["MONGO_PW"]
else:
    print("Running locally.")
    config = configparser.ConfigParser()
    config.read("./secrets/config.ini")
    ts = timestamp()
    webex_bearer = config["DEFAULT"]["webex_key"]
    attachment = config["DEFAULT"]["attachment"]
    room_id = config["DEFAULT"]["room_id"]
    room_type = config["DEFAULT"]["room_type"]
    person_id = config["DEFAULT"]["person_id"]
    # person_un =
    person_display = config["DEFAULT"]["person_display"]
    person_email = config["DEFAULT"]["person_email"]
    auth_mgrs = config["DEFAULT"]["auth_mgrs"]
    mongo_addr = config["MONGO"]["MONGO_ADDR"]
    mongo_db = config["MONGO"]["MONGO_DB"]
    bridge_collect = config["MONGO"]["BRIDGE_COLLECT"]
    response_collect = config["MONGO"]["RESPONSE_COLLECT"]
    mongo_un = config["MONGO"]["MONGO_UN"]
    mongo_pw = config["MONGO"]["MONGO_PW"]

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

RAW_FILE_NAME = ""
NONCOMMITED_LST = []

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

"""
try:
    # get file attachment
    get_attach_response = requests.request(
        "GET", attachment, headers=headers, timeout=2
    )
    get_attach_response.raise_for_status()
    print(f"Attachment received: ({get_attach_response.status_code})")
    RAW_FILE_NAME = get_attach_response.headers["content-disposition"]
except requests.exceptions.Timeout:
    print("Timeout error. Try again.")
except requests.exceptions.TooManyRedirects:
    print("Bad URL")
except requests.exceptions.HTTPError as err:
    raise SystemExit(err) from err
except requests.exceptions.RequestException as cat_exception:
    raise SystemExit(cat_exception) from cat_exception

if RAW_FILE_NAME:
    file = RAW_FILE_NAME.split('"')[1::2]
    file_name = file[0]
    print(f"Attachment file name: {file_name}")
else:
    print("Empty file attachment!")
    raise SystemExit()

try:
    attach = get_attach_response.text
    with open(file_name, "w", newline="\r\n", encoding="utf-8") as out:
        out.write(attach)
except:
    print("Unable to convert attachment to file.")
    raise SystemExit()

try:
    df = pd.read_csv(file_name, header=0)
    # print(df.head(2))
except OSError as e:
    sys.exit("CSV file not found!")

print(f"Imported header names: {list(df.columns.values)}")
header_check(df)

df1 = alias_format(df)
df2 = x_dups(df1)
no_resp = responses(df2)

print(ts)
print(attachment)
print(room_id)
print(room_type)
print(person_id)
print(person_display)
print(person_email)
"""

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
