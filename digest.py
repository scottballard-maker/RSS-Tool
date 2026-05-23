"""
AI Superstar Digest — digest.py
Fetches latest content from AI thought leaders and emails a digest.
Runs for free via GitHub Actions cron (Mon & Thu).
"""

import feedparser
import smtplib
import json
import os
import time
import requests
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from html import escape

# ─── CONFIGURATION ────────────────────────────────────────────────────────────
# Set these as environment variables (or GitHub Actions secrets)

GMAIL_USER     = os.environ.get("GMAIL_USER", "you@gmail.com")
GMAIL_APP_PASS = os.environ.get("GMAIL_APP_PASS", "")          # Gmail App Password
TO_EMAIL       = os.environ.get("TO_EMAIL", "you@gmail.com")

# Optional: Claude API key for AI-powered summaries (free $5 credit on new accounts)
ANTHROPIC_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")

# How many days back to look for new content
LOOKBACK_DAYS  = 4   # covers Mon→Thu and Thu→Mon gaps with some buffer

# Cache file — tracks already-seen URLs to avoid duplicates
CACHE_FILE     = Path("seen_urls.json")

# ─── CREATORS ─────────────────────────────────────────────────────────────────
CREATORS = [
    {
        "name": "Ethan Mollick",
        "emoji": "🤖",
        "feeds": [
            {"url": "https://www.oneusefulthing.org/feed", "type": "substack"},
        ],
        "reddit_search": "Ethan Mollick",
        "x_handle": "@emollick",
        "x_note": "Check manually: https://x.com/emollick",
    },
    {
        "name": "Andrej Karpathy",
        "emoji": "🧠",
        "feeds": [],
        "reddit_search": "Karpathy",
        "x_handle": "@karpathy",
        "x_note": "Check manually: https://x.com/karpathy",
    },
    {
        "name": "Andrew Ng",
        "emoji": "📚",
        "feeds": [
            {"url": "https://www.deeplearning.ai/the-batch/feed/", "type": "newsletter"},
        ],
        "reddit_search": "Andrew Ng",
        "x_handle": "@AndrewYNg",
        "x_note": "Check manually: https://x.com/AndrewYNg",
    },
    {
        "name": "Jim Fan",
        "emoji": "🤖",
        "feeds": [],
        "reddit_search": "Jim Fan AI",
        "x_handle": "@DrJimFan",
        "x_note": "Check manually: https://x.com/DrJimFan",
    },
    {
        "name": "Cassie Kozyrkov",
        "emoji": "📊",
        "feeds": [
            {"url": "https://medium.com/feed/@kozyrkov", "type": "medium"},
        ],
        "reddit_search": "Cassie Kozyrkov",
        "x_handle": "@quaesita",
        "x_note": "Check manually: https://x.com/quaesita",
    },
    {
        "name": "Yann LeCun",
        "emoji": "🔬",
        "feeds": [],
        "reddit_search": "Yann LeCun",
        "x_handle": "@ylecun",
        "x_note": "Check manually: https://x.com/ylecun",
    },
    {
        "name": "Swyx & Alessio Fanelli",
        "emoji": "🎙️",
        "feeds": [
            {"url": "https://latent.space/feed", "type": "substack"},
        ],
        "reddit_search": "Latent Space podcast",
        "x_handle": "@swyx / @alessiofan",
        "x_note": "Check manually: https://x.com/swyx",
    },
    {
        "name": "Rowan Cheung",
        "emoji": "📰",
        "feeds": [
            {"url": "https://www.therundown.ai/rss", "type": "newsletter"},
        ],
        "reddit_search": "Rowan Cheung AI",
        "x_handle": "@rowancheung",
        "x_note": "Check manually: https://x.com/rowancheung",
    },
    {
        "name": "Allie K. Miller",
        "emoji": "💡",
        "feeds": [],
        "reddit_search": "Allie K Miller AI",
        "x_handle": "@alliekmiller",
        "x_note": "Check manually: https://x.com/alliekmiller",
    },
    {
        "name": "Lenny Rachitsky",
        "emoji": "🚀",
        "feeds": [
            {"url": "https://www.lennysnewsletter.com/feed", "type": "substack"},
        ],
        "reddit_search": "Lenny Rachitsky",
        "x_handle": "@lennysan",
        "x_note": "Check manually: https://x.com/lennysan",
    },
]

# Subreddits to search for creator mentions
REDDIT_SUBREDDITS = ["MachineLearning", "artificial", "LocalLLaMA", "OpenAI", "singularity"]


# ─── CACHE ────────────────────────────────────────────────────────────────────

def load_cache():
    if CACHE_FILE.exists():
        return set(json.loads(CACHE_FILE.read_text()))
    return set()

def save_cache(seen: set):
    # Keep only last 2000 URLs to prevent unbounded growth
    urls = list(seen)[-2000:]
    CACHE_FILE.write_text(json.dumps(urls))


# ─── RSS FETCHING ──────────────────────────────────────────────────────────────

def fetch_rss(feed_url: str, lookback_days: int) -> list[dict]:
    """Fetch and filter RSS/Atom feed entries newer than lookback_days."""
    items = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    try:
        # Use a browser-like UA — some feeds block the default feedparser agent
        feed = feedparser.parse(
            feed_url,
            agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        for entry in feed.entries:
            pub = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                pub = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                pub = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)

            if pub and pub < cutoff:
                continue  # too old

            summary = ""
            if hasattr(entry, "summary"):
                summary = entry.summary
            elif hasattr(entry, "description"):
                summary = entry.description

            # Strip HTML tags for plain text snippet
            import re
            clean = re.sub(r"<[^>]+>", "", summary)[:400].strip()

            items.append({
                "title": entry.get("title", "Untitled"),
                "url": entry.get("link", ""),
                "snippet": clean,
                "date": pub.strftime("%b %d") if pub else "Recent",
                "source": "RSS",
            })
    except Exception as e:
        print(f"  RSS error for {feed_url}: {e}")
    return items


# ─── REDDIT FETCHING ──────────────────────────────────────────────────────────

def fetch_reddit(query: str, lookback_days: int) -> list[dict]:
    """Search Reddit via the public JSON API (no auth needed for read-only)."""
    items = []
    cutoff = time.time() - (lookback_days * 86400)
    headers = {"User-Agent": "AI-Digest-Bot/1.0 (personal digest tool)"}

    subreddits = "+".join(REDDIT_SUBREDDITS)
    url = f"https://www.reddit.com/r/{subreddits}/search.json"
    params = {"q": query, "sort": "new", "t": "week", "limit": 5}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        data = resp.json()
        for post in data.get("data", {}).get("children", []):
            p = post["data"]
            if p["created_utc"] < cutoff:
                continue
            items.append({
                "title": p["title"][:120],
                "url": f"https://reddit.com{p['permalink']}",
                "snippet": (p.get("selftext") or "")[:300].strip(),
                "date": datetime.fromtimestamp(p["created_utc"], tz=timezone.utc).strftime("%b %d"),
                "source": f"r/{p['subreddit']}",
            })
        time.sleep(1)  # Be polite to Reddit
    except Exception as e:
        print(f"  Reddit error for '{query}': {e}")
    return items


# ─── OPTIONAL: AI SUMMARIZATION ───────────────────────────────────────────────

def summarize_with_claude(text: str) -> str:
    """Condense a piece of text using Claude API (optional)."""
    if not ANTHROPIC_KEY:
        return ""
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 120,
                "messages": [{
                    "role": "user",
                    "content": f"Summarize in 2 sentences, plain text only:\n\n{text[:1000]}"
                }]
            },
            timeout=20,
        )
        return resp.json()["content"][0]["text"].strip()
    except Exception as e:
        print(f"  Claude API error: {e}")
        return ""


# ─── EMAIL ────────────────────────────────────────────────────────────────────

def build_email_html(digest: list[dict], run_date: str) -> str:
    sections = ""
    total_items = sum(len(c["items"]) for c in digest)

    for creator in digest:
        if not creator["items"]:
            continue

        items_html = ""
        for item in creator["items"]:
            ai_summary = ""
            if item.get("snippet") and ANTHROPIC_KEY:
                summary = summarize_with_claude(item["snippet"])
                if summary:
                    ai_summary = f'<p style="color:#555;font-style:italic;margin:6px 0 0;">{escape(summary)}</p>'

            items_html += f"""
            <div style="border-left:3px solid #e0e0e0;padding:10px 14px;margin:10px 0;background:#fafafa;border-radius:4px;">
              <div style="font-size:12px;color:#888;margin-bottom:4px;">{escape(item['date'])} · {escape(item['source'])}</div>
              <a href="{escape(item['url'])}" style="color:#1a1a1a;font-weight:600;font-size:15px;text-decoration:none;">
                {escape(item['title'])}
              </a>
              {"<p style='color:#555;font-size:14px;margin:6px 0 0;'>"+escape(item['snippet'][:200])+"…</p>" if item.get('snippet') else ""}
              {ai_summary}
            </div>"""

        x_note = creator.get("x_note", "")
        x_html = f'<div style="font-size:12px;color:#999;margin-top:8px;">🐦 {escape(x_note)}</div>' if x_note else ""

        sections += f"""
        <div style="margin-bottom:30px;">
          <h2 style="font-size:18px;font-weight:600;margin:0 0 4px;color:#1a1a1a;">
            {creator['emoji']} {escape(creator['name'])}
          </h2>
          {items_html}
          {x_html}
        </div>"""

    if not sections:
        sections = "<p style='color:#888;'>No new content found since the last digest. Your superstars have been quiet!</p>"

    return f"""<!DOCTYPE html>
<html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:680px;margin:0 auto;padding:24px;color:#1a1a1a;">
  <div style="border-bottom:2px solid #1a1a1a;padding-bottom:16px;margin-bottom:28px;">
    <h1 style="font-size:22px;font-weight:700;margin:0;">🧠 AI Superstar Digest</h1>
    <p style="color:#888;font-size:14px;margin:4px 0 0;">{run_date} · {total_items} new items</p>
  </div>
  {sections}
  <div style="border-top:1px solid #e0e0e0;margin-top:32px;padding-top:16px;font-size:12px;color:#aaa;">
    Sent by your AI Digest bot · RSS + Reddit · X posts require manual check
  </div>
</body></html>"""


def send_email(subject: str, html_body: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = TO_EMAIL
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASS)
        server.sendmail(GMAIL_USER, TO_EMAIL, msg.as_string())
    print(f"✅ Email sent to {TO_EMAIL}")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def run():
    print(f"\n🚀 AI Digest starting — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    seen = load_cache()
    digest = []

    for creator in CREATORS:
        print(f"\n📡 Fetching: {creator['name']}")
        items = []

        # RSS feeds
        for feed in creator.get("feeds", []):
            raw = fetch_rss(feed["url"], LOOKBACK_DAYS)
            for item in raw:
                if item["url"] not in seen:
                    items.append(item)
                    seen.add(item["url"])

        # Reddit mentions
        if creator.get("reddit_search"):
            raw = fetch_reddit(creator["reddit_search"], LOOKBACK_DAYS)
            for item in raw:
                if item["url"] not in seen:
                    items.append(item)
                    seen.add(item["url"])

        print(f"   → {len(items)} new items")
        digest.append({**creator, "items": items})

    save_cache(seen)

    run_date = datetime.now().strftime("%A, %B %d")
    html = build_email_html(digest, run_date)

    total = sum(len(c["items"]) for c in digest)
    subject = f"🧠 AI Digest — {run_date} ({total} new items)"

    send_email(subject, html)


if __name__ == "__main__":
    run()
