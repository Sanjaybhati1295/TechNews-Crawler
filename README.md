# 🤖 Tech News Crawler

A **free, zero-API-key** daily crawler for AI and programming news.  
Runs automatically every day via **GitHub Actions** and commits results back to the repo.

---

## Features

| | |
|---|---|
| **Free** | Uses only public RSS feeds — no API keys, no paid services |
| **Scheduled** | GitHub Actions cron runs every day at 07:00 UTC (12:30 IST) |
| **Smart filtering** | 50+ keywords filter for AI, ML, and programming relevance |
| **16 sources** | HN, Dev.to, Ars Technica, VentureBeat, Reddit, GitHub Blog, and more |
| **Dual storage** | SQLite DB for history + `latest.json` for easy consumption |
| **Viewer** | `viewer.html` — offline-capable news dashboard |

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/sanjaybhati1295/tech-news-crawler.git
cd tech-news-crawler
pip install -r requirements.txt
```

### 2. Run once

```bash
python fetcher.py
```

This creates `output/news.db` and `output/latest.json`.

### 3. View results

Open `viewer.html` in your browser (needs a local server to load the JSON):

```bash
# Python built-in server
python -m http.server 8080
# Then open: http://localhost:8080/viewer.html
```

---

## GitHub Actions Setup (automated daily crawl)

1. **Push this repo to GitHub** (public or private)

2. **Enable Actions** under *Settings → Actions → General → Allow all actions*

3. **That's it.** The workflow runs daily at 07:00 UTC.  
   You can also trigger it manually: *Actions → Daily Tech News Crawl → Run workflow*

The bot commits `output/latest.json` and `output/news.db` back to the repo automatically.

---

## File Structure

```
tech-news-crawler/
├── fetcher.py                        # Main crawler script
├── requirements.txt                  # feedparser only
├── viewer.html                       # Browser-based news viewer
├── .github/
│   └── workflows/
│       └── daily_crawl.yml           # Scheduled GitHub Actions job
└── output/                           # Auto-created on first run
    ├── news.db                       # SQLite database (full history)
    ├── latest.json                   # Latest 200 articles (JSON)
    └── run.log                       # Run log
```

---

## Customization

### Add more sources

Edit the `FEEDS` list in `fetcher.py`:

```python
{
    "name": "My Custom Feed",
    "url":  "https://example.com/rss",
    "category": "tech",
},
```

### Change keywords

Edit the `KEYWORDS` list in `fetcher.py` to add or remove filtering terms.

### Change schedule

Edit the cron expression in `.github/workflows/daily_crawl.yml`:

```yaml
- cron: "0 7 * * *"   # Every day at 07:00 UTC
- cron: "0 */6 * * *" # Every 6 hours
- cron: "0 7 * * 1"   # Every Monday
```

---

## Consuming the JSON

The `output/latest.json` file is perfect for building downstream tools:

```python
import json

data = json.load(open("output/latest.json"))
for article in data["articles"]:
    print(article["title"], "—", article["source"])
```

Each article has: `id`, `title`, `url`, `summary`, `source`, `category`, `published`, `fetched_at`.

---

## Sources

| Source | Category |
|--------|----------|
| Hacker News | community |
| Dev.to (AI, ML, Programming) | programming / ai |
| MIT Technology Review | research |
| Ars Technica | tech |
| The Register | tech |
| VentureBeat AI | ai |
| InfoQ | engineering |
| Reddit r/MachineLearning | community |
| Reddit r/LocalLLaMA | ai |
| Reddit r/programming | programming |
| GitHub Blog | engineering |
| Google Research Blog | research |
| Towards Data Science | data science |

---

## License

MIT
