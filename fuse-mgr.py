# fuse bot - under construction

import os
import sys
import pandas as pd

attend_csv = "./230210 - FUSE.csv"


KEY = "CI"
if os.getenv(KEY):
    webex_bearer = os.environ["WEBEX_BEARER"]
    attachment = os.environ["attachment"]
    room_id = os.environ["room_id"]
    room_type = os.environ["room_type"]
    person_id = os.environ["person_id"]
    person_email = os.environ["person_email"]

noncommit_tst = []

print(webex_bearer)
print(attachment)
print(room_id)
print(room_type)
print(person_id)
print(person_email)


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


def organizer(dframe):
    host = dframe[dframe["Attendance"] == "Meeting Organizer"]
    attnd = dframe[dframe["Attendance"] == "Required Attendee"]
    optional = dframe[dframe["Attendance"] == "Optional Attendee"]
    return (host, attnd, optional)


def responses(dframe):
    no_respond = dframe[dframe["Response"] == "None"]
    print(f"Not responded: {len(no_respond)}")
    return no_respond


"""
# check_mgr.mgr()

try:
    df = pd.read_csv(attend_csv, header=0)
    print(f"Found file: {os.path.basename(attend_csv)}")
except OSError as e:
    sys.exit("CSV file not found!")

df1 = alias_format(df)
df2 = x_dups(df1)
# dfo, dfx, opt = organizer(df2)
no_resp = responses(df2)
"""

"""
print(no_resp[["Full Name", "Alias", "Attendance", "Response"]].head())

host = df2[df2["Attendance"] == "Meeting Organizer"]
print(f"Meeting Organizer ({len(host)}):")
# print(host[["Full Name", "Alias", "Attendance", "Response"]].head())

attnd = df2[df2["Attendance"] == "Required Attendee"]
print(f"Required Attendees ({len(attnd)}):")
# print(attnd[["Full Name", "Alias", "Attendance", "Response"]].head())

optional = df2[df2["Attendance"] == "Optional Attendee"]
print(f"Optional Attendees ({len(optional)}):")
# print(optional[["Full Name", "Alias", "Attendance", "Response"]].head())

accepted = df2[df2["Response"] == "Accepted"]
print(f"Accepted Attendees ({len(accepted)}):")
# print(accepted[["Full Name", "Alias", "Attendance", "Response"]].head())

declined = df2[df2["Response"] == "Declined"]
print(f"Declined Attendees ({len(declined)}):")
# print(declined[["Full Name", "Alias", "Attendance", "Response"]].head())
"""

"""
noncommited = df2[
    (df2["Response"] == "None") & (df2["Attendance"] == "Required Attendee")
]
# print(f"\nNoncommited Attendees ({len(noncommited)}):")
# print(noncommited[["Full Name", "Alias", "Attendance", "Response"]].head())

noncommit_lst = noncommited["Alias"].values.tolist()
print(noncommit_lst)

noncommit_tst.append("aarodavi")

msg.msg(noncommit_tst)
"""
