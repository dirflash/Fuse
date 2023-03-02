import os
import sys
import json
import configparser
import requests
import pandas as pd
import certifi
from pymongo import MongoClient, DESCENDING
from datetime import datetime, timezone

KEY = "CI"
if os.getenv(KEY):
    print("Running as GitHub Action.")
    webex_bearer = os.environ["webex_bearer"]
    person_id = os.environ["person_id"]
    first_name = os.environ["first_name"]
    action = os.environ["action"]
    survey_url = os.environ["survey_url"]
    session_date = os.environ["session_date"]
    auth_mgrs = os.environ["auth_mgrs"]
    mongo_addr = os.environ["MONGO_ADDR"]
    mongo_db = os.environ["MONGO_DB"]
    bridge_collect = os.environ["BRIDGE_COLLECT"]
    response_collect = os.environ["RESPONSE_COLLECT"]
    date_collect = os.environ["DATE_COLLECT"]
    mongo_un = os.environ["MONGO_UN"]
    mongo_pw = os.environ["MONGO_PW"]
    fuse_date = os.environ["FUSE_DATE"]
else:
    print("Running locally.")
    config = configparser.ConfigParser()
    config.read("./secrets/config.ini")
    webex_bearer = config["DEFAULT"]["webex_key"]
    person_id = config["DEFAULT"]["person_id"]
    first_name = "Bob"
    auth_mgrs = config["DEFAULT"]["auth_mgrs"]
    action = "survey_submit"
    survey_url = "https://www.cisco.com"
    session_date = "2023-03-15"
    mongo_addr = config["MONGO"]["MONGO_ADDR"]
    mongo_db = config["MONGO"]["MONGO_DB"]
    bridge_collect = config["MONGO"]["BRIDGE_COLLECT"]
    date_collect = config["MONGO"]["DATE_COLLECT"]
    response_collect = config["MONGO"]["RESPONSE_COLLECT"]
    mongo_un = config["MONGO"]["MONGO_UN"]
    mongo_pw = config["MONGO"]["MONGO_PW"]
    fuse_date = "NA"

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
                                            "wrap": True,
                                        },
                                        {
                                            "title": "Attendee Report",
                                            "value": "attend_report",
                                        },
                                        {
                                            "title": "Send RSVP Reminder",
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
                                            "text": set_date,
                                            "horizontalAlignment": "Center",
                                            "fontType": "Monospace",
                                            "color": "Warning",
                                            "wrap": True,
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
                                                {
                                                    "type": "Action.Submit",
                                                    "title": "Submit",
                                                }
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
    r = requests.request("POST", post_msg_url, headers=headers, data=payload, timeout=2)
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
                            "url": "https://user-images.githubusercontent.com/10964629/216710865-00ba284d-b9b1-4b8a-a8a0-9f3f07b7d962.jpg",
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
                            "url": "https://user-images.githubusercontent.com/10964629/216710865-00ba284d-b9b1-4b8a-a8a0-9f3f07b7d962.jpg",
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
    meta_msg = f'["{s_date}", "{s_url}"]'
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
                            "url": "https://user-images.githubusercontent.com/10964629/216710865-00ba284d-b9b1-4b8a-a8a0-9f3f07b7d962.jpg",
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
            "POST", post_msg_url, headers=headers, data=payload, timeout=2
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


def attend_report(silent_response, confirmed_response, denied_response, email):
    # print("Attendance Report")
    # print(silent_response.head())
    pl_title = (
        "Number of noncommited attendees: "
        + str(len(silent_response))
        + "\nNumber of confirmed attendees: "
        + str(len(confirmed_response))
        + "\nNumber of declined attendees: "
        + str(len(denied_response))
    )
    payload = json.dumps(
        {
            "toPersonEmail": email,
            "markdown": pl_title,
        }
    )
    try:
        post_msg_r = requests.request(
            "POST", post_msg_url, headers=headers, data=payload, timeout=2
        )
        post_msg_r.raise_for_status()
        print(f"Attendance Report Message sent ({post_msg_r.status_code})")
    except requests.exceptions.Timeout:
        print("Timeout error. Try again.")
    except requests.exceptions.TooManyRedirects:
        print("Bad URL")
    except requests.exceptions.HTTPError as nc_err:
        raise SystemExit(nc_err) from nc_err
    except requests.exceptions.RequestException as nc_cat_exception:
        raise SystemExit(nc_cat_exception) from nc_cat_exception


def report_to_manager(nc, no_nc, email):
    nnc = str(no_nc)
    post_msg = "https://webexapis.com/v1/messages/"
    pl_title = (
        f"## Number of noncommited attendees: {nnc}\n\n{nc}\n\n### Sending reminders."
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


def noncomit_reminders(noes):
    no_rsvp_email = []
    print("Requested action: Send Non Committed Reminders")
    noncommited = noes[
        (noes["Response"] == "None") & (noes["Attendance"] == "Required Attendee")
    ]
    num_noncommited = len(noncommited)
    print(f"\nNoncommited Attendees: {num_noncommited}")
    # The following 3 lines takes the "Full Name" column, converts it to a list, then to
    # a string to solve formatting issues in the "report_to_manager" function.
    noncommited_names = noncommited[["Full Name"]]
    noncommited_list = noncommited_names["Full Name"].to_list()
    noncommited_list2str = "\n".join(str(e) for e in noncommited_list)
    noncommited_alias_lst = noncommited[
        "Alias"
    ].values.tolist()  # list of email addresses to send reminder.
    for _ in noncommited_alias_lst:
        no_rsvp_email.append(_ + "@cisco.com")
    report_to_manager(noncommited_list2str, num_noncommited, person_id)
    return no_rsvp_email


def pre_reminder():
    print("Pre Event Reminders")


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
            "POST", post_msg, headers=headers, data=payload, timeout=2
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
    recent_chat = (
        bridge_collection.find({"person_email": per_id}).sort("ts", DESCENDING).limit(1)
    )
    for _ in recent_chat:
        doc_id = {"_id": _["_id"]}
        doc_per_email = _["person_email"]
        doc_attach_url = _["attachment"]
        print(f"Found most recent request from {doc_per_email}...")
        print(f"with attachment URL: {doc_attach_url}")
        # print(bridge_collection.find_one(doc_id))
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
            "POST", post_msg, headers=headers, data=payload, timeout=2
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
    # a string to solve formatting issues in the "report_to_manager" function.
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


if person_id in auth_mgrs:
    print("Authorized manager.")
else:
    print("Not an authorized manager.")
    not_authd_mgr(person_id)
    sys.exit()

chat_id, chat_email, chat_url = chat_record(person_id)

try:
    # get file attachment
    get_attach_response = requests.request("GET", chat_url, headers=headers, timeout=2)
    get_attach_response.raise_for_status()
    print(f"Attachment received: ({get_attach_response.status_code})")
    cnt_disp = get_attach_response.headers.get("content-disposition")
    if bool(cnt_disp) is True:
        print("'content-disposition' exists in the headers. Pulling out filename.")
        RAW_FILE_NAME = get_attach_response.headers.get("content-disposition")
        file = RAW_FILE_NAME.split('"')[1::2]
        file_name = file[0]
        print(f"Attachment filename: {file_name}")
    else:
        print("'content-disposition' metadata not available. Defaulting file name.")
        file_name = "csv.csv"
except requests.exceptions.Timeout:
    print("Timeout error. Try again.")
except requests.exceptions.TooManyRedirects:
    print("Bad URL")
except requests.exceptions.HTTPError as err:
    raise SystemExit(err) from err
except requests.exceptions.RequestException as cat_exception:
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


if action == "attend_report":
    attend_report(no_resp, yes_respond, declined_respond, person_id)
    mgr_card(fuses_date)
elif action == "noncomit_reminders":
    notify_emails_lst = noncomit_reminders(no_resp)
    mgr_card(fuses_date)
elif action == "pre_reminder":
    pre_reminder()
    mgr_card(fuses_date)
elif action == "survey_msg":
    sur_card = survey_submit_card()
    survey_msg(sur_card, person_id)
    # mgr_card(fuses_date)
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
elif action == "survey_submit":
    print("Survey submit action.")
    print(f"Survey URL: {survey_url}")
    print(f"Session date for survey: {session_date}")
    pst_survey_card = post_survey_card(first_name, session_date, survey_url)
    post_survey_msg(pst_survey_card, person_id)
    attach_survey_card = send_survey(session_date, survey_url)
    proof_confirmation(person_id, attach_survey_card)
elif action == "post_survey_send":
    print("Post Survey Send")
    survey_lst = surveys(no_resp, yes_respond)
    print(f"Total number of surveys to send: {len(survey_lst)}")
    # survey_dispatch(person_id, session_date, survey_url, survey_lst)
    print("Kick off send surveys dispatch")

else:
    print("Unknown action.")
    failed_msg(person_id)


"""
    noncommited_names = noncommited[["Full Name"]]
    noncommited_list = noncommited_names["Full Name"].to_list()
    noncommited_list2str = "\n".join(str(e) for e in noncommited_list)
    noncommited_alias_lst = noncommited[
        "Alias"
    ].values.tolist()  # list of email addresses to send reminder.
    for _ in noncommited_alias_lst:
        no_rsvp_email.append(_ + "@cisco.com")
    report_to_manager(noncommited_list2str, num_noncommited, person_id)
    return no_rsvp_email
"""

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
