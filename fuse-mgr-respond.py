import os
import sys
import json
import configparser
import requests
import pandas as pd

KEY = "CI"
if os.getenv(KEY):
    print("Running as GitHub Action.")
    webex_bearer = os.environ["webex_bearer"]
    room_id = os.environ["room_id"]
    person_id = os.environ["person_id"]
    person_email = os.environ["person_email"]
    action = os.environ["action"]
    auth_mgrs = os.environ["auth_mgrs"]
else:
    print("Running locally.")
    config = configparser.ConfigParser()
    config.read("./secrets/config.ini")
    webex_bearer = config["DEFAULT"]["webex_key"]
    attachment = config["DEFAULT"]["attachment"]
    room_id = config["DEFAULT"]["room_id"]
    person_email = config["DEFAULT"]["person_email"]
    auth_mgrs = config["DEFAULT"]["auth_mgrs"]
    action = "attend_report"


post_msg_url = "https://webexapis.com/v1/messages/"

headers = {
    "Authorization": webex_bearer,
    "Content-Type": "application/json",
}

RAW_FILE_NAME = ""
NONCOMMITED_LST = []


def attend_report(silent_response, confirmed_response, denied_response, email):
    print("Attendance Report")
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


def noncomit_reminders():
    print("Non Committed Reminders")


def pre_reminder():
    print("Pre Event Reminders")


def survey_msg():
    print("Post Event Survey")


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
    # print(f"Not responded: {len(no_respond)}")
    y_respond = dframe[dframe["Response"] == "Accepted"]
    d_respond = dframe[dframe["Response"] == "Declined"]
    return (no_respond, y_respond, d_respond)


if action == "noncomit_reminders":
    noncomit_reminders()
elif action == "pre_reminder":
    pre_reminder()
elif action == "survey_msg":
    survey_msg()
else:
    print("Unknown action.")

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
    print(df.head())
except OSError as e:
    sys.exit("CSV file not found!")

df1 = alias_format(df)
df2 = x_dups(df1)
no_resp, yes_respond, declined_respond = responses(df2)

if action == "attend_report":
    attend_report(no_resp, yes_respond, declined_respond, person_email)
