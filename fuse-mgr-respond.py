import os
import sys

KEY = "CI"
if os.getenv(KEY):
    print("Running as GitHub Action.")
    webex_bearer = os.environ["webex_bearer"]
    room_id = os.environ["room_id"]
    person_id = os.environ["person_id"]
    action = os.environ["action"]
else:
    sys.exit()


def attend_report():
    print("Attendance Report")


def noncomit_reminders():
    print("Non Committed Reminders")


def pre_reminder():
    print("Pre Event Reminders")


def survey_msg():
    print("Post Event Survey")


if action == "attend_port":
    attend_report()
elif action == "noncomit_reminders":
    noncomit_reminders()
elif action == "pre_reminder":
    pre_reminder()
elif action == "survey_msg":
    survey_msg()
else:
    print("Unknown action.")


# Action_Choice: attend_port, noncomit_reminders, pre_reminder, survey_msg
