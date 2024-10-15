from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time
from botocore.exceptions import ClientError
import pandas as pd
import os
from pytz import timezone
import boto3
from datetime import datetime
from tempfile import mkdtemp
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

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
USER_ID = os.getenv("SPOTIFY_USER_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

SPOTIFY_CHART_USERNAME = os.getenv("SPOTIFY_CHART_USERNAME")
SPOTIFY_CHART_PASSWORD = os.getenv("SPOTIFY_CHART_PASSWORD")

db = FetchDB()

pacific_tz = timezone("America/Los_Angeles")


class Scrape:
    def __init__(self, driver):
        self.db = FetchDB()
        self.df = []
        self.us = []
        self.l2tk_chart = []
        self.other = []
        self.prospect_list = []
        self.driver = driver
        self.pub_songs = self.db.get_pub_songs()
        self.pub_artists = self.db.get_pub_artists()
        self.roster_artists = self.db.get_roster_artists()
        self.major_labels = self.db.get_major_labels()
        self.signed_artists = self.db.get_signed_artists()
        self.prospects = self.db.get_prospects()
        self.client = SpotifyAPI(CLIENT_ID, USER_ID, CLIENT_SECRET)

    def spotify_signin(self):
        self.driver.get("https://accounts.spotify.com/en/login")
        input_username = self.driver.find_element(By.XPATH, '//*[@id="login-username"]')
        input_password = self.driver.find_element(By.XPATH, '//*[@id="login-password"]')
        time.sleep(2)

        input_username.click()
        input_username.clear()
        input_username.send_keys(SPOTIFY_CHART_USERNAME)
        time.sleep(2)
        input_password.click()
        input_password.clear()
        input_password.send_keys(SPOTIFY_CHART_PASSWORD)
        time.sleep(2)
        button_log_in = self.driver.find_element(
            By.CLASS_NAME, "ButtonInner-sc-14ud5tc-0"
        )
        button_log_in.click()
        time.sleep(5)

    def check_roster(
        self, name, position, artist, track, ch, days, peak, date, callback
    ):
        checked_pub = check_prod(self.pub_songs, self.pub_artists, track, artist)
        artist_exists = any(
            art.lower() in artist.lower() for art in self.roster_artists
        )

        if checked_pub or artist_exists:

            self.df.append((name, position, artist, track, ch, days, peak, date))

        elif callback == None:
            pass
        else:
            callback()

    def spotify(self, name, url):

        self.driver.get(url)
        time.sleep(5)

        d = self.driver.find_element(By.XPATH, '//*[@id="date_picker"]')
        date = d.get_attribute("value")
        dvg = self.driver.find_elements(By.TAG_NAME, "tr")
        dvg_rows = len(dvg) - 1
        dvg_table_data = self.driver.find_elements(By.TAG_NAME, "td")
        dvg_table_data_length = len(dvg_table_data)
        dvg_columns = int(dvg_table_data_length / dvg_rows)
        non_latin_pattern = r"[\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF\u0400-\u04FF]"

        for i, song in enumerate(dvg[1 : len(dvg)]):
            position = (
                dvg_table_data[i * dvg_columns + 1]
                .find_elements(By.XPATH, ".//span")[0]
                .text
            )
            peak = dvg_table_data[i * dvg_columns + 3].text
            prev = dvg_table_data[i * dvg_columns + 4].text
            days = dvg_table_data[i * dvg_columns + 5].text
            mov = (
                dvg_table_data[i * dvg_columns + 1]
                .find_elements(By.XPATH, ".//span")[1]
                .text
            )

            try:
                mov = int(prev) - int(position)
                if mov > 0:
                    mov = "+" f"{mov}"
            except ValueError:
                if peak != position and prev == "—":
                    mov = "RE-ENTRY"
                else:
                    mov = "NEW"

            song_anchors = dvg_table_data[i * dvg_columns + 2].find_elements(
                By.XPATH, ".//a"
            )
            track = song_anchors[1].text
            artist = song_anchors[2].text

            def callback():
                if not list(
                    filter(lambda x: (x.lower() == artist.lower()), self.signed_artists)
                ):
                    if re.search(non_latin_pattern, artist):
                        print(f"Non-latin artist: {artist}")
                        pass
                    else:
                        self.df.append(
                            (name, position, artist, track, mov, None, None, date)
                        )

            self.check_roster(
                name,
                position,
                artist,
                track,
                mov,
                days,
                peak,
                date,
                callback,
            )

    def chart_search(self):
        spotify_df = pd.DataFrame(
            self.df,
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
        data_yesterday = db.get_spotify_charts()

        for i, r in spotify_df.iterrows():
            match = data_yesterday.loc[(data_yesterday["song"] == r["Song"])]
            if not match.empty:
                spotify_df.at[i, "Label"] = match["label"].iloc[0]
                spotify_df.at[i, "Link"] = match["link"].iloc[0]
                spotify_df.at[i, "Unsigned"] = match["unsigned"].iloc[0]

        for (
            chart,
            position,
            artist,
            song,
            movement,
            days,
            peak,
            date,
            label,
            link,
            unsigned_status,
        ) in spotify_df.itertuples(index=False):

            if ", " in artist:
                a = artist.split(", ")
                artist = a[0]

            elif " featuring " in artist:
                a = artist.split(" featuring ")
                artist = a[0]

            elif "feat." in artist:
                a = artist.split("feat.")
                artist = a[0]

            checked_pub = check_prod(self.pub_songs, self.pub_artists, song, artist)
            artist_exists = any(
                art.lower() in artist.lower() for art in self.roster_artists
            )

            if checked_pub or artist_exists:
                self.us.append(
                    (
                        chart,
                        position,
                        artist,
                        song,
                        None,
                        "L2TK",
                        movement,
                        days,
                        peak,
                        None,
                        None,
                        date,
                    )
                )
                continue
            if unsigned_status == "UNSIGNED":
                print(f"{position}.", artist, "-", song, "(UNSIGNED) from yesterday")
                self.us.append(
                    (
                        chart,
                        position,
                        artist,
                        song,
                        "UNSIGNED",
                        None,
                        movement,
                        None,
                        None,
                        link,
                        label,
                        date,
                    )
                )
                continue

            if movement == "NEW":

                if list(
                    filter(lambda x: (x.lower() == artist.lower()), self.signed_artists)
                ):
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
                            None,
                            None,
                            None,
                            date,
                        )
                    )

                else:
                    if ", " in artist.lower():
                        a = artist(", ")
                        artist = a[0]
                        copyright = self.client.get_artist_copy_track(
                            artist.lower(), song, "spotify"
                        )

                    elif " featuring " in artist.lower():
                        a = artist(" featuring ")
                        artist = a[0]
                        copyright = self.client.get_artist_copy_track(
                            artist.lower(), song, "spotify"
                        )

                    elif "feat." in artist.lower():
                        a = artist("feat.")
                        artist = a[0]
                        copyright = self.client.get_artist_copy_track(
                            artist.lower(), song, "spotify"
                        )
                    else:

                        copyright = self.client.get_artist_copy_track(
                            artist.lower(), song, "spotify"
                        )

                    if copyright:
                        matched_labels = list(
                            filter(
                                lambda x: smart_partial_match(x, copyright[0].lower()),
                                self.major_labels,
                            )
                        )

                        if not matched_labels:

                            self.us.append(
                                (
                                    chart,
                                    position,
                                    artist,
                                    song,
                                    "UNSIGNED",
                                    None,
                                    movement,
                                    None,
                                    None,
                                    copyright[1],
                                    copyright[0],
                                    date,
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
                                    None,
                                    None,
                                    None,
                                    date,
                                )
                            )

    def create_html(self, type, chart_name):
        conor = os.getenv("CONOR")
        ari = os.getenv("ARI")
        laura = os.getenv("LAURA")
        micah = os.getenv("MICAH")

        final_df = unsigned = pd.DataFrame(
            self.us,
            columns=[
                "Chart",
                "Position",
                "Artist",
                "Song",
                "Unsigned",
                "L2TK",
                "Movement",
                "Days",
                "Peak",
                "Link",
                "Label",
                "Date",
            ],
        )
        db.insert_spotify_charts(final_df)

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
            <br> {conor}, {ari}, {laura}, {micah}
        </p>
        """

        chart_header = None

        def add_content_and_header(chart, date):
            nonlocal html_body
            if self.l2tk_chart or self.other or self.prospect_list:
                header_text = f"<br><br><strong style='text-decoration: underline;'>{chart.upper()} - {date.upper()}</strong><br><br>"
                html_body += header_text

                if self.l2tk_chart:
                    html_body += "<p>L2TK:</p>"
                    for p in self.l2tk_chart:
                        html_body += f"<p>{p}</p>"

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
            movement,
            days,
            pea,
            link,
            label,
            date,
        ) in final_df.itertuples(index=False):
            day = str(days).replace(".0", "")
            peak = str(pea).replace(".0", "")
            chart = chart.replace("- Freddy", "")
            movement = str(movement).replace(".0", "")
            if chart != chart_header:
                if chart_header:
                    add_content_and_header(chart_header, date)

                chart_header = chart
            if type == "chart":
                if l2tk == "L2TK":
                    if artist.lower() in self.prospects:
                        self.prospect_list.append(
                            f"""
                            {position}. {artist} - {song} ({'=' if movement == '0' else movement})<br>
                            <span class='indent'>• Days on chart: {day}</span><br>
                            <span class='indent'>• Peak: {peak}</span>
                            """
                        )

                if unsigned == "UNSIGNED":
                    if movement == "0":
                        movement = "="
                    if movement.startswith("-"):
                        color = "red"
                    elif movement == "NEW":
                        color = "yellow"
                    elif movement == "=":
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
            else:
                if l2tk == "L2TK":
                    if artist.lower() not in self.prospects:
                        self.l2tk_chart.append(
                            f"""
                            {position}. {artist} - {song} ({'=' if movement == '0' else movement}) (L2TK)<br>
                            <span class='indent'>• Days on chart: {day}</span><br>
                            <span class='indent'>• Peak: {peak}</span>
                            """
                        )

        add_content_and_header(chart_header, date)

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

    options = webdriver.ChromeOptions()
    options.binary_location = "/opt/chrome/chrome"
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1963x1696")
    options.add_argument("--single-process")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-dev-tools")
    options.add_argument("--no-zygote")
    options.add_argument(f"--user-data-dir={mkdtemp()}")
    options.add_argument(f"--data-path={mkdtemp()}")
    options.add_argument(f"--disk-cache-dir={mkdtemp()}")
    options.add_argument("--remote-debugging-port=9222")
    service = webdriver.ChromeService("/opt/chromedriver")

    # local
    # from selenium.webdriver.chrome.service import Service
    # from webdriver_manager.chrome import ChromeDriverManager

    # service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(service=service, options=options)
    scrape = Scrape(driver)

    scrape.spotify_signin()
    scrape.spotify(
        "SPOTIFY GLOBAL",
        "https://charts.spotify.com/charts/view/regional-global-daily/latest",
    )
    scrape.spotify(
        "SPOTIFY USA", "https://charts.spotify.com/charts/view/regional-us-daily/latest"
    )
    scrape.spotify(
        "SPOTIFY CA", "https://charts.spotify.com/charts/view/regional-ca-daily/latest"
    )
    scrape.spotify(
        "SPOTIFY UK",
        "https://charts.spotify.com/charts/view/regional-gb-daily/latest",
    )
    scrape.spotify(
        "SPOTIFY VIRAL GLOBAL",
        "https://charts.spotify.com/charts/view/viral-global-daily/latest",
    )

    scrape.spotify(
        "SPOTIFY VIRAL US",
        "https://charts.spotify.com/charts/view/viral-us-daily/latest",
    )
    scrape.spotify(
        "SPOTIFY VIRAL CA",
        "https://charts.spotify.com/charts/view/viral-CA-daily/latest",
    )
    scrape.spotify(
        "SPOTIFY VIRAL NZ",
        "https://charts.spotify.com/charts/view/viral-nz-daily/latest",
    )
    scrape.spotify(
        "SPOTIFY VIRAL UK",
        "https://charts.spotify.com/charts/view/viral-gb-daily/latest",
    )
    scrape.driver.quit()
    scrape.chart_search()
    body = scrape.create_html("roster", "Spotify Roster Report")
    subject = f'Spotify Roster Report - {datetime.now(pacific_tz).strftime("%m/%d/%y")}'
    send_email_ses(subject, body)

    body = scrape.create_html("chart", "Spotify Chart Report")
    subject = f'Spotify Chart Report - {datetime.now(pacific_tz).strftime("%m/%d/%y")}'
    send_email_ses(subject, body)


def lambda_handler(event, context):
    scrape_all()
    return {
        "statusCode": 200,
        "body": "Scrape complete",
    }


# lambda_handler(None, None)
