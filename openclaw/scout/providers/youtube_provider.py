import os
import requests
from datetime import datetime, timezone
from ..models import RawScoutItem


class YouTubeProvider:
    name = "youtube"
    BASE_URL = "https://www.googleapis.com/youtube/v3"

    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("YOUTUBE_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("YOUTUBE_API_KEY not set.")

    def search(self, query, limit=20):
        # Step 1: search for videos
        search_resp = requests.get(f"{self.BASE_URL}/search", params={
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": min(limit, 50),
            "order": "relevance",
            "key": self.api_key,
        }).json()

        if "error" in search_resp:
            raise RuntimeError(f"YouTube API error: {search_resp['error']['message']}")

        items = search_resp.get("items", [])
        if not items:
            return []

        # Step 2: get video stats (likes, views, comments)
        video_ids = [i["id"]["videoId"] for i in items]
        stats_resp = requests.get(f"{self.BASE_URL}/videos", params={
            "part": "statistics,snippet",
            "id": ",".join(video_ids),
            "key": self.api_key,
        }).json()

        stats_map = {
            v["id"]: v for v in stats_resp.get("items", [])
        }

        # Step 3: get channel stats (subscriber count)
        channel_ids = list({i["snippet"]["channelId"] for i in items})
        channel_resp = requests.get(f"{self.BASE_URL}/channels", params={
            "part": "statistics,snippet",
            "id": ",".join(channel_ids),
            "key": self.api_key,
        }).json()

        channel_map = {
            c["id"]: c for c in channel_resp.get("items", [])
        }

        now = datetime.now(timezone.utc).isoformat() + "Z"
        results = []

        for item in items:
            snippet = item["snippet"]
            video_id = item["id"]["videoId"]
            channel_id = snippet["channelId"]

            video_data = stats_map.get(video_id, {})
            channel_data = channel_map.get(channel_id, {})

            vstats = video_data.get("statistics", {})
            cstats = channel_data.get("statistics", {})

            title = snippet.get("title", "")
            description = snippet.get("description", "")
            channel_name = snippet.get("channelTitle", "")
            published_at = snippet.get("publishedAt", now)

            # extract tags from video snippet if available
            tags = video_data.get("snippet", {}).get("tags", [])
            if not tags:
                # fallback: pull keywords from title
                tags = [w.lower() for w in title.replace(",", "").split()
                        if len(w) > 4][:8]

            results.append(RawScoutItem(
                source="youtube",
                provider=self.name,
                creator_handle=f"@{channel_name.lower().replace(' ', '')}",
                creator_name=channel_name,
                content_title=title,
                content_url=f"https://youtube.com/watch?v={video_id}",
                content_description=description,
                tags=tags,
                likes=int(vstats.get("likeCount", 0)),
                comments=int(vstats.get("commentCount", 0)),
                views=int(vstats.get("viewCount", 0)),
                followers=int(cstats.get("subscriberCount", 0)),
                published_at=published_at,
                fetched_at=now,
                raw={
                    "video_id": video_id,
                    "channel_id": channel_id,
                    "channel_url": "https://youtube.com/@" + channel_name.lower().replace(" ", "-"),
                    "snippet": snippet,
                    "vstats": vstats,
                    "cstats": cstats,
                },
            ))
        return results
