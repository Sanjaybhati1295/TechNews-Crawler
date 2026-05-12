#!/usr/bin/env python3
"""
Daily AI & Programming News Crawler
Pulls from free RSS feeds, filters by relevance, stores in SQLite + JSON.
"""

import feedparser
import sqlite3
import json
import os
import re
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

OUTPUT_DIR = Path("output")
DB_PATH    = OUTPUT_DIR / "news.db"
JSON_PATH  = OUTPUT_DIR / "latest.json"
LOG_PATH   = OUTPUT_DIR / "run.log"

# Keywords that mark an article as relevant
KEYWORDS = [
    # AI / ML
    "artificial intelligence", "machine learning", "deep learning", "neural network",
    "large language model", "llm", "gpt", "claude", "gemini", "openai", "anthropic",
    "transformer", "diffusion model", "generative ai", "rag", "fine-tuning",
    "reinforcement learning", "computer vision", "nlp", "natural language",
    "ai agent", "multimodal", "foundation model",
    # Programming / Tech
    "programming", "python", "javascript", "typescript", "rust", "golang", "cpp",
    "software engineering", "open source", "github", "developer", "api",
    "framework", "library", "compiler", "debugging", "architecture",
    "kubernetes", "docker", "devops", "cloud", "serverless",
    "web assembly", "wasm", "llvm", "database", "postgresql",
]

# Free RSS feeds — no API keys required
FEEDS = [
    # Hacker News (top stories)
    {
        "name": "Hacker News",
        "url": "https://news.ycombinator.com/rss",
        "category": "community",
    },
    # Dev.to
    {
        "name": "Dev.to – AI",
        "url": "https://dev.to/feed/tag/ai",
        "category": "programming",
    },
    {
        "name": "Dev.to – Machine Learning",
        "url": "https://dev.to/feed/tag/machinelearning",
        "category": "ai",
    },
    {
        "name": "Dev.to – Programming",
        "url": "https://dev.to/feed/tag/programming",
        "category": "programming",
    },
    # MIT Technology Review
    {
        "name": "MIT Technology Review – AI",
        "url": "https://www.technologyreview.com/feed/",
        "category": "research",
    },
    # Ars Technica
    {
        "name": "Ars Technica – Technology",
        "url": "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "category": "tech",
    },
    {
        "name": "Ars Technica – AI",
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "category": "tech",
    },
    # The Register
    {
        "name": "The Register – AI",
        "url": "https://www.theregister.com/software/ai_ml/headlines.atom",
        "category": "tech",
    },
    # VentureBeat AI
    {
        "name": "VentureBeat – AI",
        "url": "https://venturebeat.com/category/ai/feed/",
        "category": "ai",
    },
    # InfoQ
    {
        "name": "InfoQ – AI/ML",
        "url": "https://feed.infoq.com/",
        "category": "engineering",
    },
    # Reddit – machine learning (JSON feed)
    {
        "name": "Reddit – r/MachineLearning",
        "url": "https://www.reddit.com/r/MachineLearning/.rss",
        "category": "community",
    },
    {
        "name": "Reddit – r/LocalLLaMA",
        "url": "https://www.reddit.com/r/LocalLLaMA/.rss",
        "category": "ai",
    },
    {
        "name": "Reddit – r/programming",
        "url": "https://www.reddit.com/r/programming/.rss",
        "category": "programming",
    },
    # GitHub blog
    {
        "name": "GitHub Blog",
        "url": "https://github.blog/feed/",
        "category": "engineering",
    },
    # Google AI Blog
    {
        "name": "Google Research Blog",
        "url": "https://blog.research.google/atom.xml",
        "category": "research",
    },
    # Towards Data Science (Medium)
    {
        "name": "Towards Data Science",
        "url": "https://towardsdatascience.com/feed",
        "category": "data science",
    },
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def setup_logging():
    OUTPUT_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH),
            logging.StreamHandler(),
        ],
    )

def make_id(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()[:16]

def is_relevant(title: str, summary: str = "") -> bool:
    text = (title + " " + summary).lower()
    return any(kw in text for kw in KEYWORDS)

def clean_html(raw: str) -> str:
    return re.sub(r"<[^>]+>", "", raw or "").strip()[:500]

def parse_date(entry) -> str:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc).isoformat()
            except Exception:
                pass
    return datetime.now(timezone.utc).isoformat()

# ── Database ──────────────────────────────────────────────────────────────────

def init_db(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            url         TEXT NOT NULL,
            summary     TEXT,
            source      TEXT,
            category    TEXT,
            published   TEXT,
            fetched_at  TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_published ON articles(published DESC)")
    conn.commit()

def upsert_article(conn: sqlite3.Connection, article: dict):
    conn.execute("""
        INSERT OR IGNORE INTO articles
            (id, title, url, summary, source, category, published, fetched_at)
        VALUES
            (:id, :title, :url, :summary, :source, :category, :published, :fetched_at)
    """, article)

# ── Core fetch logic ──────────────────────────────────────────────────────────

def fetch_feed(feed_meta: dict) -> list[dict]:
    log = logging.getLogger(__name__)
    articles = []
    try:
        parsed = feedparser.parse(
            feed_meta["url"],
            agent="TechNewsCrawler/1.0 (educational project)",
            request_headers={"Accept": "application/rss+xml, application/atom+xml, */*"},
        )
        if parsed.bozo and not parsed.entries:
            log.warning("  ⚠  %s — feed parse error: %s", feed_meta["name"], parsed.bozo_exception)
            return []

        for entry in parsed.entries:
            title   = clean_html(getattr(entry, "title", ""))
            url     = getattr(entry, "link", "")
            summary = clean_html(getattr(entry, "summary", ""))

            if not title or not url:
                continue
            if not is_relevant(title, summary):
                continue

            articles.append({
                "id":         make_id(url),
                "title":      title,
                "url":        url,
                "summary":    summary,
                "source":     feed_meta["name"],
                "category":   feed_meta["category"],
                "published":  parse_date(entry),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            })

        log.info("  ✓  %-35s → %d relevant / %d total",
                 feed_meta["name"], len(articles), len(parsed.entries))
    except Exception as exc:
        log.error("  ✗  %s — %s", feed_meta["name"], exc)

    return articles

# ── Export ────────────────────────────────────────────────────────────────────

def export_json(conn: sqlite3.Connection, limit: int = 200):
    rows = conn.execute("""
        SELECT id, title, url, summary, source, category, published, fetched_at
        FROM   articles
        ORDER  BY published DESC
        LIMIT  ?
    """, (limit,)).fetchall()

    cols = ["id", "title", "url", "summary", "source", "category", "published", "fetched_at"]
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(rows),
        "articles": [dict(zip(cols, r)) for r in rows],
    }
    JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    logging.getLogger(__name__).info("Exported %d articles → %s", len(rows), JSON_PATH)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    setup_logging()
    log = logging.getLogger(__name__)
    log.info("=" * 60)
    log.info("Tech News Crawler — %s", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    log.info("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    total_new = 0
    for feed in FEEDS:
        articles = fetch_feed(feed)
        for a in articles:
            cur = conn.execute("SELECT id FROM articles WHERE id = ?", (a["id"],))
            if not cur.fetchone():
                upsert_article(conn, a)
                total_new += 1

    conn.commit()
    log.info("─" * 60)
    log.info("New articles saved: %d", total_new)

    export_json(conn)
    conn.close()
    log.info("Done.")

if __name__ == "__main__":
    main()
