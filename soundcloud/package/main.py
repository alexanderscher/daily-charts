from botocore.exceptions import ClientError
import pandas as pd
from selenium import webdriver
from tempfile import mkdtemp
import time
from selenium.webdriver.common.by import By
import os
import boto3
import datetime
from pytz import timezone

pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)
pd.set_option("display.colheader_justify", "center")
pd.set_option("display.precision", 3)

from db.get_db import FetchDB
from spotify_api import SpotifyAPI
from check import smart_partial_match

pacific_tz = timezone("America/Los_Angeles")

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
USER_ID = os.getenv("SPOTIFY_USER_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
db = FetchDB()

charts = [
    (
        "Soundcloud Top 50 / All music genres",
        "https://soundcloud.com/music-charts-us/sets/all-music-genres",
    ),
    (
        "Soundcloud Top 50 / Hip-hop & Rap",
        "https://soundcloud.com/music-charts-us/sets/hip-hop",
    ),
    (
        "Soundcloud Top 50 / R&B & Soul",
        "https://soundcloud.com/music-charts-us/sets/r-b",
    ),
    ("Soundcloud Top 50 / Pop", "https://soundcloud.com/music-charts-us/sets/pop"),
    (
        "Soundcloud Top 50 / Rock",
        "https://soundcloud.com/music-charts-us/sets/rock",
    ),
    (
        "Soundcloud Top 50 / Folk",
        "https://soundcloud.com/music-charts-us/sets/folk",
    ),
    (
        "Soundcloud Top 50 / Country",
        "https://soundcloud.com/music-charts-us/sets/country",
    ),
    (
        "Soundcloud Top 50 / New & hot",
        "https://soundcloud.com/music-charts-us/sets/new-hot",
    ),
    (
        "Soundcloud Top 50 / Next Pro",
        "https://soundcloud.com/music-charts-us/sets/next-pro",
    ),
    (
        "Soundcloud Trending / All Genres",
        "https://soundcloud.com/trending-music-us/sets/soundcloud-1",
    ),
    (
        "Soundcloud Trending / Pop",
        "https://soundcloud.com/trending-music-us/sets/pop-1",
    ),
    (
        "Soundcloud Trending / Hip-Hop",
        "https://soundcloud.com/trending-music-us/sets/hip-hop-rap",
    ),
    (
        "Soundcloud Trending / R&B",
        "https://soundcloud.com/trending-music-us/sets/r-b-1",
    ),
    (
        "Soundcloud Trending / Country",
        "https://soundcloud.com/trending-music-us/sets/country",
    ),
    (
        "Soundcloud Trending / Folk",
        "https://soundcloud.com/trending-music-us/sets/folk",
    ),
    (
        "Soundcloud Trending / Indie",
        "https://soundcloud.com/trending-music-us/sets/indie-1",
    ),
    (
        "Soundcloud Trending / Rock",
        "https://soundcloud.com/trending-music-us/sets/rock-metal-punk",
    ),
    (
        "Soundcloud Trending / Latin",
        "https://soundcloud.com/trending-music-us/sets/latin",
    ),
    (
        "Soundcloud Trending / Electronic",
        "https://soundcloud.com/trending-music-us/sets/electronic-1",
    ),
    (
        "Soundcloud Trending / Reggae",
        "https://soundcloud.com/trending-music-us/sets/reggae",
    ),
    (
        "Soundcloud Trending / Soul",
        "https://soundcloud.com/trending-music-us/sets/soul",
    ),
    (
        "Soundcloud Trending / House",
        "https://soundcloud.com/trending-music-us/sets/house",
    ),
]


class Scrape:
    def __init__(self, driver):
        self.roster_artists = db.get_roster_artists()
        self.major_labels = db.get_major_labels()
        self.signed_artists = db.get_signed_artists()
        self.df = []
        self.us = []
        self.already_checked = []
        self.other = []
        self.prospect_list = []
        self.driver = driver
        self.client = SpotifyAPI(CLIENT_ID, USER_ID, CLIENT_SECRET)

    def check_and_append_artist(self, chart, idx, artist, track, song_link):

        if artist.startswith("@"):
            artist = artist.split("@", 1)[1].strip()
        if "(" in artist:
            artist = artist.split(" (", 1)[0].strip()

        variations = [
            artist.split(", ", 1)[0],
            artist.split(" featuring ")[0],
            artist.split(" feat. ")[0],
            artist.split(" x ")[0],
            artist,
        ]

        if " & " in artist:
            part1, part2 = artist.split(" & ", 1)
            variations.extend([part1, part2])

        elif " and " in artist:
            part1, part2 = artist.split(" and ", 1)
            variations.extend([part1, part2])

        matched_variation = any(
            a.lower() in map(str.lower, self.signed_artists + self.roster_artists)
            for a in variations
        )

        if matched_variation:
            print(matched_variation, artist)
            return

        if (" & " in artist or " and " in artist) and ", " not in artist:
            self.df.append((chart, idx, artist.strip(), track, song_link))
        else:
            self.df.append((chart, idx, variations[0].strip(), track, song_link))

    def soundcloud(self, name, url):
        self.driver.get(url)
        time.sleep(10)

        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(6)

        row = self.driver.find_elements(
            By.XPATH,
            '//*[@id="content"]/div/div[2]/div[1]/div/div[2]/div[2]/div/div[3]/div/ul/li',
        )
        if len(row) <= 45:
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            time.sleep(4)
            row = self.driver.find_elements(
                By.XPATH,
                '//*[@id="content"]/div/div[2]/div[1]/div/div[2]/div[2]/div/div[3]/div/ul/li',
            )
        else:
            row = self.driver.find_elements(
                By.XPATH,
                '//*[@id="content"]/div/div[2]/div[1]/div/div[2]/div[2]/div/div[3]/div/ul/li',
            )
        print(len(row))

        for i, r in enumerate(row):
            idx = i + 1
            song_link = r.find_element(By.XPATH, ".//div/div[3]/a[2]")
            sl = song_link.get_attribute("href")
            s = song_link.text
            a = r.find_element(By.XPATH, ".//div/div[3]/a[1]").text

            self.check_and_append_artist(name, idx, a, s, sl)

    def chart_search(self, data):
        for (
            index,
            chart,
            position,
            artist,
            song,
            sc,
            label,
            link,
            unsigned,
            movement,
        ) in data.itertuples(index=False):

            if artist in self.already_checked:
                continue

            elif movement != "New" and unsigned != "UNSIGNED":
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
                        None,
                    )
                )
            elif unsigned == "UNSIGNED" and movement != "New":
                self.us.append(
                    (
                        chart,
                        position,
                        artist,
                        song,
                        "UNSIGNED",
                        None,
                        movement,
                        sc,
                        link,
                        label,
                    )
                )
                continue
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
                        artist.lower(), song, "daily_chart"
                    )

                    if not copyright and " & " in artist:
                        artist = artist.split(" & ")[0]
                        copyright = self.client.get_artist_copy_track(
                            artist.lower(), song, "daily_chart"
                        )
                    if not copyright and " and " in artist:
                        artist = artist.split(" and ")[0]
                        copyright = self.client.get_artist_copy_track(
                            artist.lower(), song, "daily_chart"
                        )

                    if copyright:
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
                                    movement,
                                    sc,
                                    copyright[1],
                                    copyright[0],
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
                                    None,
                                    copyright[1],
                                    copyright[0],
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
    driver = webdriver.Chrome(service=service, options=options)

    scrape = Scrape(driver)

    for title, url in charts:
        scrape.soundcloud(title, url)

    df_all_charts = pd.DataFrame(
        scrape.df, columns=["Chart", "Position", "Artist", "Song", "SC Link"]
    )
    data_yesterday = db.get_soundcloud_charts()

    for i, r in df_all_charts.iterrows():
        match = data_yesterday.loc[(data_yesterday["song"] == r["Song"])]

        if not match.empty:
            df_all_charts.at[i, "Label"] = match["label"].iloc[0]
            df_all_charts.at[i, "Link"] = match["spotify_link"].iloc[0]
            df_all_charts.at[i, "Unsigned"] = match["unsigned"].iloc[0]

        pos = int(r["Position"])
        match_chart = data_yesterday.loc[
            (data_yesterday["song"] == r["Song"])
            & (data_yesterday["chart"] == r["Chart"])
        ]
        if not match_chart.empty:
            pos_y = match_chart["position"].iloc[0]
            df_all_charts.at[i, "Movement"] = str(pos_y - pos)
        else:
            df_all_charts.at[i, "Movement"] = "New"

    scrape.chart_search(df_all_charts)
    unsigned = pd.DataFrame(
        scrape.us,
        columns=[
            "Chart",
            "Position",
            "Artist",
            "Song",
            "Unsigned",
            "L2TK",
            "Movement",
            "SC Link",
            "Link",
            "Label",
        ],
    )
    db.insert_soundcloud_charts(unsigned)
    body = scrape.create_html("Soundcloud Chart Report", unsigned)

    subject = (
        f'{'Soundcloud Chart Report'}- {datetime.now(pacific_tz).strftime("%m/%d/%y")}'
    )
    send_email_ses(subject, body)


def lambda_handler(event, context):
    try:
        scrape_all()
    except Exception as e:
        print(e)
        return {
            "statusCode": 500,
            "body": "soundcloud failed",
        }

    return {
        "statusCode": 200,
        "body": "soundcloud complete",
    }
