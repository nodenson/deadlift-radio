import random
from datetime import datetime, timedelta
from ..models import RawScoutItem

class MockProvider:
    name = "mock"

    CREATORS = [
        {"handle":"@steficohen","name":"Stefi Cohen","platform":"instagram","followers":1_200_000,"tags":["powerlifting","deadlift","strength","phd"]},
        {"handle":"@marksbell","name":"Mark Bell","platform":"youtube","followers":890_000,"tags":["powerlifting","bench","strength","slingshot"]},
        {"handle":"@bromontana","name":"Bro Montana","platform":"tiktok","followers":340_000,"tags":["deadlift","raw","strength","comedy"]},
        {"handle":"@alan_thrall","name":"Alan Thrall","platform":"youtube","followers":720_000,"tags":["barbell","technique","strength","teaching"]},
        {"handle":"@stronnigest","name":"Julia Vins","platform":"instagram","followers":2_100_000,"tags":["powerlifting","aesthetics","strength","women"]},
        {"handle":"@cbum","name":"Chris Bumstead","platform":"instagram","followers":8_400_000,"tags":["bodybuilding","classic","cbum","olympia"]},
        {"handle":"@nataliacorvino","name":"Natalia Corvino","platform":"tiktok","followers":560_000,"tags":["bodybuilding","women","prep","bikini"]},
        {"handle":"@nick_strength_power","name":"Nick Strength & Power","platform":"youtube","followers":780_000,"tags":["bodybuilding","natty","analysis"]},
        {"handle":"@gregdoucette","name":"Greg Doucette","platform":"youtube","followers":1_650_000,"tags":["bodybuilding","diet","cookbook","anabolic"]},
        {"handle":"@adamondra","name":"Adam Ondra","platform":"instagram","followers":1_100_000,"tags":["climbing","sport","elite","9c"]},
        {"handle":"@ashimaracing","name":"Ashima Shiraishi","platform":"instagram","followers":310_000,"tags":["climbing","bouldering","women","youth"]},
        {"handle":"@magnus_midtbo","name":"Magnus Midtbo","platform":"youtube","followers":2_300_000,"tags":["climbing","crossover","challenges","viral"]},
        {"handle":"@nathanielcolemanclimbing","name":"Nathaniel Coleman","platform":"instagram","followers":190_000,"tags":["climbing","bouldering","olympian"]},
        {"handle":"@alexhonnold","name":"Alex Honnold","platform":"instagram","followers":3_200_000,"tags":["climbing","free_solo","adventure"]},
        {"handle":"@hubermanlab","name":"Andrew Huberman","platform":"youtube","followers":6_100_000,"tags":["science","health","protocol","neuroscience"]},
        {"handle":"@peterattiamd","name":"Peter Attia","platform":"youtube","followers":920_000,"tags":["longevity","medicine","zone2","health"]},
        {"handle":"@davidgoggins","name":"David Goggins","platform":"instagram","followers":9_800_000,"tags":["mindset","ultra","military","suffering"]},
        {"handle":"@kneesovertoesguy","name":"Ben Patrick","platform":"tiktok","followers":1_400_000,"tags":["knees","rehab","atg","mobility"]},
        {"handle":"@mountaindog1","name":"John Meadows Legacy","platform":"instagram","followers":520_000,"tags":["bodybuilding","training","legacy","mountain_dog"]},
        {"handle":"@iamjohnmeadows","name":"John Meadows","platform":"youtube","followers":410_000,"tags":["bodybuilding","training","mountain_dog"]},
    ]

    TEMPLATES = [
        "New {tag} PR — here is what changed",
        "Why most people get {tag} wrong",
        "{tag} for beginners: the only guide",
        "6 weeks of {tag} — results and lessons",
        "I tested 3 {tag} methods so you do not have to",
        "The {tag} mistake that held me back for years",
        "Reacting to your {tag} form — episode {n}",
        "{tag} Q&A — your questions answered",
        "My full {tag} training week",
        "Why {tag} is the most underrated movement",
    ]

    def search(self, query, limit=20):
        keywords = [k.strip().lower() for k in query.replace(",", " ").split()]
        now = datetime.utcnow()

        scored = []
        for c in self.CREATORS:
            text = " ".join(c["tags"] + [c["name"].lower(), c["handle"].lower()])
            hits = sum(1 for kw in keywords if kw in text)
            scored.append((hits, c))
        scored.sort(key=lambda x: x[0], reverse=True)

        top = [c for _, c in scored if _ > 0]
        rest = [c for _, c in scored if _ == 0]
        random.shuffle(rest)
        pool = (top + rest)[:limit]

        items = []
        for creator in pool:
            tag = random.choice(creator["tags"])
            n = random.randint(1, 99)
            title = random.choice(self.TEMPLATES).format(tag=tag, n=n)
            days_ago = random.randint(0, 60)
            published = (now - timedelta(days=days_ago)).isoformat() + "Z"
            followers = creator["followers"]
            views = int(followers * random.uniform(0.02, 0.40))
            likes = int(views * random.uniform(0.04, 0.12))
            comments = int(likes * random.uniform(0.02, 0.08))
            items.append(RawScoutItem(
                source=creator["platform"],
                provider=self.name,
                creator_handle=creator["handle"],
                creator_name=creator["name"],
                content_title=title,
                content_url=f"https://{creator['platform']}.com/{creator['handle'].lstrip('@')}/p/{n}",
                content_description=f"{title}. Tags: {', '.join(creator['tags'])}",
                tags=creator["tags"],
                likes=likes, comments=comments, views=views, followers=followers,
                published_at=published,
                fetched_at=now.isoformat() + "Z",
                raw={"mock": True}
            ))
        return items
