"""
summarizer.py — Feed articles to Groq (free LLM API) and get a cohesive daily digest.
Falls back to extractive summary if no API key is set.
"""

import os
import json
import logging
import textwrap
from datetime import datetime, timezone

log = logging.getLogger(__name__)

GROQ_MODEL = "llama-3.3-70b-versatile"   # Free on Groq's free tier

SYSTEM_PROMPT = """You are a senior tech journalist writing a daily AI & tech briefing for software engineers and tech professionals.

Your job: read a list of today's top tech articles and produce a single, cohesive daily digest.

Rules:
- Write in a clear, confident, journalistic tone — not bullet points, real paragraphs
- Structure your output as valid JSON with these exact keys:
  {
    "headline": "One punchy headline for today (max 12 words)",
    "tldr": "2-sentence summary of the biggest thing that happened today",
    "sections": [
      {
        "title": "Section name (e.g. AI Models & Research, Developer Tools, Industry Moves)",
        "body": "2-4 paragraph narrative covering the key stories in this area. Weave multiple articles together naturally. Mention specific products, companies, and numbers. Be specific and concrete."
      }
    ],
    "key_takeaway": "One sentence — the single most important thing to know today"
  }
- Use 3-4 sections. Only include sections where there are actual stories.
- Do NOT make up facts. Only use what's in the articles provided.
- Do NOT return markdown, code blocks, or anything outside the JSON object."""


def build_prompt(articles: list[dict]) -> str:
    today = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")
    lines = [f"Today is {today}. Here are the top tech & AI stories:\n"]
    for i, a in enumerate(articles, 1):
        lines.append(f"{i}. [{a['source']}] {a['title']}")
        if a.get("summary"):
            lines.append(f"   {a['summary'][:300]}")
        lines.append("")
    return "\n".join(lines)


def summarize_with_groq(articles: list[dict]) -> dict:
    """Call Groq API (free tier) to generate the digest."""
    try:
        from groq import Groq
    except ImportError:
        raise RuntimeError("groq package not installed. Run: pip install groq")

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable not set")

    client   = Groq(api_key=api_key)
    prompt   = build_prompt(articles)

    log.info("Calling Groq (%s) with %d articles…", GROQ_MODEL, len(articles))
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.4,
        max_tokens=2000,
    )

    raw = response.choices[0].message.content.strip()
    # Strip markdown fences if model adds them
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    digest = json.loads(raw)
    log.info("Digest generated: '%s'", digest.get("headline", ""))
    return digest


def extractive_fallback(articles: list[dict]) -> dict:
    """
    No-LLM fallback: build a structured digest from article titles/summaries.
    Used when GROQ_API_KEY is not set.
    """
    log.warning("GROQ_API_KEY not set — using extractive fallback (no LLM)")

    # Group by rough category
    groups: dict[str, list] = {"AI & Models": [], "Developer Tools & Engineering": [], "Industry & Business": []}
    ai_words  = ["ai", "model", "llm", "gpt", "claude", "gemini", "llama", "neural", "machine learning", "deep learning", "openai", "anthropic"]
    dev_words = ["python", "javascript", "rust", "framework", "github", "open source", "developer", "programming", "system design", "kubernetes", "database"]

    for a in articles:
        text = (a["title"] + " " + a.get("summary", "")).lower()
        if any(w in text for w in ai_words):
            groups["AI & Models"].append(a)
        elif any(w in text for w in dev_words):
            groups["Developer Tools & Engineering"].append(a)
        else:
            groups["Industry & Business"].append(a)

    sections = []
    for title, items in groups.items():
        if not items:
            continue
        bullets = "\n".join(f"• {a['title']} ({a['source']})" for a in items[:5])
        sections.append({"title": title, "body": bullets})

    top = articles[0] if articles else {}
    return {
        "headline":      top.get("title", "Today's Tech Digest"),
        "tldr":          f"Today's digest covers {len(articles)} significant stories across AI, developer tools, and the tech industry.",
        "sections":      sections,
        "key_takeaway":  top.get("summary", "Check the full stories for details."),
    }


def generate_digest(articles: list[dict]) -> dict:
    """Main entry: try Groq, fall back to extractive."""
    if not articles:
        return {
            "headline":     "No significant news today",
            "tldr":         "No major stories were found in today's crawl.",
            "sections":     [],
            "key_takeaway": "Check back tomorrow.",
        }
    try:
        return summarize_with_groq(articles)
    except Exception as exc:
        log.warning("Groq summarization failed (%s), using extractive fallback", exc)
        return extractive_fallback(articles)
