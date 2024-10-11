from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time
from botocore.exceptions import ClientError
import pandas as pd
import os
import boto3
import datetime
from tempfile import mkdtemp
from selenium.common.exceptions import ElementClickInterceptedException


pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)
pd.set_option("display.colheader_justify", "center")
pd.set_option("display.precision", 3)

from db.get_db import FetchDB
from spotify_api import SpotifyAPI
from check import check_prod
from check import smart_partial_match

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID_L2TK")
USER_ID = os.getenv("SPOTIFY_USER_ID_L2TK")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET_L2TK")


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

    def genius(self, name, genre):
        genre()
        time.sleep(5)
        for i in range(0, 10):
            try:
                load_more = self.driver.find_element(
                    By.CLASS_NAME, "SquareButton-sc-109lda7-0"
                )
                load_more.click()
                time.sleep(3)
            except ElementClickInterceptedException:
                time.sleep(5)
                load_more = self.driver.find_element(
                    By.CLASS_NAME, "SquareButton-sc-109lda7-0"
                )
                load_more.click()
                time.sleep(3)

        rank = self.driver.find_elements(
            By.CLASS_NAME, "ChartItemdesktop__Rank-sc-3bmioe-1"
        )
        song = self.driver.find_elements(
            By.CLASS_NAME, "ChartSongdesktop__Title-sc-18658hh-3"
        )
        artist = self.driver.find_elements(
            By.CLASS_NAME, "ChartSongdesktop__Artist-sc-18658hh-5"
        )
        metadata = self.driver.find_elements(
            By.CLASS_NAME, "ChartSongdesktop__Metadata-sc-18658hh-6"
        )

        for idx, md in enumerate(metadata):
            r = rank[idx].text
            s = song[idx].text
            a = artist[idx].text

            if len(md.find_elements(By.XPATH, "./div")) > 1:
                views = md.find_element(By.XPATH, "./div[2]/div/span")
                if views.text:
                    v = views.text
                else:
                    no_views = md.find_element(By.XPATH, "./div[2]/div")
                    if no_views:
                        v = "<1k views / No data"

                    else:
                        v = md.text
                if ", " in a:
                    comma = a.split(", ")[0]
                    if list(
                        filter(
                            lambda x: (x.lower() == comma.lower()),
                            self.signed_artists + self.pub_artists,
                        )
                    ):
                        continue
                    else:
                        self.df.append((name, r, a, s, v, None, None, None))
                        print(f"{comma} not in signed")

                if " & " in a:
                    andpersand = a.split(" & ")[0]
                    if list(
                        filter(
                            lambda x: (x.lower() == andpersand.lower()),
                            self.signed_artists + self.pub_artists,
                        )
                    ):
                        continue
                    else:
                        self.df.append((name, r, a, s, v, None, None, None))
                        print(f"{andpersand} not in signed")

                else:
                    if not list(
                        filter(lambda x: (x.lower() == a.lower()), self.signed_artists)
                    ):
                        self.df.append((name, r, a, s, v, None, None, None))
                        print(f"{a} not in signed")

        def genius_scroll():
            from selenium.webdriver.common.action_chains import ActionChains

            element = self.driver.find_element(
                By.CLASS_NAME, "ChartSongdesktop__Title-sc-18658hh-3"
            )
            actions = ActionChains(self.driver)
            actions.move_to_element(element).perform()
            time.sleep(2)

        genius_scroll()

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


def genius_click(x):
    el = driver.find_element(By.XPATH, x)
    el.click()
    time.sleep(1)


def genius_all():
    genius_click('//*[@id="top-songs"]/div/div[1]/div[2]/div/div/div[1]/div')
    genius_click(
        '//*[@id="top-songs"]/div/div[1]/div[2]/div/div/div[2]/div[2]/div[2]/div'
    )


def genius_rap_hh():
    genius_click('//*[@id="top-songs"]/div/div[1]/div[2]/div/div/div[1]/div')
    genius_click(
        '//*[@id="top-songs"]/div/div[1]/div[2]/div/div/div[2]/div[2]/div[3]/div'
    )


def genius_pop():
    genius_click('//*[@id="top-songs"]/div/div[1]/div[2]/div/div/div[1]/div')
    genius_click(
        '//*[@id="top-songs"]/div/div[1]/div[2]/div/div/div[2]/div[2]/div[4]/div'
    )


def genius_rnb():
    genius_click('//*[@id="top-songs"]/div/div[1]/div[2]/div/div/div[1]/div')
    genius_click(
        '//*[@id="top-songs"]/div/div[1]/div[2]/div/div/div[2]/div[2]/div[5]/div'
    )


def genius_rock():
    genius_click('//*[@id="top-songs"]/div/div[1]/div[2]/div/div/div[1]/div')
    genius_click(
        '//*[@id="top-songs"]/div/div[1]/div[2]/div/div/div[2]/div[2]/div[6]/div'
    )


def genius_country():
    genius_click('//*[@id="top-songs"]/div/div[1]/div[2]/div/div/div[1]/div')
    genius_click(
        '//*[@id="top-songs"]/div/div[1]/div[2]/div/div/div[2]/div[2]/div[7]/div'
    )


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

    from selenium.webdriver.common.keys import Keys

    driver.get("https://genius.com/#top-songs")
    time.sleep(2)
    driver.refresh()
    time.sleep(2)
    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.CONTROL + Keys.HOME)
    time.sleep(2)
    scrape.genius("Genius Chart - Daily Trending Top 100: ALL GENRES", genius_all)
    scrape.genius("Genius Chart - Daily Trending Top 100: RAP", genius_rap_hh)
    scrape.genius("Genius Chart - Daily Trending Top 100: POP", genius_pop)
    scrape.genius("Genius Chart - Daily Trending Top 100: R&B", genius_rnb)
    scrape.genius("Genius Chart - Daily Trending Top 100: Rock", genius_rock)
    scrape.genius("Genius Chart - Daily Trending Top 100: Country", genius_country)

    driver.quit()

    genius_data = pd.DataFrame(
        scrape.df,
        columns=[
            "Chart",
            "Position",
            "Artist",
            "Song",
            "Streams",
            "Movement",
            "Days",
            "Date",
        ],
    )

    body = scrape.create_html("roster", "Spotify Roster Report")
    subject = f'Spotify Roster Report - {datetime.datetime.now().strftime("%m/%d/%y")}'
    send_email_ses(subject, body)

    body = scrape.create_html("chart", "Spotify Chart Report")
    subject = f'Spotify Chart Report - {datetime.datetime.now().strftime("%m/%d/%y")}'
    send_email_ses(subject, body)


def lambda_handler(event, context):
    scrape_all()
    return {
        "statusCode": 200,
        "body": "Scrape complete",
    }


lambda_handler(None, None)
