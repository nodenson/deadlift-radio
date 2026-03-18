import json
from collections import Counter
from datetime import datetime, timezone
from .models import ScoredItem, CreatorProfile, IntelligenceReport

def _aggregate_creators(scored_items, run_id):
    groups = {}
    for si in scored_items:
        key = (si.item.creator_handle, si.item.source)
        groups.setdefault(key, []).append(si)
    profiles = []
    for (handle, platform), items in groups.items():
        scores = [i.total_score for i in items]
        all_tags = [t for i in items for t in i.item.tags]
        top_tags = [t for t, _ in Counter(all_tags).most_common(5)]
        dates = sorted([i.item.published_at for i in items])
        profiles.append(CreatorProfile(
            handle=handle, name=items[0].item.creator_name,
            platform=platform, followers=items[0].item.followers,
            total_appearances=len(items),
            avg_score=round(sum(scores)/len(scores), 4),
            best_score=round(max(scores), 4),
            top_tags=top_tags,
            first_seen=dates[0] if dates else "",
            last_seen=dates[-1] if dates else "",
            run_ids=[run_id],
        ))
    profiles.sort(key=lambda p: p.avg_score, reverse=True)
    return profiles

def _dominant_tags(scored_items, top_n=10):
    all_tags = [t for si in scored_items for t in si.item.tags]
    return [t for t, _ in Counter(all_tags).most_common(top_n)]

def _platform_spread(scored_items):
    counts = {}
    for si in scored_items:
        counts[si.item.source] = counts.get(si.item.source, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

def _recommendations(scored_items, profiles):
    recs = []
    if profiles:
        p = profiles[0]
        recs.append(f"Priority outreach: {p.name} ({p.handle}) -- avg {p.avg_score:.2f}, {p.followers:,} followers on {p.platform}")
    high_collab = list({si.item.creator_name for si in scored_items if si.breakdown.collaboration_potential > 0.7})[:3]
    if high_collab:
        recs.append(f"High collab potential: {', '.join(high_collab)}")
    high_eng = list({si.item.creator_name for si in scored_items if si.breakdown.engagement > 0.6})[:3]
    if high_eng:
        recs.append(f"Strong engagement signal: {', '.join(high_eng)}")
    yt = [si for si in scored_items if si.item.source == "youtube"]
    if yt:
        recs.append(f"{len(yt)} YouTube results -- prioritize for long-form collaboration")
    if not recs:
        recs.append("Broaden query terms to surface more results")
    return recs

def build_report(run_id, query, provider, scored_items, top_n=10):
    now = datetime.now(timezone.utc).isoformat()
    profiles = _aggregate_creators(scored_items, run_id)
    return IntelligenceReport(
        run_id=run_id, query=query, provider=provider,
        generated_at=now, total_items=len(scored_items),
        top_items=scored_items[:top_n],
        creator_profiles=profiles,
        dominant_tags=_dominant_tags(scored_items),
        platform_spread=_platform_spread(scored_items),
        recommendations=_recommendations(scored_items, profiles),
    )

def report_to_dict(report):
    def item_dict(si):
        return {
            "creator_handle": si.item.creator_handle,
            "creator_name": si.item.creator_name,
            "platform": si.item.source,
            "content_title": si.item.content_title,
            "content_url": si.item.content_url,
            "score_total": si.total_score,
            "score_breakdown": {
                "relevance": si.breakdown.relevance,
                "engagement": si.breakdown.engagement,
                "recency": si.breakdown.recency,
                "creator_fit": si.breakdown.creator_fit,
                "collaboration_potential": si.breakdown.collaboration_potential,
            },
            "tags": si.item.tags,
            "followers": si.item.followers,
            "published_at": si.item.published_at,
        }
    return {
        "run_id": report.run_id, "query": report.query,
        "provider": report.provider, "generated_at": report.generated_at,
        "total_items": report.total_items,
        "dominant_tags": report.dominant_tags,
        "platform_spread": report.platform_spread,
        "recommendations": report.recommendations,
        "top_items": [item_dict(si) for si in report.top_items],
        "creator_profiles": [
            {"handle":p.handle,"name":p.name,"platform":p.platform,
             "followers":p.followers,"total_appearances":p.total_appearances,
             "avg_score":p.avg_score,"best_score":p.best_score,
             "top_tags":p.top_tags,"last_seen":p.last_seen}
            for p in report.creator_profiles
        ],
    }

def format_brief(report):
    lines = [
        "=" * 60,
        "OPENCLAW INTELLIGENCE BRIEF",
        f"Run:       {report.run_id}",
        f"Query:     {report.query}",
        f"Provider:  {report.provider}",
        f"Generated: {report.generated_at}",
        f"Items:     {report.total_items}",
        "=" * 60,
        "",
        "-- TOP CREATORS --",
    ]
    for p in report.creator_profiles[:5]:
        lines.append(f"  {p.handle} ({p.platform}) | score: {p.avg_score:.2f} | {p.followers:,} followers | {', '.join(p.top_tags[:3])}")
    lines += ["", "-- TOP CONTENT --"]
    for si in report.top_items[:5]:
        lines.append(f"  [{si.total_score:.2f}] {si.item.creator_name}: {si.item.content_title}")
    lines += ["", "-- PLATFORM SPREAD --"]
    for platform, count in report.platform_spread.items():
        lines.append(f"  {platform}: {count}")
    lines += ["", "-- DOMINANT TAGS --"]
    lines.append("  " + ", ".join(report.dominant_tags))
    lines += ["", "-- RECOMMENDATIONS --"]
    for rec in report.recommendations:
        lines.append(f"  -> {rec}")
    lines += ["", "=" * 60]
    return "\n".join(lines)
