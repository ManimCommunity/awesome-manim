import re
import os
from youtube_search import Service
from dotenv import load_dotenv
load_dotenv()


def extract_channel_id_from_rss_link(str):
    return re.findall(
        r"(?<=https://www.youtube.com/feeds/videos.xml\?channel_id=)[0-9a-zA-Z_-]+", str
    )


def extract_channel_id_from_channel_url(str):
    return re.findall(r"(?<=https://www.youtube.com/channel/)[0-9a-zA-Z_-]+", str)


def get_youtube_channel_id_from_custom_name(name):
    service = Service(
        10,
        os.getenv('YOUTUBE_DATA_APP_KEY'))
    return service.find_channel_by_custom_url(name)
