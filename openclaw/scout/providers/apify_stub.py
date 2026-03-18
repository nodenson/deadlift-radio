import os
from datetime import datetime, timezone
from ..models import RawScoutItem

class ApifyStubProvider:
    name = "apify"
    def __init__(self, token=None, platform="instagram"):
        self.token = token or os.environ.get("APIFY_API_TOKEN", "")
        self.platform = platform
    def search(self, query, limit=20):
        if not self.token:
            raise RuntimeError("APIFY_API_TOKEN not set. Use MockProvider for dev.")
        raise NotImplementedError("Wire up live Apify calls here")
    def _normalize(self, raw, platform):
        now = datetime.now(timezone.utc).isoformat() + "Z"
        if platform == "instagram":
            return RawScoutItem(
                source="instagram", provider=self.name,
                creator_handle=raw.get("ownerUsername",""),
                creator_name=raw.get("ownerFullName", raw.get("ownerUsername","")),
                content_title=raw.get("caption","")[:120],
                content_url=raw.get("url",""),
                content_description=raw.get("caption",""),
                tags=raw.get("hashtags",[]),
                likes=raw.get("likesCount",0), comments=raw.get("commentsCount",0),
                views=raw.get("videoViewCount",0), followers=raw.get("ownerFollowersCount",0),
                published_at=raw.get("timestamp",now), fetched_at=now, raw=raw,
            )
        raise ValueError(f"Unknown platform: {platform}")

class MCPStubProvider:
    name = "mcp"
    def search(self, query, limit=20):
        raise NotImplementedError("MCPStubProvider not yet implemented")
