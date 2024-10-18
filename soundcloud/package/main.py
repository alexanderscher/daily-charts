from botocore.exceptions import ClientError
import pandas as pd
from selenium import webdriver
from tempfile import mkdtemp
import time
from selenium.webdriver.common.by import By

pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)
pd.set_option("display.colheader_justify", "center")
pd.set_option("display.precision", 3)


def soundcloud(self, url, driver):
    driver.get(url)
    time.sleep(10)

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(6)

    row = driver.find_elements(
        By.XPATH,
        '//*[@id="content"]/div/div[2]/div[1]/div/div[2]/div[2]/div/div[3]/div/ul/li',
    )
    print(len(row))


def lambda_handler(event, context):
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

    soundcloud("https://soundcloud.com/trending-music-us/sets/soundcloud-1", driver)
    soundcloud("https://soundcloud.com/trending-music-us/sets/pop-1", driver)
    soundcloud("https://soundcloud.com/trending-music-us/sets/hip-hop-rap", driver)
    soundcloud("https://soundcloud.com/trending-music-us/sets/r-b-1", driver)
