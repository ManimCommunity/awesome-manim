import os
import re
import feedparser

# from pathlib import Path
import time
import requests
import json
from dotenv import load_dotenv
from datetime import datetime
from flask import Flask, request
from flask_cors import CORS, cross_origin
from supabase import create_client, Client

from helper import get_youtube_channel_id_from_custom_name

CRAWL_DELAY = 5
SECONDS_IN_DAY = 24 * 60 * 60
README_URL = (
    "https://raw.githubusercontent.com/ManimCommunity/awesome-manim/main/README.md"
)
# LAST_UPDATED = 0
# CURRENTLY_CRAWLING = False
# ENTRIES = []
VIDEOS_PER_PAGE = 30
TMP_FILE = "/tmp/data.json"

load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)


def now():
    return datetime.utcnow().timestamp()


def get_data():
    if os.path.exists(TMP_FILE):
        return json.loads(open(TMP_FILE, "r").read())
    else:
        return {"last_updated": 0, "currently_crawling": False, "entries": []}


def save_data(data):
    return open(TMP_FILE, "w").write(json.dumps(data))


def is_manim_video(entry):
    try:
        check_str = entry["title"] + " " + entry["summary"]
        return (
            "manim" in check_str.lower()
            or "#some" in check_str.lower()
            or "SoME" in check_str
        )
    except:
        return False


def update_entries():
    # Get the README content
    # readme_path = Path(__file__).parent.parent.joinpath(Path("README.md")).absolute()
    # content = open(readme_path, "r").read()

    response = requests.get(README_URL)
    content = response.text

    # Get channel URLs from the content
    channel_ids = []
    channel_custom_names = []
    # channel_ids.extend(re.findall(r"https://www.youtube.com/channel/[0-9a-zA-Z_-]+", content))
    channel_ids.extend(
        re.findall(r"(?<=https://www.youtube.com/channel/)[0-9a-zA-Z_-]+", content)
    )
    channel_custom_names.extend(
        re.findall(r"(?<=https://www.youtube.com/c/)[0-9a-zA-Z_-]+", content)
    )

    for channel_custom_name in channel_custom_names:
        try:
            channel_id = get_youtube_channel_id_from_custom_name(channel_custom_name)
            if channel_id:
                channel_ids.append(channel_id)
                print("Channel ID for", channel_custom_name, "=", channel_id)
            else:
                print("Could not get the channel ID for", channel_custom_name)
        except:
            print("Could not get the channel ID for", channel_custom_name)

        time.sleep(CRAWL_DELAY)

    new_entries = []
    for id in channel_ids:
        feed_url = "https://www.youtube.com/feeds/videos.xml?channel_id=" + id
        print("Crawling", feed_url)
        feed = feedparser.parse(feed_url)
        new_entries.extend(feed["entries"])
        # import ipdb; ipdb.set_trace()
        time.sleep(CRAWL_DELAY)

    rows = []
    for entry in new_entries:
        rows.append(
            {
                "yt_videoid": entry["yt_videoid"],
                "link": entry["link"],
                "author": entry["author"],
                "yt_channelid": entry["yt_channelid"],
                "title": entry["title"],
                "published": entry["published"],
                "updated": entry["updated"],
                "thumbnail_url": entry["media_thumbnail"][0]["url"],
                "summary": entry["summary"],
                "view_count": entry["media_statistics"]["views"],
                "like_count": entry["media_starrating"]["count"],
                "json": entry,
                "is_manim_video": is_manim_video(entry),
            }
        )

    for row in rows:
        try:
            supabase.table("video").upsert(row, ignore_duplicates=True).execute()
        except:
            try:
                yt_videoid = row["yt_videoid"]
                del row["yt_videoid"]
                supabase.table("video").update(row).eq(
                    "yt_videoid", yt_videoid
                ).execute()
            except:
                pass
    # supabase.table("video").upsert(rows, ignore_duplicates=True).execute()

    # data["entries"] = new_entries
    # data["currently_crawling"] = False
    # data["last_updated"] = now()
    return None


app = Flask(__name__)
cors = CORS(app)
app.config["CORS_HEADERS"] = "Content-Type"


@app.route("/videos/<int:page_id>")
@cross_origin()
def videos(page_id: int):
    if page_id <= 0:
        return "[]"
    rows = (
        supabase.table("video")
        .select("*")
        .eq("is_manim_video", True)
        .order("published", desc=True)
        .range((page_id - 1) * VIDEOS_PER_PAGE, page_id * VIDEOS_PER_PAGE)
        .execute()
    )
    return rows.json()


@app.route("/update")
def update():
    if "X-Appengine-Cron" in request.headers:
        if request.headers["X-Appengine-Cron"] == "true":
            update_entries()
            return "Update complete", 200

    return "Forbidden", 403


if __name__ == "__main__":
    # update_entries()
    app.run(debug=True, port=3001)
# import ipdb; ipdb.set_trace()
