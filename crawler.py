"""
crawler.py — Fetch RSS feeds, score articles for significance, extract images.
"""

import feedparser
import requests
import re
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

# ── Sources ────────────────────────────────────────────────────────────────────

FEEDS = [
    {"name": "Hacker News",           "url": "https://news.ycombinator.com/rss",                          "weight": 1.2},
    {"name": "VentureBeat AI",        "url": "https://venturebeat.com/category/ai/feed/",                 "weight": 1.5},
    {"name": "Ars Technica",          "url": "https://feeds.arstechnica.com/arstechnica/technology-lab",  "weight": 1.3},
    {"name": "The Register AI",       "url": "https://www.theregister.com/software/ai_ml/headlines.atom", "weight": 1.2},
    {"name": "MIT Tech Review",       "url": "https://www.technologyreview.com/feed/",                    "weight": 1.4},
    {"name": "Dev.to AI",             "url": "https://dev.to/feed/tag/ai",                                "weight": 1.0},
    {"name": "Dev.to Programming",    "url": "https://dev.to/feed/tag/programming",                       "weight": 1.0},
    {"name": "GitHub Blog",           "url": "https://github.blog/feed/",                                 "weight": 1.3},
    {"name": "Google Research",       "url": "https://blog.research.google/atom.xml",                     "weight": 1.5},
    {"name": "Reddit r/MachineLearning", "url": "https://www.reddit.com/r/MachineLearning/.rss",          "weight": 1.1},
    {"name": "Reddit r/LocalLLaMA",   "url": "https://www.reddit.com/r/LocalLLaMA/.rss",                  "weight": 1.1},
    {"name": "InfoQ",                 "url": "https://feed.infoq.com/",                                   "weight": 1.2},
    {"name": "Towards Data Science",  "url": "https://towardsdatascience.com/feed",                       "weight": 1.0},
    {"name": "Wired AI",              "url": "https://www.wired.com/feed/tag/artificial-intelligence/rss","weight": 1.3},
    {"name": "TechCrunch AI",         "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "weight": 1.4},
]

# ── Significance signals ────────────────────────────────────────────────────────

# These words in a title = high-signal "something new happened"
LAUNCH_WORDS = [
    "launch", "launches", "launched", "release", "releases", "released",
    "announce", "announces", "announced", "unveil", "unveils", "unveiled",
    "introduce", "introduces", "introduced", "debut", "debuts",
    "new ", "update", "upgrade", "open source", "open-source",
    "breakthrough", "first ", "beats", "surpasses", "outperforms",
    "acquires", "acquisition", "raises", "funding", "partnership",
    "ban", "bans", "regulation", "law", "policy", "lawsuit",
    "gpt", "claude", "gemini", "llama", "mistral", "stable diffusion",
    "model", "agent", "benchmark", "paper", "research",
    "system design", "architecture", "microservice", "kubernetes",
    "rust", "python", "typescript", "framework",
]

# Topics we care about
TOPIC_KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "deep learning",
    "llm", "large language model", "gpt", "claude", "gemini", "openai",
    "anthropic", "google deepmind", "meta ai", "apple intelligence",
    "transformer", "neural network", "diffusion", "generative",
    "agent", "rag", "fine-tuning", "inference", "training",
    "programming", "software", "developer", "open source",
    "system design", "distributed", "cloud", "api", "database",
    "github", "python", "javascript", "rust",
]

def is_significant(title: str, summary: str = "") -> bool:
    text = (title + " " + summary).lower()
    has_topic   = any(kw in text for kw in TOPIC_KEYWORDS)
    has_launch  = any(w in text  for w in LAUNCH_WORDS)
    return has_topic and has_launch

def score_article(title: str, summary: str, source_weight: float) -> float:
    text  = (title + " " + summary).lower()
    score = source_weight
    score += sum(0.3 for w in LAUNCH_WORDS   if w in text)
    score += sum(0.2 for w in TOPIC_KEYWORDS if w in text)
    # Recency bonus applied by caller
    return score

def clean_html(raw: str) -> str:
    return re.sub(r"<[^>]+>", "", raw or "").strip()

def try_fetch_image(url: str) -> str | None:
    """Try to extract the og:image from an article page."""
    try:
        r = requests.get(url, timeout=6,
                         headers={"User-Agent": "Mozilla/5.0 (compatible; NewsDigest/1.0)"})
        soup = BeautifulSoup(r.text, "html.parser")
        for attr in [("property", "og:image"), ("name", "twitter:image")]:
            tag = soup.find("meta", {attr[0]: attr[1]})
            if tag and tag.get("content", "").startswith("http"):
                return tag["content"]
    except Exception:
        pass
    return None

def parse_date(entry) -> datetime:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return datetime.now(timezone.utc)

# ── Main fetch ─────────────────────────────────────────────────────────────────

def fetch_all(top_n: int = 30, max_age_hours: int = 36) -> list[dict]:
    """
    Crawl all feeds, keep only significant & recent articles,
    return top_n scored by relevance.
    """
    cutoff   = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    articles = []
    seen_ids = set()

    for feed_meta in FEEDS:
        try:
            parsed = feedparser.parse(
                feed_meta["url"],
                agent="TechDigest/1.0",
                request_headers={"Accept": "application/rss+xml, application/atom+xml, */*"},
            )
            count = 0
            for entry in parsed.entries:
                title   = clean_html(getattr(entry, "title", ""))
                url     = getattr(entry, "link", "")
                summary = clean_html(getattr(entry, "summary", ""))[:600]
                pub     = parse_date(entry)

                if not title or not url:
                    continue

                uid = hashlib.sha1(url.encode()).hexdigest()[:12]
                if uid in seen_ids:
                    continue
                seen_ids.add(uid)

                if pub < cutoff:
                    continue
                if not is_significant(title, summary):
                    continue

                score = score_article(title, summary, feed_meta["weight"])
                # Recency bonus: more recent = higher score
                age_hours = (datetime.now(timezone.utc) - pub).total_seconds() / 3600
                score += max(0, (max_age_hours - age_hours) / max_age_hours) * 2

                articles.append({
                    "id":        uid,
                    "title":     title,
                    "url":       url,
                    "summary":   summary,
                    "source":    feed_meta["name"],
                    "published": pub.isoformat(),
                    "score":     round(score, 2),
                    "image":     None,
                })
                count += 1

            log.info("  %-30s → %d significant articles", feed_meta["name"], count)

        except Exception as exc:
            log.warning("  ⚠  %s — %s", feed_meta["name"], exc)

    # Sort by score, take top_n
    articles.sort(key=lambda a: a["score"], reverse=True)
    top = articles[:top_n]

    # Try to fetch images for top 6 articles (to keep it fast)
    log.info("Fetching images for top articles…")
    for a in top[:6]:
        img = try_fetch_image(a["url"])
        if img:
            a["image"] = img
            log.info("  🖼  %s", a["title"][:60])

    log.info("Total selected: %d articles from %d feeds", len(top), len(FEEDS))
    return top
