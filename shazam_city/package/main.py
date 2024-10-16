import time
from botocore.exceptions import ClientError
import pandas as pd
from pytz import timezone
import os
import boto3
import datetime
from datetime import datetime
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)
pd.set_option("display.colheader_justify", "center")
pd.set_option("display.precision", 3)

from db.get_db import FetchDB
from spotify_api import SpotifyAPI
from check import smart_partial_match


db = FetchDB()
pacific_tz = timezone("America/Los_Angeles")
non_latin_pattern = (
    r"[\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF\u0400-\u04FF\u1100-\u11FF\uAC00-\uD7AF]"
)
path = "/tmp/shazam-city.csv"

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID_GOOGLE")
USER_ID = os.getenv("SPOTIFY_USER_ID_GOOGLE")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET_GOOGLE")


class Scrape:
    def __init__(self):
        self.df = []
        self.us = []
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
        self.repeat = []

    def shazam_city(self, url, country):
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Failed to access {url}. Status code: {response.status_code}")
            return

        soup = BeautifulSoup(response.content, "html.parser")

        city_elements = soup.find_all(
            "option", value=lambda v: v and v.startswith("/charts/top-50/")
        )
        city_links = [option["value"] for option in city_elements]

        for city in city_links:
            city_url = urljoin("https://www.shazam.com", city)
            city_name = city_url.split("/")[-1]
            city_response = requests.get(city_url)
            if city_response.status_code != 200:
                print(
                    f"Failed to access {city_url}. Status code: {city_response.status_code}"
                )
                continue

            city_soup = BeautifulSoup(city_response.content, "html.parser")

            button = city_soup.find("a", class_="Header_responsiveView__srGi_")
            if not button:
                print(f"No download button found for {city_url}")
                continue

            button_url = urljoin("https://www.shazam.com", button.get("href"))

            self.download_csv(button_url, city_name, country)

    def download_csv(self, button_url, city, country):
        response = requests.get(button_url)
        if response.status_code == 200:
            with open(path, "wb") as f:
                f.write(response.content)
            print(f"CSV saved to {path}")

            data = pd.read_csv(path, skiprows=2, on_bad_lines="skip")
            for _, row in data.iterrows():
                self.process_shazam_row(row, city, country)

            os.remove(path)
        else:
            print(f"Failed to download CSV. Status: {response.status_code}")

    def process_shazam_row(self, row, city, country):
        s = row["Title"]
        a = row["Artist"]
        idx = row["Rank"]
        if a in self.repeat:
            return
        self.repeat.append(a)
        self.check_and_append_artist(city, idx, a, s, country)

    def check_and_append_artist(self, city, idx, artist, track, country):
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
            self.df.append(
                (f"Shazam Cities {country} Top 50 {city}", idx, artist, track)
            )
        else:
            self.df.append(
                (f"Shazam Cities {country} Top 50 {city}", idx, variations[0], track)
            )

    def city_search(self, shazam_cities):

        for chart, position, artist, song, movement in shazam_cities.itertuples(
            index=False
        ):

            if artist in self.already_checked:
                continue

            elif movement != "New":
                self.us.append(
                    (
                        chart,
                        position,
                        artist,
                        song,
                        None,
                        None,
                        None,
                        None,
                        None,
                    )
                )
            elif movement == "New":

                if list(
                    filter(
                        lambda x: (x.lower() == artist.lower()),
                        self.signed_artists + self.roster_artists,
                    )
                ):

                    continue

                else:
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
                        matched_labels = list(
                            filter(
                                lambda x: smart_partial_match(x, copyright[0].lower()),
                                self.major_labels,
                            )
                        )
                        if not matched_labels:
                            print(artist, "unsigned")

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
            self.already_checked.append(artist)

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
            if self.other or self.prospect_list:
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


def scrape_all():

    scrape = Scrape()

    scrape.shazam_city(
        "https://www.shazam.com/charts/top-50/united-states/los-angeles", "US"
    )
    scrape.shazam_city("https://www.shazam.com/charts/top-50/canada/calgary", "CA")
    scrape.shazam_city(
        "https://www.shazam.com/charts/top-50/united-kingdom/belfast", "UK"
    )
    scrape.shazam_city("https://www.shazam.com/charts/top-50/australia/adelaide", "AU")

    shazam_cities = pd.DataFrame(
        scrape.df, columns=["Chart", "Position", "Artist", "Song"]
    )

    data_yesterday = db.get_shazam_city_charts()

    for i, r in shazam_cities.iterrows():
        pos = r["Position"]
        match = data_yesterday.loc[
            (data_yesterday["song"].str.lower() == r["Song"].lower())
        ]

        if not match.empty:

            pos_y = int(match["position"].iloc[0])

            if pos_y == pos:
                shazam_cities.at[i, "Movement"] = "0"
            else:
                movement_value = pos_y - pos
                shazam_cities.at[i, "Movement"] = str(movement_value)
        else:
            shazam_cities.at[i, "Movement"] = "New"

    shazam_cities["Movement"] = shazam_cities["Movement"].astype(str)

    scrape.city_search(shazam_cities)
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

    db.insert_shazam_city_charts(unsigned_charts)
    body = scrape.create_html("Shazam Cities Report", unsigned_charts)

    subject = (
        f'{'Shazam Cities Report'}- {datetime.now(pacific_tz).strftime("%m/%d/%y")}'
    )
    send_email_ses(subject, body)


def lambda_handler(event, context):
    scrape_all()
    return {
        "statusCode": 200,
        "body": "Scrape complete",
    }


# lambda_handler(None, None)
