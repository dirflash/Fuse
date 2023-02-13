import os
import sys

KEY = "CI"
if os.getenv(KEY):
    print("Running as GitHub Action.")
    webex_bearer = os.environ["webex_bearer"]
    room_id = os.environ["room_id"]
    person_id = os.environ["person_id"]
    action = os.environ["action"]
    auth_mgrs = os.environ["auth_mgrs"]
else:
    sys.exit()

print(person_id)


def attend_report():
    print("Attendance Report")


def noncomit_reminders():
    print("Non Committed Reminders")


def pre_reminder():
    print("Pre Event Reminders")


def survey_msg():
    print("Post Event Survey")


if action == "attend_report":
    attend_report()
elif action == "noncomit_reminders":
    noncomit_reminders()
elif action == "pre_reminder":
    pre_reminder()
elif action == "survey_msg":
    survey_msg()
else:
    print("Unknown action.")

if person_id in auth_mgrs:
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
