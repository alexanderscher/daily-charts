from datetime import datetime, timedelta
import jwt
import requests
from requests.exceptions import HTTPError
import time
import os
from pytz import timezone
import boto3
from botocore.exceptions import ClientError
import pandas as pd
import numpy as np
import re

pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)
pd.set_option("display.colheader_justify", "center")
pd.set_option("display.precision", 3)

from db.get_db import FetchDB
from spotify_api import SpotifyAPI
from check import check_prod
from check import smart_partial_match
from check import check_prod_albums


db = FetchDB()

pacific_tz = timezone("America/Los_Angeles")

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID_FREDDY")
USER_ID = os.getenv("SPOTIFY_USER_ID_FREDDY")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET_FREDDY")

APPLE_TEAM_ID = os.getenv("APPLE_TEAM_ID")
APPLE_KEY_ID = os.getenv("APPLE_KEY_ID")
APPLE_PRIVATE_KEY = os.getenv("APPLE_PRIVATE_KEY")

if not APPLE_TEAM_ID or not APPLE_KEY_ID or not APPLE_PRIVATE_KEY:
    raise ValueError("Missing required environment variables for Apple Music API")

APPLE_PRIVATE_KEY = (
    f"-----BEGIN PRIVATE KEY-----\n{APPLE_PRIVATE_KEY}\n-----END PRIVATE KEY-----"
)


class AppleMusicAPI:
    def __init__(
        self,
        secret_key,
        key_id,
        team_id,
        proxies=None,
        requests_session=True,
        max_retries=10,
        requests_timeout=None,
        session_length=12,
    ):
        self.proxies = proxies
        self._secret_key = secret_key
        self._key_id = key_id
        self._team_id = team_id
        self._alg = "ES256"
        self.token_str = ""
        self.session_length = session_length
        self.token_valid_until = None
        self.generate_token(session_length)
        self.root = "https://api.music.apple.com/v1/"
        self.max_retries = max_retries
        self.requests_timeout = requests_timeout
        if requests_session:
            self._session = requests.Session()
        else:
            self._session = requests.api
        self.playlist_ids = None
        self.apple_df = []
        self.roster_artists = db.get_roster_artists()
        self.majorlabels = db.get_major_labels()
        self.signed_artists = db.get_signed_artists()
        self.pub_songs = db.get_pub_songs()
        self.pub_artists = db.get_pub_artists()
        self.pub_albums = db.get_pub_albums()
        self.spotify_client = SpotifyAPI(CLIENT_ID, USER_ID, CLIENT_SECRET)
        self.us = []
        self.already_checked = []
        self.offset = 0

    def token_is_valid(self):
        return (
            datetime.now() <= self.token_valid_until
            if self.token_valid_until is not None
            else False
        )

    def generate_token(self, session_length):
        token_exp_time = datetime.now() + timedelta(hours=session_length)
        headers = {"alg": self._alg, "kid": self._key_id}
        payload = {
            "iss": self._team_id,
            "iat": int(datetime.now().timestamp()),
            "exp": int(token_exp_time.timestamp()),
        }
        self.token_valid_until = token_exp_time
        token = jwt.encode(
            payload, self._secret_key, algorithm=self._alg, headers=headers
        )
        self.token_str = token if type(token) is not bytes else token.decode()

    def _auth_headers(self):

        if self.token_str:
            return {"Authorization": "Bearer {}".format(self.token_str)}
        else:
            return {}

    def _call(self, method, url, params):

        if not url.startswith("http"):
            url = self.root + url

        if not self.token_is_valid():
            self.generate_token(self.session_length)

        headers = self._auth_headers()
        headers["Content-Type"] = "application/json"
        r = self._session.request(
            method,
            url,
            headers=headers,
            proxies=self.proxies,
            params=params,
            timeout=self.requests_timeout,
        )
        r.raise_for_status()
        return r.json()

    def _get(self, url, **kwargs):

        retries = self.max_retries
        delay = 1
        while retries > 0:
            try:
                return self._call("GET", url, kwargs)
            except HTTPError as e:
                retries -= 1
                status = e.response.status_code
                if status == 429 or (500 <= status < 600):
                    if retries < 0:
                        raise
                    else:
                        print("retrying ..." + str(delay) + " secs")
                        time.sleep(delay + 1)
                        delay += 1
                else:
                    raise
            except Exception as e:
                print("exception", str(e))
                retries -= 1
                if retries >= 0:
                    print("retrying ..." + str(delay) + "secs")
                    time.sleep(delay + 1)
                    delay += 1
                else:
                    raise

    def check_and_append_artist(self, name, idx, artist, track):

        variations = [
            artist.split(", ", 1)[0],
            artist.split(" featuring ")[0],
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
            self.apple_df.append((name, idx, artist, track, None, None, None, None))
        else:
            self.apple_df.append(
                (name, idx, variations[0], track, None, None, None, None)
            )

    def tracks(self, name, genre):
        self.offset = 0
        time.sleep(1)
        i = 0
        p = 0
        while i < 10:
            if name == "APPLE MUSIC TOP SONGS - ALL GENRES":
                chart_url = f"https://api.music.apple.com/v1/catalog/us/charts?chart=most-played&offset={self.offset}&types=songs"
            else:
                chart_url = f"https://api.music.apple.com/v1/catalog/us/charts?chart=most-played&offset={self.offset}&types=songs&genre={genre}"

            chart = self._get(chart_url)
            charts = chart["results"]["songs"]
            for c in charts:
                li = c["data"]
                for l in li:
                    track = l["attributes"]["name"]
                    artist = l["attributes"]["artistName"]

                    checked_pub = check_prod(
                        self.pub_songs, self.pub_artists, track, artist
                    )

                    artist_exists = any(
                        art.lower() in artist.lower() for art in self.roster_artists
                    )
                    if checked_pub or artist_exists:
                        self.apple_df.append(
                            (name, p + 1, artist, track, None, None, None, None)
                        )
                    else:
                        self.check_and_append_artist(name, p + 1, artist, track)
                    p += 1

            self.offset += 20
            i += 1

    def albums(self, name, genre):
        self.offset = 0
        time.sleep(1)
        i = 0
        p = 0
        while i < 10:
            if name == "APPLE MUSIC TOP ALBUMS - ALL GENRES":
                chart_url = f"https://api.music.apple.com/v1/catalog/us/charts?chart=most-played&offset={self.offset}&types=albums"
            else:
                chart_url = f"https://api.music.apple.com/v1/catalog/us/charts?chart=most-played&offset={self.offset}&types=albums&genre={genre}"

            chart = self._get(chart_url)
            charts = chart["results"]["albums"]
            for c in charts:
                li = c["data"]
                for l in li:
                    album = l["attributes"]["name"]
                    artist = l["attributes"]["artistName"]

                    checked_pub = check_prod_albums(
                        self.pub_albums, self.pub_artists, album, artist
                    )

                    artist_exists = any(
                        art.lower() in artist.lower() for art in self.roster_artists
                    )
                    if checked_pub or artist_exists:
                        self.apple_df.append(
                            (name, p + 1, artist, album, None, None, None, None)
                        )
                    else:
                        self.check_and_append_artist(name, p + 1, artist, album)
                    p += 1

            self.offset += 20
            i += 1

    def music_videos(self, name, genre):
        self.offset = 0
        total_videos = 0

        i = 0
        p = 0
        while i < 10:

            if name == "APPLE MUSIC TOP MUSIC VIDEOS - ALL GENRES":
                chart_url = f"https://api.music.apple.com/v1/catalog/us/charts?chart=most-played&offset={self.offset}&types=music-videos"
            else:
                chart_url = f"https://api.music.apple.com/v1/catalog/us/charts?chart=most-played&offset={self.offset}&types=music-videos&genre={genre}"

            chart = self._get(chart_url)
            charts = chart["results"]["music-videos"]
            for c in charts:
                li = c["data"]
                total_videos += len(li)
                for i, l in enumerate(li):
                    song = l["attributes"]["name"]
                    artist = l["attributes"]["artistName"]

                    checked_pub = check_prod(
                        self.pub_songs, self.pub_artists, song, artist
                    )
                    artist_exists = any(
                        art.lower() in artist.lower() for art in self.roster_artists
                    )
                    if checked_pub or artist_exists:
                        self.apple_df.append(
                            (name, i + 1, artist, song, None, None, None)
                        )
                    else:
                        self.check_and_append_artist(name, p + 1, artist, song)

                    p += 1

            self.offset += 20
            i += 1
        print(f"Total videos for {name}: {total_videos}")

    def get_copyright_info(self, artist, song, chart_type, source="spotify"):
        artist = artist.lower()

        if "album" in chart_type.lower():
            method = self.spotify_client.get_artist_copy_album
        else:
            method = self.spotify_client.get_artist_copy_track

        copyright = method(artist, song, source)
        return copyright

    def chart_search(self, apple_data):

        for i, row in apple_data.iloc[:].iterrows():
            chart = row["Chart"]
            position = row["Position"]
            artist = row["Artist"]
            song = row["Song"] if type(row["Song"]) != float else "NA"
            movement = row["Movement"]
            label = row["Label"]
            link = row["Link"]
            unsigned_status = row["Unsigned"]

            artist_exists = any(
                art.lower() in artist.lower() for art in self.roster_artists
            )
            song_exists_in_album = (
                check_prod_albums(self.pub_albums, self.pub_artists, song, artist)
                if "album" in chart.lower()
                else False
            )
            checked_pub = (
                check_prod(self.pub_songs, self.pub_artists, song, artist)
                if not song_exists_in_album
                else False
            )

            if checked_pub or artist_exists or song_exists_in_album:
                self.us.append(
                    (
                        chart,
                        position,
                        artist,
                        song,
                        None,
                        "L2TK",
                        movement,
                        None,
                        label,
                    )
                )
                continue
            if artist in self.already_checked:
                print("already_checked", artist)
                continue
            if unsigned_status != "UNSIGNED" and movement != "New":
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
                continue

            if unsigned_status == "UNSIGNED" and movement != "New":
                print(artist, song, link, label, "from yesterday")
                self.us.append(
                    (
                        chart,
                        position,
                        artist,
                        song,
                        "UNSIGNED",
                        None,
                        movement,
                        link,
                        label,
                    )
                )
                continue

            if movement == "New":
                copyright = None
                copyright = self.get_copyright_info(artist, song, chart)

                if not copyright and " & " in artist:
                    artist = artist.split(" & ")[0]
                    copyright = self.get_copyright_info(artist, song, chart)

                if copyright:
                    year_pattern = r"202[0-4]"
                    if not re.search(year_pattern, copyright[0]):
                        continue

                    matched_labels = list(
                        filter(
                            lambda x: smart_partial_match(x, copyright[0]),
                            self.majorlabels,
                        )
                    )

                    if not matched_labels:
                        try:
                            self.us.append(
                                (
                                    chart,
                                    position,
                                    artist,
                                    song,
                                    "UNSIGNED",
                                    None,
                                    movement,
                                    copyright[1],
                                    copyright[0],
                                )
                            )
                        except (IndexError, TypeError):
                            self.us.append(
                                (
                                    chart,
                                    position,
                                    artist,
                                    song,
                                    "UNSIGNED",
                                    None,
                                    movement,
                                    "No Link",
                                    label,
                                )
                            )
                    else:
                        self.us.append(
                            (
                                chart,
                                position,
                                artist,
                                song,
                                None,
                                None,
                                movement,
                                None,
                                copyright[0],
                            )
                        )


def scrape_all():
    scrape = AppleMusicAPI(APPLE_PRIVATE_KEY, APPLE_KEY_ID, APPLE_TEAM_ID)

    scrape.tracks("APPLE MUSIC TOP SONGS - ALL GENRES", None)
    scrape.tracks("APPLE MUSIC TOP SONGS - HIP-HOP", 18)
    scrape.tracks("APPLE MUSIC TOP SONGS - ALT", 20)
    scrape.tracks("APPLE MUSIC TOP SONGS - POP", 14)
    scrape.tracks("APPLE MUSIC TOP SONGS - R&B", 15)
    scrape.tracks("APPLE MUSIC TOP SONGS - ROCK", 21)
    scrape.tracks("APPLE MUSIC TOP SONGS - COUNTRY", 6)
    scrape.albums("APPLE MUSIC TOP ALBUMS - ALL GENRES", None)
    scrape.albums("APPLE MUSIC TOP ALBUMS - HIP-HOP", 18)
    scrape.albums("APPLE MUSIC TOP ALBUMS - ALT", 20)
    scrape.albums("APPLE MUSIC TOP ALBUMS - POP", 14)
    scrape.albums("APPLE MUSIC TOP ALBUMS - R&B", 15)
    scrape.albums("APPLE MUSIC TOP ALBUMS - ROCK", 21)
    scrape.albums("APPLE MUSIC TOP ALBUMS - COUNTRY", 6)
    scrape.albums("APPLE MUSIC TOP ALBUMS - SINGER SONGWRITER", 10)
    scrape.music_videos("APPLE MUSIC TOP MUSIC VIDEOS - ALL GENRES", None)
    scrape.music_videos("APPLE MUSIC TOP MUSIC VIDEOS - HIP-HOP", 18)
    scrape.music_videos("APPLE MUSIC TOP MUSIC VIDEOS - ALT", 20)
    scrape.music_videos("APPLE MUSIC TOP MUSIC VIDEOS - POP", 14)
    scrape.music_videos("APPLE MUSIC TOP MUSIC VIDEOS - R&B", 15)
    scrape.music_videos("APPLE MUSIC TOP MUSIC VIDEOS - ROCK", 21)
    scrape.music_videos("APPLE MUSIC TOP MUSIC VIDEO - COUNTRY", 6)
    scrape.music_videos("APPLE MUSIC TOP MUSIC VIDEO- SINGER SONGWRITER", 10)

    apple_data = pd.DataFrame(
        scrape.apple_df,
        columns=[
            "Chart",
            "Position",
            "Artist",
            "Song",
            "Movement",
            "Days",
            "Peak",
            "Date",
        ],
    )

    data_yesterday = db.get_apple_charts()

    for i, r in apple_data.iterrows():
        pos = r["Position"]
        chart = r["Chart"]
        match = data_yesterday.loc[
            (data_yesterday["song"].str.lower() == r["Song"].lower())
            & (data_yesterday["chart"].str.lower() == chart.lower())
        ]

        if not match.empty:
            apple_data.at[i, "Label"] = match["label"].iloc[0]
            apple_data.at[i, "Link"] = match["link"].iloc[0]
            apple_data.at[i, "Unsigned"] = match["unsigned"].iloc[0]
            pos_y = int(match["position"].iloc[0])

            if pos_y == pos:
                apple_data.at[i, "Movement"] = "0"
            else:
                movement_value = pos_y - pos
                apple_data.at[i, "Movement"] = str(movement_value)
        else:
            apple_data.at[i, "Movement"] = "New"

    scrape.chart_search(apple_data)

    final_data = pd.DataFrame(
        scrape.us,
        columns=[
            "Chart",
            "Position",
            "Artist",
            "Song",
            "Unsigned",
            "L2TK",
            "Movement",
            "Link",
            "Label",
        ],
    )
    final_data = final_data.replace({np.nan: None})

    return final_data


other = []
l2tk_chart = []
prospect_list = []
prospects = db.get_prospects()


def create_html(type, df, report_name):
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
            {report_name} - {datetime.now(pacific_tz).strftime("%m/%d/%y")}
            <br> {conor}, {ari}, {laura}, {micah}, {lucas}
        </p>
        """

    chart_header = None

    def add_content_and_header(chart):
        nonlocal html_body
        if l2tk_chart or other or prospect_list:
            header_text = f"<br><br><strong style='text-decoration: underline;'>{chart.upper()}</strong><br><br>"
            html_body += header_text

            if l2tk_chart:
                html_body += "<p>L2TK:</p>"
                for p in l2tk_chart:
                    html_body += f"<p>{p}</p>"

            if prospect_list:
                html_body += "<br><p>PROSPECT:</p>"
                for p in prospect_list:
                    html_body += (
                        f"<p><span style='background-color: red;'>{p}</span></p>"
                    )

            if other:
                html_body += "<br><p>NEW ADDS:</p>"
                for p in other:
                    html_body += f"<p>{p['c']}</p>"

        l2tk_chart.clear()
        prospect_list.clear()
        other.clear()

    for (
        chart,
        position,
        artist,
        song,
        unsigned,
        l2tk,
        movement,
        link,
        label,
    ) in df.itertuples(index=False):
        if chart != chart_header:
            if chart_header:
                add_content_and_header(chart_header)

            chart_header = chart
        if type == "chart":
            if l2tk == "L2TK":
                if artist.lower() in prospects:
                    prospect_list.append(
                        f"""
                            {position}. {artist} - {song} ({'=' if movement == '0' else movement})
                            """
                    )
                    continue

            if unsigned == "UNSIGNED":
                if movement.startswith("-"):
                    color = "red"
                elif movement == "New":
                    color = "yellow"
                elif movement == "0":
                    color = "black"
                else:
                    color = "green"
                other.append(
                    {
                        "c": f"""
                            {position}. {artist} - {song} <span style='color:{color};'>({movement})</span><br>
                            <span class='indent'>• Label: {label} (UNSIGNED)</span><br>
                            <span class='indent'>• <a href='{link}'>{link}</a></span>
                            """,
                        "h": True,
                    }
                )
        else:
            if l2tk == "L2TK":
                if artist.lower() not in prospects:
                    l2tk_chart.append(
                        f"""
                            {position}. {artist} - {song} ({'=' if movement == '0' else movement}) (L2TK)<br>
                            """
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


def update_apple_charts():
    df = scrape_all()
    db.insert_apple_charts(df)
    body = create_html("roster", df, "Apple Roster Report")
    subject = f'Apple Roster Report - {datetime.now(pacific_tz).strftime("%m/%d/%y")}'
    send_email_ses(subject, body)

    body = create_html("chart", df, "Apple Chart Report")
    subject = f'Apple Chart Report - {datetime.now(pacific_tz).strftime("%m/%d/%y")}'
    send_email_ses(subject, body)


def lambda_handler(event, context):
    update_apple_charts()
    return {
        "statusCode": 200,
        "body": "Scrape complete",
    }


# lambda_handler(None, None)
