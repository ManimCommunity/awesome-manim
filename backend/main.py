import os
import re
import feedparser
# from pathlib import Path
from datetime import datetime
import time
import requests
from flask import Flask
import json


CRAWL_DELAY = 5
SECONDS_IN_DAY = 24 * 60 * 60
README_URL = (
    "https://raw.githubusercontent.com/ManimCommunity/awesome-manim/main/README.md"
)
# LAST_UPDATED = 0
# CURRENTLY_CRAWLING = False
# ENTRIES = []
TMP_FILE = "/tmp/data.json"


def now():
    return datetime.utcnow().timestamp()


def get_data():
    if os.path.exists(TMP_FILE):
        return json.loads(open(TMP_FILE, "r").read())
    else:
        return {"last_updated":0, "currently_crawling": False, "entries": []}


def save_data(data):
    return open(TMP_FILE, "w").write(json.dumps(data))


def update_entries(data):
    # Get the README content
    # readme_path = Path(__file__).parent.parent.joinpath(Path("README.md")).absolute()
    # content = open(readme_path, "r").read()

    response = requests.get(README_URL)
    content = response.text

    # Get channel URLs from the content
    channel_ids = []
    # channel_ids.extend(re.findall(r"https://www.youtube.com/channel/[0-9a-zA-Z_-]+", content))
    # channel_ids.extend(re.findall(r"https://www.youtube.com/c/[0-9a-zA-Z_-]+", content))
    channel_ids.extend(
        re.findall(r"(?<=https://www.youtube.com/channel/)[0-9a-zA-Z_-]+", content)
    )

    new_entries = []
    for id in channel_ids:
        feed_url = "https://www.youtube.com/feeds/videos.xml?channel_id=" + id
        print("Crawling", feed_url)
        feed = feedparser.parse(feed_url)
        new_entries.extend(feed["entries"])
        # import ipdb; ipdb.set_trace()
        time.sleep(CRAWL_DELAY)

    data["entries"] = new_entries
    data["currently_crawling"] = False
    data["last_updated"] = now()
    return data

app = Flask(__name__)


@app.route("/")
def main():
    data = get_data()
    return json.dumps(data["entries"])


@app.route("/update")
def update():
    # global CURRENTLY_CRAWLING, LAST_UPDATED
    data = get_data()
    if not data["currently_crawling"] and now() > data["last_updated"] + SECONDS_IN_DAY:
        data["currently_crawling"] = True
        save_data(data)
        try:
            data = update_entries(data)
            save_data(data)
        except:
            data["currently_crawling"] = False
            save_data(data)
            return "There was a problem with the update"

        return "Update complete"
    else:
        return "Already up-to-date"


if __name__ == "__main__":
    app.run(debug=True, port=3001)
# import ipdb; ipdb.set_trace()
