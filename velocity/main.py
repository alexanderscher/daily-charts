from datetime import datetime, timedelta
from botocore.exceptions import ClientError
import pandas as pd
import os
import boto3
import datetime
import re

pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)
pd.set_option("display.colheader_justify", "center")
pd.set_option("display.precision", 3)

from db.get_db import FetchDB
from spotify_api import SpotifyAPI

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
USER_ID = os.getenv("SPOTIFY_USER_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

db = FetchDB()

roster_artists = db.get_roster_artists()
pub_songs = db.get_pub_songs()
pub_artists = db.get_pub_artists()
majorlabels = db.get_major_labels()
signed_artists = db.get_signed_artists()
df = []
other = []


def smart_partial_match(label, text):
    normalized_text = text.lower()
    normalized_label = label.lower()
    pattern = r"(?:^|\s|,)" + re.escape(normalized_label) + r"(?:\s*[/,]\s*|\s|$)"
    return re.search(pattern, normalized_text) is not None


def velocity():
    client = SpotifyAPI(CLIENT_ID, USER_ID, CLIENT_SECRET)
    artist_list = client.get_playlist_songs("4iPVyRQvyAricdP1jPAjlQ")
    data = pd.DataFrame(artist_list, columns=["artist", "track", "added at"])

    for i, d in data.iterrows():
        artist = d["artist"]
        song = d["track"]
        date = d["added at"]
        dt_format = "%Y-%m-%dT%H:%M:%SZ"
        added_at = datetime.strptime(date, dt_format)
        time_frame = datetime.now() - timedelta(days=1)

        if added_at >= time_frame:
            if not list(
                filter(lambda x: (x.lower() == artist.lower()), signed_artists)
            ):
                copyright = client.get_artist_copy_track(
                    artist.lower(), song.lower(), "daily_chart"
                )
                if copyright:
                    matched_labels = list(
                        filter(
                            lambda x: smart_partial_match(x, copyright[0].lower()),
                            majorlabels,
                        )
                    )
                    if not matched_labels:
                        print(artist, added_at, copyright)
                        df.append(
                            ("Velocity", artist, song, copyright[1], copyright[0])
                        )


def create_html(self):
    conor = os.getenv("CONOR")
    ari = os.getenv("ARI")
    laura = os.getenv("LAURA")
    micah = os.getenv("MICAH")

    final_df = pd.DataFrame(df, columns=["chart", "artist", "song", "link", "label"])

    html_body = f"""
        <html>
        <head>
        <style>
            body {{ font-family: Arial, sans-serif; font-size: 12px; }}
            h2 {{ font-size: 14px; font-weight: bold; }}
            .prospect {{ color: red; }}
            .other {{ color: yellow; }}
        </style>
        </head>
        <body>
        <p>
            Veloctiy Report - {datetime.datetime.now().strftime("%m/%d/%y")}
            <br> {conor}, {ari}, {laura}, {micah}
        </p>
        """

    html_body += f"<strong>{chart.upper()}</strong>"
    html_body += "<br><p>NEW ADDS:</p>"

    for chart, artist, song, link, label in final_df.itertuples(index=False):

        for p in self.other:
            html_body += f"<p><mark>{p['c']}</mark></p>"

    html_body += "</body></html>"

    return html_body


def send_email(subject, body) -> None:
    ses_client = boto3.client(
        "ses",
        region_name="us-east-1",
    )
    sender = os.getenv("ALEX")

    try:
        response = ses_client.send_email(
            Destination={
                "ToAddresses": [os.getenv("ALEX_MAIL")],
            },
            Message={
                "Body": {
                    "Html": {
                        "Charset": "UTF-8",
                        "Data": body,
                    },
                },
                "Subject": {
                    "Charset": "UTF-8",
                    "Data": subject,
                },
            },
            Source=sender,
        )
    except ClientError as e:
        print(f"Error sending email: {e.response['Error']['Message']}")
    else:
        print(f"Email sent! Message ID: {response['MessageId']}")


def scrape_all():
    velocity()
    body = create_html()
    subject = f'Velocity  Report - {datetime.datetime.now().strftime("%m/%d/%y")}'
    send_email(subject, body)


def lambda_handler(event, context):
    scrape_all()
    return {
        "statusCode": 200,
        "body": "Scrape complete",
    }


lambda_handler(None, None)
