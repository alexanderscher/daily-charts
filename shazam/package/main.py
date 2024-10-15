from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time
from botocore.exceptions import ClientError
import pandas as pd
from pytz import timezone
import os
import boto3
import datetime
from tempfile import mkdtemp
from datetime import datetime
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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


class Scrape:
    def __init__(self, driver):
        self.df = []
        self.us = []
        self.l2tk_chart = []
        self.other = []
        self.prospect_list = []
        self.driver = driver
        self.pub_songs = db.get_pub_songs()
        self.pub_artists = db.get_pub_artists()
        self.roster_artists = db.get_roster_artists()
        self.major_labels = db.get_major_labels()
        self.signed_artists = db.get_signed_artists()
        self.prospects = db.get_prospects()
        self.client = SpotifyAPI(CLIENT_ID, USER_ID, CLIENT_SECRET)

    def download(self, name, url, path):
        self.driver.get(url)
        time.sleep(5)
        non_latin_pattern = r"[\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF\u0400-\u04FF]"

        download_icon = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, ".Header_downloadCSVIcon__48xi4")
            )
        )
        download_icon.click()

        time.sleep(5)
        print(path)

        data = pd.read_csv(path, skiprows=2, on_bad_lines="skip")

        for i, row in data.iterrows():
            s = row["Title"]
            a = row["Artist"]
            idx = row["Rank"]
            if ", " in a:
                comma = a.split(", ", 1)[0]
                if list(
                    filter(
                        lambda x: (x.lower() == comma.lower()),
                        self.signed_artists + self.roster_artists,
                    )
                ):
                    continue
                else:
                    self.df.append((name, idx, a, s, None, None, None))
                    continue

            elif " & " in a:
                andpersand = a.split(" & ")[0]
                if list(
                    filter(
                        lambda x: (x.lower() == andpersand.lower()),
                        self.signed_artists + self.roster_artists,
                    )
                ):
                    continue
                else:
                    self.df.append((name, idx, a, s, None, None, None))
                    continue
            if " featuring " in a:
                ft = a.split(" featuring ")[0]
                if list(
                    filter(
                        lambda x: (x.lower() == ft.lower()),
                        self.signed_artists + self.roster_artists,
                    )
                ):
                    continue
                else:
                    self.df.append((name, idx, a, s, None, None, None))
                    continue
            elif " x " in a:
                ex = a.split(" x ")[0]
                if list(
                    filter(
                        lambda x: (x.lower() == ex.lower()),
                        self.signed_artists + self.roster_artists,
                    )
                ):
                    continue
                else:
                    self.df.append((name, idx, a, s, None, None, None))
                    continue
            else:
                if not list(
                    filter(
                        lambda x: (x.lower() == a.lower()),
                        self.signed_artists + self.roster_artists,
                    )
                ):
                    if re.search(non_latin_pattern, a):
                        print(f"Non-latin artist: {a}")
                        pass
                    elif re.search(non_latin_pattern, s):
                        print(f"Non-latin artist: {a}")
                        pass
                    else:
                        self.df.append((name, idx, a, s, None, None, None))
                        continue

        os.remove(path)

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

            if ", " in artist:
                a = artist.split(", ")
                artist = a[0]

            if " & " in artist:
                a = artist.split(" & ")
                artist = a[0]

            if unsigned == "UNSIGNED":

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

                if not copyright or (
                    "2023" not in copyright[0] and "2024" not in copyright[0]
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
                            copyright[0] if copyright else None,
                        )
                    )
                    continue

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
                                copyright[1],
                                copyright[0],
                                movement,
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
                                None,
                                copyright[0],
                                movement,
                            )
                        )

    def create_html(self, type, chart_name, data):
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
            {chart_name} - {datetime.now(pacific_tz).strftime("%m/%d/%y")}
            <br> {conor}, {ari}, {laura}, {micah}
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
    # formatted_date = today.strftime("%d-%m-%Y")
    formatted_date = "15-10-2024"
    scrape.download(
        "Shazam Global Top 200 Genres / Hip-Hop",
        "https://www.shazam.com/charts/genre/world/hip-hop-rap",
        f"./download/Shazam Top 200 Hip-Hop_Rap {formatted_date}.csv",
    )

    scrape.download(
        "Shazam Global Top 200 Genres / Pop",
        "https://www.shazam.com/charts/genre/world/pop",
        f"./download/Shazam Top 200 Pop {formatted_date}.csv",
    )

    scrape.download(
        "Shazam Global Top 100 Genres / ALT",
        "https://www.shazam.com/charts/genre/world/alternative",
        f"./download/Shazam Top 100 Alternative {formatted_date}.csv",
    )

    scrape.download(
        "Shazam Global Top 100 Genres / R&B",
        "https://www.shazam.com/charts/genre/world/randb-soul",
        f"./download/Shazam Top 100 R&B_Soul {formatted_date}.csv",
    )

    scrape.download(
        "Shazam Global Top 100 Genres / Singer Songwriter",
        "https://www.shazam.com/charts/genre/world/singer-songwriter",
        f"./download/Shazam Top 50 Singer_Songwriter {formatted_date}.csv",
    )

    scrape.download(
        "Shazam Global Top 100 Genres / Country",
        "https://www.shazam.com/charts/genre/world/country",
        f"./download/Shazam Top 100 Country {formatted_date}.csv",
    )

    scrape.download(
        "Shazam Top 200 / Global",
        "https://www.shazam.com/charts/top-200/world",
        f"/Users/al/Desktop/L2TK.nosync/shazam_cities/csv/Shazam Top 200 Global Chart - The most Shazamed tracks in the world {formatted_date}.csv",
    )

    scrape.download(
        "Shazam Top 200 / US",
        "https://www.shazam.com/charts/top-200/united-states",
        f"/Users/al/Desktop/L2TK.nosync/shazam_cities/csv/Shazam Top 200 United States Chart {formatted_date}.csv",
    )

    scrape.download(
        "Shazam Top 200 / UK",
        "https://www.shazam.com/charts/top-200/united-kingdom",
        f"/Users/al/Desktop/L2TK.nosync/shazam_cities/csv/Shazam Top 200 United Kingdom Chart {formatted_date}.csv",
    )

    scrape.download(
        "Shazam Top 200 / CA",
        "https://www.shazam.com/charts/top-200/canada",
        f"/Users/al/Desktop/L2TK.nosync/shazam_cities/csv/Shazam Top 200 Canada Chart {formatted_date}.csv",
    )
    scrape.download(
        "Shazam US Top 100 Genres / Hip-Hop",
        "https://www.shazam.com/charts/genre/united-states/hip-hop-rap",
        f"/Users/al/Desktop/L2TK.nosync/shazam_cities/csv/Shazam Top 100 Hip-Hop_Rap {formatted_date}.csv",
    )

    scrape.download(
        "Shazam US Top 100 Genres / Pop",
        "https://www.shazam.com/charts/genre/united-states/pop",
        f"/Users/al/Desktop/L2TK.nosync/shazam_cities/csv/Shazam Top 100 Pop {formatted_date}.csv",
    )

    scrape.download(
        "Shazam US Top 100 Genres / Dance",
        "https://www.shazam.com/charts/genre/united-states/dance",
        f"/Users/al/Desktop/L2TK.nosync/shazam_cities/csv/Shazam Top 100 Dance {formatted_date}.csv",
    )

    scrape.download(
        "Shazam US Top 100 Genres / Country",
        "https://www.shazam.com/charts/genre/united-states/country",
        f"/Users/al/Desktop/L2TK.nosync/shazam_cities/csv/Shazam Top 100 Country {formatted_date}.csv",
    )

    scrape.driver.quit()


def scrape_all():
    download_dir = os.path.abspath("./download")

    prefs = {
        "download.default_directory": download_dir,
    }

    options = webdriver.ChromeOptions()
    options.add_experimental_option("prefs", prefs)
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

    options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(service=service, options=options)

    scrape = Scrape(driver)
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
    body = scrape.create_html("chart", "Shazam Chart Report", unsigned_charts)

    subject = f'Shazam Chart Report - {datetime.now(pacific_tz).strftime("%m/%d/%y")}'
    send_email_ses(subject, body)


def lambda_handler(event, context):
    scrape_all()
    return {
        "statusCode": 200,
        "body": "Scrape complete",
    }


# lambda_handler(None, None)
