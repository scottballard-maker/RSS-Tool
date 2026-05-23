# 🧠 AI Superstar Digest

Automated email digest of content from top AI thought leaders.
Runs free on GitHub Actions every Monday & Thursday at 7am MT.

---

## What it covers

| Creator | Sources | X (manual) |
|---|---|---|
| Ethan Mollick | Substack RSS | @emollick |
| Andrej Karpathy | Reddit mentions | @karpathy |
| Andrew Ng | The Batch RSS + Reddit | @AndrewYNg |
| Jim Fan | Reddit mentions | @DrJimFan |
| Cassie Kozyrkov | Medium RSS | @quaesita |
| Yann LeCun | Reddit mentions | @ylecun |
| Swyx & Alessio | Latent Space Substack RSS | @swyx |
| Rowan Cheung | The Rundown RSS | @rowancheung |
| Allie K. Miller | Reddit mentions | @alliekmiller |
| Lenny Rachitsky | Lenny's Newsletter RSS | @lennysan |

**X posts cannot be fetched for free** (API costs $100+/mo). The email includes links to check manually.

---

## Setup (15 minutes, completely free)

### Step 1 — Fork or create this repo on GitHub
Put all files in the repo root with `.github/workflows/digest.yml` in place.

### Step 2 — Get a Gmail App Password
1. Go to your Google Account → Security → 2-Step Verification (enable if needed)
2. Search "App passwords" → create one named "AI Digest"
3. Copy the 16-character password (shown once)

### Step 3 — Add GitHub Secrets
In your repo: **Settings → Secrets and variables → Actions → New repository secret**

| Secret name | Value |
|---|---|
| `GMAIL_USER` | your.email@gmail.com |
| `GMAIL_APP_PASS` | the 16-char app password |
| `TO_EMAIL` | where to send digest (can be same) |
| `ANTHROPIC_API_KEY` | (optional) for AI summaries |

### Step 4 — Enable GitHub Actions
Go to the **Actions** tab in your repo and enable workflows if prompted.

### Step 5 — Test it
Click **Actions → AI Superstar Digest → Run workflow** to trigger manually and check your inbox.

---

## Cost breakdown

| Component | Cost |
|---|---|
| GitHub Actions (2 runs/week) | Free (2,000 min/month included) |
| Gmail SMTP | Free |
| RSS feeds | Free |
| Reddit public API | Free |
| Claude API summaries | Optional — ~$0.01/run |

**Total: $0/month** (or ~$0.08/month with AI summaries enabled)

---

## Customization

**Change schedule:** Edit the cron lines in `.github/workflows/digest.yml`
- `"0 14 * * 1"` = Monday 7am MT
- `"0 14 * * 4"` = Thursday 7am MT

**Add a creator:** Add a new entry to the `CREATORS` list in `digest.py`:
```python
{
    "name": "New Person",
    "emoji": "🔥",
    "feeds": [
        {"url": "https://example.substack.com/feed", "type": "substack"},
    ],
    "reddit_search": "New Person AI",
    "x_handle": "@handle",
    "x_note": "Check manually: https://x.com/handle",
},
```

**Change lookback window:** Edit `LOOKBACK_DAYS = 4` in `digest.py`

---

## Local testing

```bash
pip install feedparser requests

# Set env vars
export GMAIL_USER="you@gmail.com"
export GMAIL_APP_PASS="your-app-password"
export TO_EMAIL="you@gmail.com"

python digest.py
```
