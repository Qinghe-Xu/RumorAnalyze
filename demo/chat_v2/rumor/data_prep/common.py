"""Shared schema and helpers for converting rumor datasets to RumorAnalyze tables."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

POST_FIELDS = ["post_id", "user_id", "created_at", "text", "followers", "label"]
REPOST_FIELDS = ["post_id", "parent_post_id", "user_id", "created_at"]
LABELS = {"rumor", "debunk", "normal"}


def hash_user(raw_id: object, salt: str) -> str:
    """Pseudonymize a user id; same id + salt always maps to the same value."""
    digest = hashlib.sha256(f"{salt}:{raw_id}".encode("utf-8")).hexdigest()
    return f"u_{digest[:12]}"


def write_tables(out_dir: Path, posts: list[dict], reposts: list[dict]) -> None:
    for row in posts:
        if row["label"] not in LABELS:
            raise ValueError(f"invalid label: {row['label']}")
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, fields, rows in (
        ("posts.csv", POST_FIELDS, posts),
        ("reposts.csv", REPOST_FIELDS, reposts),
    ):
        rows = sorted(rows, key=lambda r: r["created_at"])
        with (out_dir / name).open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerows({k: r[k] for k in fields} for r in rows)
