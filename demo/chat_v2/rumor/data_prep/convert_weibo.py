"""Convert one event of the Weibo rumor dataset (Ma et al., IJCAI 2016) to RumorAnalyze tables.

Expected raw layout:
  <raw_dir>/Weibo.txt          lines like "eid:123 label:1 <post ids...>"
  <raw_dir>/Weibo/<eid>.json   list of posts; first item is the source post

The dataset only labels events (1 = rumor, 0 = non-rumor). Posts inside a rumor
event that contain a debunk keyword are labeled "debunk"; this is a heuristic.

Usage:
  python convert_weibo.py --raw-dir RAW --event-id EID --out OUT_DIR [--salt S]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from common import hash_user, write_tables

DEBUNK_KEYWORDS = ("辟谣", "谣言", "不实", "假消息", "已证实为假")


def _event_label(raw_dir: Path, event_id: str) -> str:
    for line in (raw_dir / "Weibo.txt").read_text(encoding="utf-8").splitlines():
        parts = dict(p.split(":", 1) for p in line.split()[:2] if ":" in p)
        if parts.get("eid") == event_id:
            return "rumor" if parts.get("label") == "1" else "normal"
    raise SystemExit(f"event {event_id} not found in Weibo.txt")


def _ts(value: object) -> str:
    return datetime.fromtimestamp(int(value), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def convert(raw_dir: Path, event_id: str, salt: str) -> tuple[list[dict], list[dict]]:
    event_label = _event_label(raw_dir, event_id)
    items = json.loads((raw_dir / "Weibo" / f"{event_id}.json").read_text(encoding="utf-8"))
    posts, reposts = [], []
    for index, item in enumerate(items):
        post_id = str(item.get("mid") or item.get("id"))
        user_id = hash_user(item.get("uid"), salt)
        created_at = _ts(item["t"])
        parent = item.get("parent")
        text = str(item.get("text") or "")
        is_debunk = (
            event_label == "rumor" and index > 0 and any(k in text for k in DEBUNK_KEYWORDS)
        )
        # Source post, root-level posts, and reposts whose comment debunks the rumor
        # are content posts; debunking reposts also keep their edge in reposts.csv.
        if index == 0 or not parent or is_debunk:
            posts.append({
                "post_id": post_id, "user_id": user_id, "created_at": created_at,
                "text": text, "followers": int(item.get("followers_count") or 0),
                "label": "debunk" if is_debunk else event_label,
            })
        if index > 0 and parent:
            reposts.append({
                "post_id": post_id, "parent_post_id": str(parent),
                "user_id": user_id, "created_at": created_at,
            })
    return posts, reposts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--event-id", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--salt", default="rumoranalyze")
    args = parser.parse_args()
    posts, reposts = convert(args.raw_dir, args.event_id, args.salt)
    write_tables(args.out, posts, reposts)
    print(f"wrote {len(posts)} posts, {len(reposts)} reposts to {args.out}")


if __name__ == "__main__":
    main()
