"""
renderer.py — Turn a digest dict + articles into a beautiful standalone HTML page.
"""

from datetime import datetime, timezone
from pathlib import Path
import html as html_lib
import json

def esc(s: str) -> str:
    return html_lib.escape(str(s or ""))

def render_digest(digest: dict, articles: list[dict], out_path: Path):
    date_str  = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")
    date_slug = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Images from top articles
    images = [(a["image"], a["title"], a["url"], a["source"])
              for a in articles if a.get("image")][:3]

    # Build sections HTML
    sections_html = ""
    for sec in digest.get("sections", []):
        body = esc(sec.get("body", ""))
        # Convert newlines to paragraphs
        paras = "".join(f"<p>{p.strip()}</p>" for p in body.split("\n") if p.strip())
        sections_html += f"""
        <div class="section">
          <h2>{esc(sec.get('title',''))}</h2>
          <div class="section-body">{paras}</div>
        </div>"""

    # Build images HTML
    images_html = ""
    if images:
        cards = ""
        for img_url, title, link, source in images:
            cards += f"""
            <a class="img-card" href="{esc(link)}" target="_blank" rel="noopener">
              <img src="{esc(img_url)}" alt="{esc(title)}" loading="lazy" onerror="this.parentElement.style.display='none'" />
              <div class="img-caption">
                <span class="img-source">{esc(source)}</span>
                <span class="img-title">{esc(title[:70])}{'…' if len(title)>70 else ''}</span>
              </div>
            </a>"""
        images_html = f'<div class="image-strip">{cards}</div>'

    # Sources list
    sources_seen = list(dict.fromkeys(a["source"] for a in articles))
    sources_html = " · ".join(f"<span>{esc(s)}</span>" for s in sources_seen)

    # Article references
    refs_html = ""
    for a in articles[:20]:
        refs_html += f"""
        <a class="ref-link" href="{esc(a['url'])}" target="_blank" rel="noopener">
          <span class="ref-source">{esc(a['source'])}</span>
          <span class="ref-title">{esc(a['title'])}</span>
        </a>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Tech Digest — {date_str}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;900&family=Source+Serif+4:ital,wght@0,300;0,400;0,600;1,300;1,400&display=swap" rel="stylesheet" />
  <style>
    :root {{
      --ink:      #1a1a1a;
      --ink2:     #444;
      --ink3:     #888;
      --rule:     #d8d0c4;
      --bg:       #faf8f4;
      --accent:   #c0392b;
      --surface:  #f2ede6;
      --serif:    'Source Serif 4', Georgia, serif;
      --display:  'Playfair Display', Georgia, serif;
    }}
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background: var(--bg);
      color: var(--ink);
      font-family: var(--serif);
      font-weight: 300;
      line-height: 1.75;
    }}

    /* ── Masthead ── */
    .masthead {{
      border-bottom: 3px double var(--ink);
      padding: 2.5rem 0 1.5rem;
      text-align: center;
      max-width: 860px;
      margin: 0 auto;
    }}
    .masthead-label {{
      font-family: var(--serif);
      font-size: 0.7rem;
      letter-spacing: 0.22em;
      text-transform: uppercase;
      color: var(--ink3);
      margin-bottom: 0.6rem;
    }}
    .masthead-title {{
      font-family: var(--display);
      font-size: clamp(2.4rem, 6vw, 4rem);
      font-weight: 900;
      line-height: 1.1;
      letter-spacing: -0.02em;
      color: var(--ink);
    }}
    .masthead-title em {{
      color: var(--accent);
      font-style: normal;
    }}
    .masthead-date {{
      margin-top: 0.9rem;
      font-size: 0.8rem;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--ink3);
    }}

    /* ── Layout ── */
    .container {{
      max-width: 860px;
      margin: 0 auto;
      padding: 0 1.5rem 4rem;
    }}

    /* ── TLDR Banner ── */
    .tldr {{
      border-left: 4px solid var(--accent);
      background: var(--surface);
      padding: 1.2rem 1.5rem;
      margin: 2.5rem 0 2rem;
      font-size: 1.05rem;
      font-style: italic;
      color: var(--ink2);
    }}
    .tldr strong {{
      display: block;
      font-family: var(--display);
      font-size: 0.72rem;
      font-style: normal;
      letter-spacing: 0.15em;
      text-transform: uppercase;
      color: var(--accent);
      margin-bottom: 0.4rem;
    }}

    /* ── Image Strip ── */
    .image-strip {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 1px;
      background: var(--rule);
      border: 1px solid var(--rule);
      margin: 2rem 0;
      overflow: hidden;
    }}
    .img-card {{
      display: block;
      background: var(--surface);
      text-decoration: none;
      overflow: hidden;
    }}
    .img-card img {{
      width: 100%;
      height: 170px;
      object-fit: cover;
      display: block;
      transition: transform 0.3s ease;
    }}
    .img-card:hover img {{ transform: scale(1.03); }}
    .img-caption {{
      padding: 0.7rem 0.9rem;
    }}
    .img-source {{
      display: block;
      font-size: 0.62rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--accent);
      margin-bottom: 0.2rem;
    }}
    .img-title {{
      display: block;
      font-size: 0.82rem;
      font-weight: 400;
      color: var(--ink2);
      line-height: 1.4;
    }}

    /* ── Rule ── */
    hr {{
      border: none;
      border-top: 1px solid var(--rule);
      margin: 2.5rem 0;
    }}

    /* ── Sections ── */
    .section {{ margin: 2.5rem 0; }}
    .section h2 {{
      font-family: var(--display);
      font-size: 1.4rem;
      font-weight: 700;
      color: var(--ink);
      padding-bottom: 0.5rem;
      border-bottom: 1px solid var(--rule);
      margin-bottom: 1.2rem;
    }}
    .section-body p {{
      font-size: 1.02rem;
      line-height: 1.8;
      color: var(--ink2);
      margin-bottom: 1rem;
    }}

    /* ── Key Takeaway ── */
    .takeaway {{
      background: var(--ink);
      color: #f5f0e8;
      padding: 1.5rem 2rem;
      margin: 2.5rem 0;
      font-family: var(--display);
      font-size: 1.15rem;
      font-weight: 400;
      font-style: italic;
      line-height: 1.55;
      position: relative;
    }}
    .takeaway::before {{
      content: '★  KEY TAKEAWAY';
      display: block;
      font-family: var(--serif);
      font-size: 0.65rem;
      font-style: normal;
      letter-spacing: 0.18em;
      color: #c0a882;
      margin-bottom: 0.6rem;
    }}

    /* ── Sources bar ── */
    .sources-bar {{
      font-size: 0.72rem;
      color: var(--ink3);
      letter-spacing: 0.04em;
      border-top: 1px solid var(--rule);
      border-bottom: 1px solid var(--rule);
      padding: 0.6rem 0;
      margin: 2rem 0;
    }}
    .sources-bar span {{ margin-right: 0.5rem; }}

    /* ── References ── */
    .refs-title {{
      font-size: 0.68rem;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      color: var(--ink3);
      margin-bottom: 1rem;
    }}
    .ref-link {{
      display: flex;
      gap: 0.7rem;
      align-items: baseline;
      padding: 0.5rem 0;
      border-bottom: 1px solid var(--rule);
      text-decoration: none;
      transition: background 0.1s;
    }}
    .ref-link:hover {{ background: var(--surface); padding-left: 0.4rem; }}
    .ref-source {{
      font-size: 0.63rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--accent);
      white-space: nowrap;
      flex-shrink: 0;
      width: 130px;
    }}
    .ref-title {{
      font-size: 0.85rem;
      color: var(--ink2);
      line-height: 1.4;
    }}

    /* ── Footer ── */
    footer {{
      border-top: 3px double var(--ink);
      max-width: 860px;
      margin: 0 auto;
      padding: 1.5rem;
      text-align: center;
      font-size: 0.72rem;
      letter-spacing: 0.06em;
      color: var(--ink3);
    }}
  </style>
</head>
<body>

  <div class="masthead">
    <div class="masthead-label">Daily AI & Tech Intelligence</div>
    <div class="masthead-title">TECH<em>PULSE</em></div>
    <div class="masthead-date">{date_str}</div>
  </div>

  <div class="container">

    <div class="tldr">
      <strong>Today in Brief</strong>
      {esc(digest.get('tldr', ''))}
    </div>

    {images_html}

    <div class="sources-bar">Sourced from: {sources_html}</div>

    {sections_html}

    <div class="takeaway">{esc(digest.get('key_takeaway', ''))}</div>

    <hr />

    <div class="refs-title">Source Articles ({len(articles)} crawled)</div>
    <div class="refs">{refs_html}</div>

  </div>

  <footer>
    TECHPULSE · Generated {date_str} · {len(articles)} articles crawled from {len(set(a['source'] for a in articles))} sources
  </footer>

</body>
</html>"""

    out_path.write_text(html, encoding="utf-8")
