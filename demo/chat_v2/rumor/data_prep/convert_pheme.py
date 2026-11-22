"""Convert one PHEME event (Zubiaga et al.) to RumorAnalyze tables.

Expected raw layout (PHEME "all-rnr-annotated-threads"):
  <event_dir>/rumours/<thread_id>/source-tweets/<id>.json
  <event_dir>/rumours/<thread_id>/reactions/<id>.json
  <event_dir>/rumours/<thread_id>/annotation.json   (optional, has "true"/"misinformation")
  <event_dir>/non-rumours/<thread_id>/...

Labels: source tweet of a rumour thread -> "rumor"; of a non-rumour thread -> "normal";
a reaction that the annotation marks as debunking is not available per tweet, so reactions
containing debunk keywords are labeled "debunk" (heuristic).

Usage:
  python convert_pheme.py --event-dir DIR --out OUT_DIR [--salt S]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from common import hash_user, write_tables

DEBUNK_KEYWORDS = ("fake", "hoax", "not true", "false", "debunk", "fact check")


def _ts(value: str) -> str:
    return datetime.strptime(value, "%a %b %d %H:%M:%S %z %Y").strftime("%Y-%m-%d %H:%M:%S")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def convert(event_dir: Path, salt: str) -> tuple[list[dict], list[dict]]:
    posts, reposts = [], []
    for group, label in (("rumours", "rumor"), ("non-rumours", "normal")):
        for thread in sorted((event_dir / group).glob("*")):
            if not thread.is_dir():
                continue
            for src in (thread / "source-tweets").glob("*.json"):
                tw = _load(src)
                posts.append({
                    "post_id": str(tw["id_str"]), "user_id": hash_user(tw["user"]["id_str"], salt),
                    "created_at": _ts(tw["created_at"]), "text": tw.get("text", ""),
                    "followers": int(tw["user"].get("followers_count") or 0), "label": label,
                })
            for rx in (thread / "reactions").glob("*.json"):
                tw = _load(rx)
                text = tw.get("text", "")
                post_id = str(tw["id_str"])
                user_id = hash_user(tw["user"]["id_str"], salt)
                created_at = _ts(tw["created_at"])
                parent = tw.get("in_reply_to_status_id_str") or thread.name
                reposts.append({"post_id": post_id, "parent_post_id": str(parent),
                                "user_id": user_id, "created_at": created_at})
                if label == "rumor" and any(k in text.lower() for k in DEBUNK_KEYWORDS):
                    posts.append({"post_id": post_id, "user_id": user_id, "created_at": created_at,
                                  "text": text, "followers": int(tw["user"].get("followers_count") or 0),
                                  "label": "debunk"})
    return posts, reposts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--event-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--salt", default="rumoranalyze")
    args = parser.parse_args()
    posts, reposts = convert(args.event_dir, args.salt)
    write_tables(args.out, posts, reposts)
    print(f"wrote {len(posts)} posts, {len(reposts)} reposts to {args.out}")


if __name__ == "__main__":
    main()
