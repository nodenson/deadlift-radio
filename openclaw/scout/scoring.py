import math
from datetime import datetime, timezone
from .models import RawScoutItem, ScoreBreakdown, ScoredItem

DEFAULT_WEIGHTS = {
    "relevance": 0.30,
    "engagement": 0.25,
    "recency": 0.20,
    "creator_fit": 0.15,
    "collaboration_potential": 0.10,
}

RELEVANCE_KEYWORDS = [
    "deadlift","squat","bench","powerlifting","strength","barbell",
    "hypertrophy","bodybuilding","climbing","training","program",
    "pr","record","form","technique","raw","competition",
]

COLLAB_SIGNALS = [
    "deadlift","powerlifting","strength","barbell","raw","technique",
    "programming","training","coaching","meet","competition",
    "climbing","bouldering","crossover","athletic",
]

def _relevance(item, query):
    keywords = [k.strip().lower() for k in query.replace(",", " ").split() if k.strip()]
    text = " ".join([item.content_title, item.content_description,
                     " ".join(item.tags), item.creator_name]).lower()
    if not keywords:
        return 0.5
    q = sum(1 for kw in keywords if kw in text) / len(keywords)
    t = min(sum(1 for kw in RELEVANCE_KEYWORDS if kw in text) / 5, 1.0)
    score = q * 0.7 + t * 0.3
    # hard gate: if no query keywords match at all, cap at 0.15
    if q == 0.0:
        score = min(score, 0.15)
    return round(score, 4)

def _engagement(item):
    if item.followers == 0:
        return 0.0
    rate = (item.likes + item.comments) / item.followers
    return round(min(rate / 0.05, 1.0), 4)

def _recency(item):
    try:
        pub = datetime.fromisoformat(item.published_at.rstrip("Z")).replace(tzinfo=timezone.utc)
        days_old = (datetime.now(timezone.utc) - pub).total_seconds() / 86400
    except Exception:
        return 0.5
    return round(min(max(math.exp(-0.693 * days_old / 365), 0.0), 1.0), 4)

def _creator_fit(item):
    f = item.followers
    if f < 10_000: size = 0.2
    elif f < 50_000: size = 0.5
    elif f < 500_000: size = 1.0
    elif f < 2_000_000: size = 0.8
    else: size = 0.5
    platform = {"youtube":1.0,"instagram":0.85,"tiktok":0.70,"twitter":0.50,"podcast":1.0}.get(item.source.lower(), 0.5)
    return round(size * 0.6 + platform * 0.4, 4)

def _collab(item, query):
    text = " ".join([item.content_title, item.content_description, " ".join(item.tags)]).lower()
    sig = min(sum(1 for s in COLLAB_SIGNALS if s in text) / 4, 1.0)
    return round(min(sig * 0.6 + _engagement(item) * 0.2 + _creator_fit(item) * 0.2, 1.0), 4)

def score_items(items, query, run_id, weights=None):
    if weights is None:
        weights = DEFAULT_WEIGHTS
    scored = []
    for item in items:
        bd = ScoreBreakdown(
            relevance=_relevance(item, query),
            engagement=_engagement(item),
            recency=_recency(item),
            creator_fit=_creator_fit(item),
            collaboration_potential=_collab(item, query),
        )
        scored.append(ScoredItem(item=item, breakdown=bd,
                                  total_score=round(bd.weighted_total(weights), 4),
                                  query=query, run_id=run_id))
    scored.sort(key=lambda x: x.total_score, reverse=True)
    return scored
