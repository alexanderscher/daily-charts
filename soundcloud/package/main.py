import time
from selenium import webdriver
from tempfile import mkdtemp
from selenium.webdriver.common.by import By
import pandas as pd
import random
import time

pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)
pd.set_option("display.colheader_justify", "center")
pd.set_option("display.precision", 3)


def soundcloud(chart, url, driver):
    driver.get(url)
    time.sleep(10)

    for i in range(0, 4):
        random_scroll_height = random.randint(100, 500)
        driver.execute_script(
            f"window.scrollTo(0, document.body.scrollHeight - {random_scroll_height});"
        )
        random_sleep = random.uniform(2, 6)

        time.sleep(random_sleep)

    row = driver.find_elements(
        By.XPATH,
        '//*[@id="content"]/div/div[2]/div[1]/div/div[2]/div[2]/div/div[3]/div/ul/li',
    )
    print(len(row))


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

    soundcloud(
        "Soundcloud Top 50 / All music genres",
        "https://soundcloud.com/music-charts-us/sets/all-music-genres",
        driver,
    )
    soundcloud(
        "Soundcloud Top 50 / Hip-hop & Rap",
        "https://soundcloud.com/music-charts-us/sets/hip-hop",
        driver,
    )
    soundcloud(
        "Soundcloud Top 50 / R&B & Soul",
        "https://soundcloud.com/music-charts-us/sets/r-b",
        driver,
    )
    soundcloud(
        "Soundcloud Top 50 / Pop",
        "https://soundcloud.com/music-charts-us/sets/pop",
        driver,
    )

    soundcloud(
        "Soundcloud Top 50 / Rock",
        "https://soundcloud.com/music-charts-us/sets/rock",
        driver,
    )

    soundcloud(
        "Soundcloud Top 50 / Folk",
        "https://soundcloud.com/music-charts-us/sets/folk",
        driver,
    )

    soundcloud(
        "Soundcloud Top 50 / Country",
        "https://soundcloud.com/music-charts-us/sets/country",
        driver,
    )

    soundcloud(
        "Soundcloud Top 50 / New & hot",
        "https://soundcloud.com/music-charts-us/sets/new-hot",
        driver,
    )

    soundcloud(
        "Soundcloud Top 50 / Next Pro",
        "https://soundcloud.com/music-charts-us/sets/next-pro",
        driver,
    )


def lambda_handler(event, context):
    scrape_all()
    return {
        "statusCode": 200,
        "body": "Scrape complete",
    }


lambda_handler(None, None)
