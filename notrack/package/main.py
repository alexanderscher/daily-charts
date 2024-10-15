import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

private_key = os.getenv("GOOGLE_PRIVATE_KEY")
client_email = os.getenv("GOOGLE_CLIENT_EMAIL")
project_id = os.getenv("GOOGLE_PROJECT_ID")

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

creds_dict = {
    "type": "service_account",
    "project_id": project_id,
    "private_key_id": "",
    "private_key": private_key,
    "client_email": client_email,
    "client_id": "",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{client_email}",
}

creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

spreadsheet = client.open("No Track List")

from db.get_db import FetchDB

db = FetchDB()

signed = db.get_signed_artists()
majorlabel = db.get_major_labels()
spreadsheet = client.open(f"No Track List")
wks = spreadsheet.worksheet("Sheet1")
column_a_cells = wks.range("A2:A" + str(wks.row_count))
column_b_cells = wks.range("B2:B" + str(wks.row_count))
non_empty_a_cells = [cell for cell in column_a_cells if cell.value != ""]
non_empty_b_cells = [cell for cell in column_b_cells if cell.value != ""]
print(non_empty_a_cells)
print(non_empty_b_cells)

new_signed = []
new_label = []


def update_cells():
    if len(non_empty_a_cells):
        for c in column_a_cells:
            artist = c.value.strip().lower()
            if artist != "":
                if artist not in new_signed:
                    if not list(
                        filter(lambda x: (x.lower() == artist.lower()), signed)
                    ):
                        new_signed.append(artist)
        db.insert_signed_artist(new_signed)

        for cell in column_a_cells:
            cell.value = ""

        wks.update_cells(column_a_cells)

    if len(non_empty_b_cells):
        for c in column_b_cells:
            label = c.value.strip().lower()
            if label != "":
                if label not in new_label:
                    if not list(
                        filter(lambda x: (x.lower() == label.lower()), majorlabel)
                    ):
                        new_label.append(label)
        db.insert_major_label(new_label)

        for cell in column_b_cells:
            cell.value = ""

        wks.update_cells(column_b_cells)


def lambda_handler(event, context):
    update_cells()
    return {
        "statusCode": 200,
        "body": "Scrape complete",
    }


lambda_handler(None, None)
