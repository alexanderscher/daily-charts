import time
from botocore.exceptions import ClientError
import pandas as pd
import os
import boto3
import datetime
import requests

pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)
pd.set_option("display.colheader_justify", "center")
pd.set_option("display.precision", 3)

from db.get_db import FetchDB
from spotify_api import SpotifyAPI
from check import smart_partial_match
from lyricsgenius import Genius
import re


CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID_L2TK")
USER_ID = os.getenv("SPOTIFY_USER_ID_L2TK")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET_L2TK")
TOKEN = os.getenv("GENIUS_ACCESS_TOKEN")
db = FetchDB()
non_latin_pattern = (
    r"[\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF\u0400-\u04FF\u1100-\u11FF\uAC00-\uD7AF]"
)


class Scrape:
    def __init__(self):
        self.db = FetchDB()
        self.genius_client = Genius(TOKEN)
        self.pub_songs = self.db.get_pub_songs()
        self.pub_artists = self.db.get_pub_artists()
        self.roster_artists = self.db.get_roster_artists()
        self.major_labels = self.db.get_major_labels()
        self.signed_artists = self.db.get_signed_artists()
        self.prospects = self.db.get_prospects()
        self.client = SpotifyAPI(CLIENT_ID, USER_ID, CLIENT_SECRET)
        self.already_checked = []
        self.df = []
        self.us = []
        self.other = []
        self.prospect_list = []

    def check_and_append_artist(self, name, index, artist_name, track, views):
        if artist_name in [
            "Genius Romanizations",
            "Genius English Translations",
            "Traditional Transcriptions",
        ]:
            return None
        elif re.search(non_latin_pattern, artist_name):
            return None
        elif re.search(non_latin_pattern, track):
            return None

        variations = [
            artist_name.split(" (", 1)[0],
            artist_name.split(", ", 1)[0],
            artist_name.split(" & ", 1)[0],
        ]

        if " & " in artist_name:
            part1, part2 = artist_name.split(" & ", 1)
            variations.extend([part1, part2])

        matched_variation = next(
            (
                variation
                for variation in variations
                if variation.lower()
                in map(str.lower, self.signed_artists + self.roster_artists)
            ),
            None,
        )

        if matched_variation:
            return None
        elif " & " in artist_name:
            self.df.append((name, index, artist_name, track, views))
        else:
            self.df.append((name, index, variations[0], track, views))

    def genius(self, name, genre):
        time.sleep(5)
        page = 1
        index = 1

        while True:
            try:
                response = self.genius_client.charts(
                    time_period="day",
                    chart_genre=genre,
                    per_page=50,
                    page=page,
                    text_format=None,
                    type_="songs",
                )

                chart_items = response.get("chart_items", [])

                if not chart_items:
                    print(f"No more items found on page {page}. Stopping.")
                    break

                for c in chart_items:
                    item = c.get("item", {})
                    artist_name = item.get("artist_names", "Unknown Artist")
                    track = item.get("title", "Unknown Title")
                    views = item.get("stats", {}).get("pageviews", 0)
                    self.check_and_append_artist(name, index, artist_name, track, views)

                    index += 1

                page += 1

            except (requests.exceptions.Timeout, TimeoutError) as e:
                print(f"Timeout error on page {page}. Retrying in 10 seconds...")
                time.sleep(10)
                continue

            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                break

    def _process_artist(self, artist, song):
        if artist in [
            "Genius Romanizations",
            "Genius English Translations",
        ]:
            return None
        else:
            split_tokens = [
                ", ",
                " (@",
                "(@",
                " featuring ",
                " Featuring ",
                " feat. ",
                " / ",
                " X ",
            ]
            for token in split_tokens:
                if token in artist:
                    artist = artist.split(token)[0]
                    break
            return artist

    def running(
        self,
        chart,
        position,
        artist,
        song,
        streams,
        movement,
        label,
        link,
        unsigned,
    ):
        processed_artist = self._process_artist(artist, song)

        if processed_artist == None:
            pass

        elif processed_artist in self.already_checked:
            print("already_checked", artist)

        elif movement != "New" and unsigned != "UNSIGNED":
            self.us.append(
                (
                    chart,
                    position,
                    processed_artist,
                    song,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                )
            )

        elif unsigned == "UNSIGNED":
            self.us.append(
                (
                    chart,
                    position,
                    processed_artist,
                    song,
                    "UNSIGNED",
                    None,
                    streams,
                    movement,
                    link,
                    label,
                )
            )

        elif movement == "New":

            copyright = self.client.get_artist_copy_track(
                processed_artist.lower(), song, "daily_chart"
            )
            if not copyright and " & " in artist:
                artist = artist.split(" & ")[0]
                processed_artist = self._process_artist(artist, song)
                copyright = self.client.get_artist_copy_track(
                    processed_artist.lower(), song, "daily_chart"
                )

            elif copyright:
                matched_labels = list(
                    filter(
                        lambda x: smart_partial_match(x, copyright[0].lower()),
                        self.major_labels,
                    )
                )

                if not matched_labels:
                    print(
                        f"{position}...",
                        processed_artist,
                        "-",
                        song,
                        "\n",
                        " • Label:",
                        copyright[0],
                        "(UNSIGNED)\n",
                        " • Link:",
                        copyright[1],
                    )
                    self.us.append(
                        (
                            chart,
                            position,
                            processed_artist,
                            song,
                            "UNSIGNED",
                            None,
                            streams,
                            movement,
                            copyright[1],
                            copyright[0],
                        )
                    )

                else:
                    self.already_checked.append(processed_artist)
                    self.us.append(
                        (
                            chart,
                            position,
                            processed_artist,
                            song,
                            None,
                            None,
                            None,
                            None,
                            copyright[1],
                            copyright[0],
                        )
                    )

    def chart_search(self):
        genius_data = pd.DataFrame(
            self.df, columns=["Chart", "Position", "Artist", "Song", "Views"]
        )
        data_yesterday = db.get_genius_charts()
        for i, r in genius_data.iterrows():
            pos = int(r["Position"])
            chart = r["Chart"]
            match = data_yesterday.loc[
                (data_yesterday["song"].str.lower() == r["Song"].lower())
                & (data_yesterday["chart"].str.lower() == chart.lower())
            ]

            if not match.empty:
                genius_data.at[i, "Label"] = match["label"].iloc[0]
                genius_data.at[i, "Link"] = match["link"].iloc[0]
                genius_data.at[i, "Unsigned"] = match["unsigned"].iloc[0]
                pos_y = int(match["position"].iloc[0])

                if pos_y == pos:
                    genius_data.at[i, "Movement"] = "0"
                else:
                    movement_value = pos_y - pos
                    genius_data.at[i, "Movement"] = str(movement_value)
            else:
                genius_data.at[i, "Movement"] = "New"

        for (
            chart,
            position,
            artist,
            song,
            streams,
            movement,
            label,
            link,
            unsigned,
        ) in genius_data.iloc[:].itertuples(index=False):

            self.running(
                chart,
                position,
                artist,
                song,
                streams,
                movement,
                label,
                link,
                unsigned,
            )

    def create_html(self, chart_name, data):
        conor = os.getenv("CONOR")
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
            {chart_name} - {datetime.datetime.now().strftime("%m/%d/%y")}
            <br> {conor}, {ari}, {laura}, {micah}
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
            views,
            movement,
            link,
            label,
        ) in data.itertuples(index=False):

            if chart != chart_header:
                if chart_header:
                    add_content_and_header(chart_header)

                chart_header = chart

            if unsigned == "UNSIGNED":
                if movement.startswith("-"):
                    color = "red"
                elif movement == "NEW":
                    color = "yellow"
                elif movement == "0":
                    color = "black"
                else:
                    color = "green"

                self.other.append(
                    {
                        "c": f"""
                        {position}. {artist} - {song} <span style='color:{color};'>({movement})</span><br>
                        <span class='indent'>• Views: {views}</span><br>
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
    scrape.genius("Genius Chart - Daily Trending Top 100: ALL GENRES", "all")
    scrape.genius("Genius Chart - Daily Trending Top 100: RAP", "rap")
    scrape.genius("Genius Chart - Daily Trending Top 100: POP", "pop")
    scrape.genius("Genius Chart - Daily Trending Top 100: R&B", "rb")
    scrape.genius("Genius Chart - Daily Trending Top 100: Rock", "rock")
    scrape.genius("Genius Chart - Daily Trending Top 100: Country", "country")
    scrape.chart_search()
    final_df = pd.DataFrame(
        scrape.us,
        columns=[
            "Chart",
            "Position",
            "Artist",
            "Song",
            "Unsigned",
            "L2TK",
            "Views",
            "Movement",
            "Link",
            "Label",
        ],
    )
    print(final_df)

    db.insert_genius_charts(final_df)
    body = scrape.create_html("Genius Chart Report", final_df)
    subject = f'Genius Chart Report - {datetime.datetime.now().strftime("%m/%d/%y")}'
    send_email_ses(subject, body)


def lambda_handler(event, context):
    scrape_all()
    return {
        "statusCode": 200,
        "body": "Scrape complete",
    }


lambda_handler(None, None)
