from botocore.exceptions import ClientError
import pandas as pd
from pytz import timezone
import os
import boto3
import datetime
from tempfile import mkdtemp
from datetime import datetime
import re
import requests
from bs4 import BeautifulSoup


pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)
pd.set_option("display.colheader_justify", "center")
pd.set_option("display.precision", 3)

from db.get_db import FetchDB
from spotify_api import SpotifyAPI
from check import smart_partial_match

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
USER_ID = os.getenv("SPOTIFY_USER_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

db = FetchDB()
pacific_tz = timezone("America/Los_Angeles")
non_latin_pattern = (
    r"[\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF\u0400-\u04FF\u1100-\u11FF\uAC00-\uD7AF]"
)
path = "/tmp/shazam.csv"


class Scrape:
    def __init__(self):
        self.df = []
        self.us = []
        self.l2tk_chart = []
        self.other = []
        self.prospect_list = []
        self.already_checked = []
        self.pub_songs = db.get_pub_songs()
        self.pub_artists = db.get_pub_artists()
        self.roster_artists = db.get_roster_artists()
        self.major_labels = db.get_major_labels()
        self.signed_artists = db.get_signed_artists()
        self.prospects = db.get_prospects()
        self.client = SpotifyAPI(CLIENT_ID, USER_ID, CLIENT_SECRET)

    def download(self, name, url):
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Failed to access {url}. Status code: {response.status_code}")
            return
        soup = BeautifulSoup(response.content, "html.parser")

        button = soup.find("a", class_="Header_responsiveView__srGi_")
        if not button:
            print("Download button not found.")
            return

        button_url = button.get("href")
        print(f"Download URL: https://www.shazam.com{button_url}")

        csv_response = requests.get(f"https://www.shazam.com{button_url}")
        if csv_response.status_code == 200:
            with open(path, "wb") as f:
                f.write(csv_response.content)
            print(f"CSV file saved to {path}")
        else:
            print(f"Failed to download CSV. Status code: {csv_response.status_code}")
            return

        data = pd.read_csv(path, skiprows=2, on_bad_lines="skip")
        self.process_data(name, data)
        os.remove(path)

    def check_and_append_artist(self, name, idx, artist, track):
        if re.search(non_latin_pattern, artist) or re.search(non_latin_pattern, track):
            return None

        variations = [
            artist.split(", ", 1)[0],
            artist.split(" featuring ")[0],
            artist.split(" x ")[0],
        ]

        if " & " in artist:
            part1, part2 = artist.split(" & ", 1)
            variations.extend([part1, part2])

        matched_variation = any(
            a.lower() in map(str.lower, self.signed_artists + self.roster_artists)
            for a in variations
        )

        if matched_variation:
            return None
        elif " & " in artist and ", " not in artist:
            self.df.append((name, idx, artist, track, None, None, None))
        else:
            self.df.append((name, idx, variations[0], track, None, None, None))

    def process_data(self, name, data):
        for i, row in data.iterrows():
            s = row["Title"]
            a = row["Artist"]
            idx = row["Rank"]

            self.check_and_append_artist(name, idx, a, s)

    def chart_search(self, shazam_charts):

        for (
            chart,
            position,
            artist,
            song,
            movement,
            link,
            label,
            unsigned,
        ) in shazam_charts.iloc[:].itertuples(index=False):

            if artist in self.already_checked:
                print("already_checked", artist)
                continue

            if movement != "New" and unsigned != "UNSIGNED":
                self.us.append(
                    (
                        chart,
                        position,
                        artist,
                        song,
                        None,
                        None,
                        link,
                        label,
                        None,
                    )
                )
                continue

            if unsigned == "UNSIGNED" and movement != "New":
                self.us.append(
                    (
                        chart,
                        position,
                        artist,
                        song,
                        "UNSIGNED",
                        None,
                        link,
                        label,
                        movement,
                    )
                )

                continue

            if movement == "New":
                copyright = self.client.get_artist_copy_track(
                    artist.lower(), song, "shazam"
                )

                if not copyright and " & " in artist:
                    artist = artist.split(" & ")[0]
                    copyright = self.client.get_artist_copy_track(
                        artist.lower(), song, "shazam"
                    )

                if copyright:
                    year_pattern = r"202[0-4]"
                    if not re.search(year_pattern, copyright[0]):
                        continue

                    matched_labels = [
                        label
                        for label in self.major_labels
                        if smart_partial_match(label, copyright[0].lower())
                    ]

                    if not matched_labels:
                        self.us.append(
                            (
                                chart,
                                position,
                                artist,
                                song,
                                "UNSIGNED",
                                None,
                                copyright[1],
                                copyright[0],
                                movement,
                            )
                        )
                    else:
                        self.already_checked.append(artist)
                        self.us.append(
                            (
                                chart,
                                position,
                                artist,
                                song,
                                None,
                                None,
                                None,
                                copyright[1],
                                copyright[0],
                            )
                        )

    def create_html(self, chart_name, data):
        conor = os.getenv("CONOR")
        lucas = os.getenv("LUCAS")
        ari = os.getenv("ARI")
        laura = os.getenv("LAURA")
        micah = os.getenv("MICAH")

        html_body = f"""
        <html>
        <head>
        <style>
            body {{ font-family: Arial, sans-serif; font-size: 12px; color: black; }}
            h2 {{ font-size: 14px; font-weight: bold; }}
            a {{ color: black; text-decoration: none; }} /* Unvisited link */
            a:visited {{ color: black; text-decoration: none; }} /* Visited link */
            a:hover {{ text-decoration: underline; }} /* Hover effect */
            .indent {{ padding-left: 20px; }} 
        </style>
        </head>
        <body>
        <p>
            {chart_name} - {datetime.now(pacific_tz).strftime("%m/%d/%y")}
            <br> {conor}, {ari}, {laura}, {micah}, {lucas}
        </p>
        """

        chart_header = None

        def add_content_and_header(chart):
            nonlocal html_body
            if self.l2tk_chart or self.other or self.prospect_list:
                header_text = f"<br><br><strong style='text-decoration: underline;'>{chart.upper()}</strong><br><br>"
                html_body += header_text

                if self.prospect_list:
                    html_body += "<br><p>PROSPECT:</p>"
                    for p in self.prospect_list:
                        html_body += (
                            f"<p><span style='background-color: red;'>{p}</span></p>"
                        )

                if self.other:
                    html_body += "<br><p>NEW ADDS:</p>"
                    for p in self.other:
                        html_body += f"<p>{p['c']}</p>"

            self.l2tk_chart = []
            self.prospect_list = []
            self.other = []

        for (
            chart,
            position,
            artist,
            song,
            unsigned,
            l2tk,
            link,
            label,
            movement,
        ) in data.itertuples(index=False):

            if chart != chart_header:
                if chart_header:
                    add_content_and_header(chart_header)
                chart_header = chart

            if unsigned == "UNSIGNED":
                if movement.startswith("-"):
                    color = "red"
                elif movement == "New":
                    color = "yellow"
                elif movement == "0":
                    color = "black"
                else:
                    color = "green"

                self.other.append(
                    {
                        "c": f"""
                        {position}. {artist} - {song} <span style='color:{color};'>({movement})</span><br>
                        <span class='indent'>• Label: {label} (UNSIGNED)</span><br>
                        <span class='indent'>• <a href='{link}'>{link}</a></span>
                        """,
                        "h": True,
                    }
                )

        add_content_and_header(chart_header)

        html_body += "</body></html>"

        return html_body


def send_email_ses(subject, body) -> None:
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


def download_shazam(scrape):
    today = datetime.now(pacific_tz)
    scrape.download(
        "Shazam Global Top 200 Genres / Hip-Hop",
        "https://www.shazam.com/charts/genre/world/hip-hop-rap",
    )

    scrape.download(
        "Shazam Global Top 200 Genres / Pop",
        "https://www.shazam.com/charts/genre/world/pop",
    )

    scrape.download(
        "Shazam Global Top 100 Genres / ALT",
        "https://www.shazam.com/charts/genre/world/alternative",
    )

    scrape.download(
        "Shazam Global Top 100 Genres / R&B",
        "https://www.shazam.com/charts/genre/world/randb-soul",
    )

    scrape.download(
        "Shazam Global Top 100 Genres / Singer Songwriter",
        "https://www.shazam.com/charts/genre/world/singer-songwriter",
    )

    scrape.download(
        "Shazam Global Top 100 Genres / Country",
        "https://www.shazam.com/charts/genre/world/country",
    )

    scrape.download(
        "Shazam Top 200 / Global", "https://www.shazam.com/charts/top-200/world"
    )

    scrape.download(
        "Shazam Top 200 / US",
        "https://www.shazam.com/charts/top-200/united-states",
    )

    scrape.download(
        "Shazam Top 200 / UK", "https://www.shazam.com/charts/top-200/united-kingdom"
    )

    scrape.download(
        "Shazam Top 200 / CA", "https://www.shazam.com/charts/top-200/canada"
    )
    scrape.download(
        "Shazam US Top 100 Genres / Hip-Hop",
        "https://www.shazam.com/charts/genre/united-states/hip-hop-rap",
    )

    scrape.download(
        "Shazam US Top 100 Genres / Pop",
        "https://www.shazam.com/charts/genre/united-states/pop",
    )

    scrape.download(
        "Shazam US Top 100 Genres / Dance",
        "https://www.shazam.com/charts/genre/united-states/dance",
    )

    scrape.download(
        "Shazam US Top 100 Genres / Country",
        "https://www.shazam.com/charts/genre/united-states/country",
    )


def scrape_all():
    scrape = Scrape()
    download_shazam(scrape)

    shazam_charts = pd.DataFrame(
        scrape.df,
        columns=["Chart", "Position", "Artist", "Song", "Movement", "Link", "Label"],
    )
    data_yesterday = db.get_shazam_charts()

    for i, r in shazam_charts.iterrows():
        pos = r["Position"]
        chart = r["Chart"]
        match = data_yesterday.loc[
            (data_yesterday["song"].str.lower() == r["Song"].lower())
            & (data_yesterday["chart"].str.lower() == chart.lower())
        ]

        if not match.empty:
            shazam_charts.at[i, "Label"] = match["label"].iloc[0]
            shazam_charts.at[i, "Link"] = match["link"].iloc[0]
            shazam_charts.at[i, "Unsigned"] = match["unsigned"].iloc[0]
            pos_y = int(match["position"].iloc[0])

            if pos_y == pos:
                shazam_charts.at[i, "Movement"] = "0"
            else:
                movement_value = pos_y - pos
                shazam_charts.at[i, "Movement"] = str(movement_value)
        else:
            shazam_charts.at[i, "Movement"] = "New"

    shazam_charts["Movement"] = shazam_charts["Movement"].astype(str)

    scrape.chart_search(shazam_charts)
    unsigned_charts = pd.DataFrame(
        scrape.us,
        columns=[
            "Chart",
            "Position",
            "Artist",
            "Song",
            "Unsigned",
            "L2TK",
            "Link",
            "Label",
            "Movement",
        ],
    )

    db.insert_shazam_charts(unsigned_charts)
    body = scrape.create_html("Shazam Chart Report", unsigned_charts)

    subject = f'Shazam Chart Report - {datetime.now(pacific_tz).strftime("%m/%d/%y")}'
    send_email_ses(subject, body)


def lambda_handler(event, context):
    scrape_all()
    return {
        "statusCode": 200,
        "body": "Scrape complete",
    }


# lambda_handler(None, None)
