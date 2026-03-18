from dataclasses import dataclass, field

@dataclass
class RawScoutItem:
    source: str
    provider: str
    creator_handle: str
    creator_name: str
    content_title: str
    content_url: str
    content_description: str
    tags: list
    likes: int
    comments: int
    views: int
    followers: int
    published_at: str
    fetched_at: str
    raw: dict = field(default_factory=dict)

@dataclass
class ScoreBreakdown:
    relevance: float = 0.0
    engagement: float = 0.0
    recency: float = 0.0
    creator_fit: float = 0.0
    collaboration_potential: float = 0.0

    def weighted_total(self, weights):
        return (
            self.relevance * weights.get("relevance", 0.25) +
            self.engagement * weights.get("engagement", 0.25) +
            self.recency * weights.get("recency", 0.20) +
            self.creator_fit * weights.get("creator_fit", 0.15) +
            self.collaboration_potential * weights.get("collaboration_potential", 0.15)
        )

@dataclass
class ScoredItem:
    item: RawScoutItem
    breakdown: ScoreBreakdown
    total_score: float
    query: str
    run_id: str

@dataclass
class CreatorProfile:
    handle: str
    name: str
    platform: str
    followers: int
    total_appearances: int
    avg_score: float
    best_score: float
    top_tags: list
    last_seen: str
    first_seen: str
    run_ids: list

@dataclass
class IntelligenceReport:
    run_id: str
    query: str
    provider: str
    generated_at: str
    total_items: int
    top_items: list
    creator_profiles: list
    dominant_tags: list
    platform_spread: dict
    recommendations: list
