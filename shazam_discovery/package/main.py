from botocore.exceptions import ClientError
import pandas as pd
from pytz import timezone
import os
import boto3
import datetime
from datetime import datetime, timedelta
import re
import requests
from bs4 import BeautifulSoup
from requests.exceptions import HTTPError
import jwt
import time


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

APPLE_TEAM_ID = os.getenv("APPLE_TEAM_ID")
APPLE_KEY_ID = os.getenv("APPLE_KEY_ID")
APPLE_PRIVATE_KEY = os.getenv("APPLE_PRIVATE_KEY")

if not APPLE_TEAM_ID or not APPLE_KEY_ID or not APPLE_PRIVATE_KEY:
    raise ValueError("Missing required environment variables for Apple Music API")

APPLE_PRIVATE_KEY = (
    f"-----BEGIN PRIVATE KEY-----\n{APPLE_PRIVATE_KEY}\n-----END PRIVATE KEY-----"
)

db = FetchDB()
pacific_tz = timezone("America/Los_Angeles")
non_latin_pattern = (
    r"[\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF\u0400-\u04FF\u1100-\u11FF\uAC00-\uD7AF]"
)
path = "/tmp/shazam.csv"


class ShazamDiscovery:
    """
    This class is used to connect to the Apple Music API and make requests for catalog resources
    """

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
        self._alg = "ES256"  # encryption algo that Apple requires
        self.token_str = ""  # encrypted api token
        self.session_length = session_length
        self.token_valid_until = None
        self.generate_token(session_length)
        self.root = "https://api.music.apple.com/v1/"
        self.max_retries = max_retries
        self.requests_timeout = requests_timeout
        self.signed_artists = db.get_signed_artists()
        self.roster_artists = db.get_roster_artists()
        self.major_labels = db.get_major_labels()
        self.prospect = db.get_prospects()
        self.client = SpotifyAPI(CLIENT_ID, USER_ID, CLIENT_SECRET)
        self.repeat = []
        self.df = []
        self.us = []
        self.already_checked = []
        self.other = []
        self.prospect_list = []

        if requests_session:
            self._session = requests.Session()
        else:
            self._session = requests.api
        self.playlist_ids = None

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
            "iss": self._team_id,  # issuer
            "iat": int(datetime.now().timestamp()),  # issued at
            "exp": int(token_exp_time.timestamp()),  # expiration time
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
        r.raise_for_status()  # Check for error
        return r.json()

    def _get(self, url, **kwargs):

        retries = self.max_retries
        delay = 1
        while retries > 0:
            try:
                return self._call("GET", url, kwargs)
            except HTTPError as e:  # Retry for some known issues
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

    def search(self):

        pl_info = self._get(
            f"https://api.music.apple.com/v1/catalog/us/playlists/pl.eba7614f65cd42ff8868b2d8181f49f4"
        )
        pl_tracks = pl_info["data"][0]["relationships"]["tracks"]["data"]

        for i, track in enumerate(pl_tracks):
            try:

                artist = track["attributes"]["artistName"]
                track_name = track["attributes"]["name"]
                self.check_and_append_artist(
                    "Shazam Chart / Discovery Top 50", i + 1, artist, track_name
                )
            except KeyError as e:
                pass

    def shazam_discovery(self, name, url):
        response = requests.get(url)

        if response.status_code != 200:
            print(f"Failed to access {url}. Status code: {response.status_code}")
            return

        soup = BeautifulSoup(response.content, "html.parser")

        song_items = soup.find_all("div", class_="page_songItem__lAdHy")

        for idx, item in enumerate(song_items, start=1):
            artist = item.find(
                "span", class_="Text-module_text-gray-900__Qcj0F"
            ).get_text(strip=True)

            track = item.find(
                "span", class_="SongItem-module_metadataLine__7Mm6B"
            ).get_text(strip=True)

            self.check_and_append_artist(name, idx, artist, track)

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
            self.df.append((name, idx, artist, track))
        else:
            self.df.append((name, idx, variations[0], track))

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
            link,
            label,
            unsigned,
            movement,
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
                        movement,
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
                                copyright[1],
                                copyright[0],
                                movement,
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
    apple_music_client = ShazamDiscovery(APPLE_PRIVATE_KEY, APPLE_KEY_ID, APPLE_TEAM_ID)
    apple_music_client.shazam_discovery(
        "Shazam Chart / Discovery Top 10: US",
        "https://www.shazam.com/charts/discovery/united-states",
    )
    apple_music_client.shazam_discovery(
        "Shazam Chart / Discovery Top 10: UK",
        "https://www.shazam.com/charts/discovery/united-kingdom",
    )
    apple_music_client.shazam_discovery(
        "Shazam Chart / Discovery Top 10: Canada",
        "https://www.shazam.com/charts/discovery/canada",
    )
    apple_music_client.shazam_discovery(
        "Shazam Chart / Discovery Top 10: Australia",
        "https://www.shazam.com/charts/discovery/australia",
    )

    shazam_charts = pd.DataFrame(
        apple_music_client.df, columns=["Chart", "Position", "Artist", "Song"]
    )

    data_yesterday = db.get_shazam_discovery_charts()
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

    apple_music_client.chart_search(shazam_charts)
    unsigned_charts = pd.DataFrame(
        apple_music_client.us,
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

    db.insert_shazam_discovery_charts(unsigned_charts)
    body = apple_music_client.create_html("Shazam Discovery Report", unsigned_charts)

    subject = (
        f'Shazam Discovery Report - {datetime.now(pacific_tz).strftime("%m/%d/%y")}'
    )
    send_email_ses(subject, body)


def lambda_handler(event, context):
    scrape_all()
    return {
        "statusCode": 200,
        "body": "Scrape complete",
    }


# lambda_handler(None, None)
