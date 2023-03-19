import argparse
import datetime as dt
import os
from io import BytesIO
from time import sleep

import requests
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# twitter API token
bearer_token = os.environ.get("BEARER_TOKEN")

# num seconds to sleep before taking screenshot of tweet
TWEET_LOAD_TIME_SECONDS = 1


def create_url(user_id: int) -> str:
    """build request url for user"""
    return f"https://api.twitter.com/2/users/{user_id}/tweets"


def get_params(start_date: str, max_results=100) -> dict:
    """build params dict for tweet request"""
    return {
        "tweet.fields": "created_at",
        "start_time": start_date + "T00:00:01Z",
        "max_results": max_results,
    }


def bearer_oauth(r: requests.Request) -> requests.Request:
    """Adds auth headers to r."""
    r.headers["Authorization"] = f"Bearer {bearer_token}"
    r.headers["User-Agent"] = "v2UserTweetsPython"
    return r


def get_tweets(url: str, params: dict) -> list:
    """exhaustively returns all tweets with tweet request url and params"""
    page_count = 0
    next_token = None
    all_res = []
    while page_count == 0 or next_token is not None:
        page_count += 1
        params["pagination_token"] = next_token
        response = requests.request("GET", url, auth=bearer_oauth, params=params)
        if response.status_code != 200:
            raise Exception(
                "Request returned an error: {} {}".format(
                    response.status_code, response.text
                )
            )
        res = response.json()
        next_token = res["meta"].get("next_token")  # type:ignore
        tweets = [(d["id"], d["created_at"]) for d in res["data"]]
        all_res.extend(tweets)

    return all_res


def save_mobile_screenshot(
    tweet_id: str, created_time: str, driver: WebDriver, save_path: str
) -> None:
    """loads tweet in mobile format and save image screenshot to `save_path`"""

    url = f"https://twitter.com/EBLAeast/status/{tweet_id}"

    html_content = f"""
    <blockquote class="twitter-tweet" style="width: 400px;" data-dnt="true">
    <p lang="en" dir="ltr"></p>

    <a href="{url}"></a>

    </blockquote> <script async src="https://platform.twitter.com/widgets.js"
        charset="utf-8"></script>
    """
    driver.get(f"data:text/html;charset=utf-8, {html_content}")
    # sleep for enough time for tweet to load
    sleep(TWEET_LOAD_TIME_SECONDS)
    e = driver.find_element(By.CLASS_NAME, "twitter-tweet")

    with BytesIO(b"") as bottom:
        p = e.screenshot_as_png
        bottom.write(p)

        img = Image.open(bottom)
        img.save(f"{save_path}/{created_time}.png")


def main():
    parser = argparse.ArgumentParser(
        prog="tweet_screeshotter",
        description="scrape user tweets from a start date to now and save screenshots",
    )
    parser.add_argument("user_id", help="user id to scrape tweets from")
    parser.add_argument("start_date", help="date to start scraping tweets from")
    parser.add_argument(
        "img_path",
        help="path of folder to save tweet screenshots into, folder must exist already!",
    )
    args = parser.parse_args()
    user_id = args.user_id
    start_date = args.start_date
    img_path = args.img_path

    print(f"grabbing all tweets from {start_date} to {str(dt.datetime.now().date())}")
    # instantiate and install chrome driver if needed
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

    url = create_url(user_id)
    params = get_params(start_date, max_results=100)
    tweets = get_tweets(url, params)

    num_tweets = len(tweets)

    print(f"found {num_tweets} tweets in total")
    print(f"rendering and saving screenshots to {img_path}")

    # load each tweet and save a screenshot in img_path
    for idx, (id, created_at) in enumerate(tweets):
        print(f"{idx+1}/{num_tweets}")
        save_mobile_screenshot(id, created_at, driver, save_path=img_path)


if __name__ == "__main__":
    main()
