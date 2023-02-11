import os
import sys
import requests
import json
import pandas as pd

webex_bearer = os.environ["webex_bearer"]
attachment = os.environ["attachment"]
room_id = os.environ["room_id"]
room_type = os.environ["room_type"]
person_id = os.environ["person_id"]
person_email = os.environ["person_email"]
auth_mgrs = os.environ["auth_mgrs"]

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
                                "style": "Person",
                                "url": "https://user-images.githubusercontent.com/10964629/216710865-00ba284d-b9b1-4b8a-a8a0-9f3f07b7d962.jpg",
                                "size": "Medium",
                                "height": "100px",
                                "width": "400px",
                            }
                        ],
                        "width": "auto",
                    }
                ],
            },
            {
                "type": "ColumnSet",
                "columns": [
                    {
                        "type": "Column",
                        "width": 65,
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": "Fuse Bot Mission Control",
                                "weight": "Bolder",
                                "color": "Default",
                                "size": "Large",
                                "fontType": "Monospace",
                            }
                        ],
                    }
                ],
                "spacing": "Padding",
                "horizontalAlignment": "Center",
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
                                        "title": "Attendee Report",
                                        "id": "attendee_report",
                                    }
                                ],
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
                                        "title": "Send Reminders",
                                        "id": "send_remind",
                                    }
                                ],
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
                                        "type": "Action.ShowCard",
                                        "title": "Send Survey",
                                        "card": {
                                            "type": "AdaptiveCard",
                                            "body": [
                                                {
                                                    "type": "Input.Text",
                                                    "placeholder": "Survey Link",
                                                    "id": "survey_link",
                                                },
                                                {
                                                    "type": "ActionSet",
                                                    "actions": [
                                                        {
                                                            "type": "Action.Submit",
                                                            "title": "Submit",
                                                            "id": "survey_submit",
                                                        }
                                                    ],
                                                },
                                            ],
                                        },
                                        "id": "survey_card",
                                    }
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
        + "---"
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
        print("Timeout error. Try again.")
    except requests.exceptions.TooManyRedirects:
        print("Bad URL")
    except requests.exceptions.HTTPError as nc_err:
        raise SystemExit(nc_err) from nc_err
    except requests.exceptions.RequestException as nc_cat_exception:
        raise SystemExit(nc_cat_exception) from nc_cat_exception


def not_authd_mgr(email):
    post_msg = "https://webexapis.com/v1/messages/"
    pl_title = "**You don't appear to be an authorized manager of this bot.**"
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
    print(payload)
    r = requests.request("POST", post_msg_url, headers=headers, data=payload, timeout=2)
    return r


if person_email in auth_mgrs:
    print("Authorized manager.")
else:
    print("Not an authorized manager.")
    not_authd_mgr(person_email)
    sys.exit()

try:
    # get file attachment
    get_attach_response = requests.request(
        "GET", attachment, headers=headers, timeout=2
    )
    get_attach_response.raise_for_status()
    print(f"attachment received: ({get_attach_response.status_code})")
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
    # print(df.head())
except OSError as e:
    sys.exit("CSV file not found!")

df1 = alias_format(df)
df2 = x_dups(df1)
no_resp = responses(df2)
mgr_ctl_response = mgr_control()

noncommited = df2[
    (df2["Response"] == "None") & (df2["Attendance"] == "Required Attendee")
]
num_noncommited = len(noncommited)
print(f"\nNoncommited Attendees: {num_noncommited}")
noncommited_string = noncommited[["Full Name"]].to_string(index=False, header=False)

post_noncommited(noncommited_string, num_noncommited, person_email)

NONCOMMITED_LST = noncommited["Alias"].values.tolist()
