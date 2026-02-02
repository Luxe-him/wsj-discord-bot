import os
import json
from pathlib import Path
from datetime import datetime

import feedparser
import requests

DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
WSJ_RSS_URL = "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"

BASE_DIR = Path(__file__).resolve().parent
STATE_FILE = BASE_DIR / "state.json"

MAX_POSTS_PER_RUN = 6


def log(msg: str) -> None:
    print(f"[{datetime.utcnow().isoformat()}Z] {msg}")


def load_seen() -> set[str]:
    if STATE_FILE.exists():
        try:
            return set(json.loads(STATE_FILE.read_text(encoding="utf-8")).get("seen", []))
        except Exception:
            return set()
    return set()


def save_seen(seen: set[str]) -> None:
    # cap size so it doesn't grow forever
    seen_list = list(seen)[-2000:]
    STATE_FILE.write_text(json.dumps({"seen": seen_list}, indent=2), encoding="utf-8")


def post(title: str, link: str) -> None:
    payload = {
        "username": "WSJ News",
        "embeds": [{"title": title[:256], "url": link}],
        "allowed_mentions": {"parse": []},
    }
    r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=15)
    r.raise_for_status()


def main():
    seen = load_seen()
    feed = feedparser.parse(WSJ_RSS_URL)

    posted = 0
    for entry in reversed(feed.entries or []):  # oldest -> newest
        link = (entry.get("link") or "").strip()
        if not link:
            continue

        uid = link  # stable key
        if uid in seen:
            continue

        title = (entry.get("title") or "WSJ Headline").strip()
        post(title, link)
        log(f"Posted: {title}")
        seen.add(uid)
        posted += 1

        if posted >= MAX_POSTS_PER_RUN:
            break

    save_seen(seen)
    log(f"Run complete. Posted {posted} items.")


if __name__ == "__main__":
    main()
