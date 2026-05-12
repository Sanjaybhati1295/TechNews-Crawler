#!/usr/bin/env python3
"""
main.py — Daily AI & Tech Digest Generator

1. Crawls 15+ RSS feeds
2. Filters for significant/new stories only
3. Calls Groq LLM to write a cohesive daily brief
4. Renders a beautiful HTML digest page

Usage:
    python main.py

Environment variables:
    GROQ_API_KEY   — your free Groq API key (get one at console.groq.com)
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from crawler   import fetch_all
from summarizer import generate_digest
from renderer  import render_digest

OUTPUT_DIR = Path("output")

def setup_logging():
    OUTPUT_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s %(message)s",
        handlers=[
            logging.FileHandler(OUTPUT_DIR / "run.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )

def main():
    setup_logging()
    log = logging.getLogger(__name__)

    today = datetime.now(timezone.utc)
    log.info("=" * 60)
    log.info("TECHPULSE Digest — %s", today.strftime("%Y-%m-%d %H:%M UTC"))
    log.info("=" * 60)

    # Step 1: Crawl
    log.info("Step 1/3 — Crawling feeds…")
    articles = fetch_all(top_n=30, max_age_hours=36)
    log.info("Selected %d significant articles", len(articles))

    if not articles:
        log.warning("No articles found. Check network / feeds.")

    # Step 2: Summarize
    log.info("Step 2/3 — Generating digest…")
    digest = generate_digest(articles)

    # Step 3: Render
    log.info("Step 3/3 — Rendering HTML…")
    date_slug  = today.strftime("%Y-%m-%d")
    html_path  = OUTPUT_DIR / f"digest-{date_slug}.html"
    latest_path = OUTPUT_DIR / "index.html"   # always overwrite the "latest" page

    render_digest(digest, articles, html_path)
    render_digest(digest, articles, latest_path)

    # Also save raw JSON for debugging / downstream use
    (OUTPUT_DIR / f"digest-{date_slug}.json").write_text(
        json.dumps({"digest": digest, "articles": articles}, indent=2, ensure_ascii=False)
    )

    log.info("─" * 60)
    log.info("Done!  Open: output/index.html")
    log.info("Headline: %s", digest.get("headline", ""))

if __name__ == "__main__":
    main()
