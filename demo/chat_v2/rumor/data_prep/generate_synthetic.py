"""Generate synthetic rumor-spread events in the RumorAnalyze table format.

All data is simulated (fixed seed, reproducible). Each event has rumor, debunk
and normal source posts; reposts form multi-level cascades whose parent can be
another repost. Big accounts get more reposts, and debunk posts start later.

Usage:
  python generate_synthetic.py --out DIR [--seed 2026]
"""

from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta
from pathlib import Path

from common import hash_user, write_tables

EVENTS = [
    {
        "slug": "salt_shortage",
        "start": "2026-03-02 08:00:00",
        "rumor": ["紧急扩散！核污染导致海盐全部停产，超市食盐即将断货，赶紧囤货！",
                  "我朋友在盐业公司，说下周起食盐限购，大家抓紧买",
                  "已经有超市食盐卖空了，再不囤就来不及了"],
        "debunk": ["【辟谣】我国食盐以井矿盐为主，供应充足，请勿听信谣言盲目囤盐。",
                   "盐业协会回应：食盐库存充足，不存在断货，相关说法不实。"],
        "normal": ["今天去超市看到很多人在买盐，有点夸张", "食盐的种类有哪些？科普一下"],
        "rumor_scale": 1.0, "debunk_delay_h": 10,
    },
    {
        "slug": "exam_leak",
        "start": "2026-06-05 20:00:00",
        "rumor": ["内部消息：今年高考数学卷已泄露，答案在群里流传，速看",
                  "有人在网上卖高考真题，据说是真的，已经有人买到了"],
        "debunk": ["【警方通报】网传“高考试题泄露”系诈骗信息，请考生和家长提高警惕。",
                   "教育考试院：试卷保密工作严格，网上所谓真题均为虚假信息。"],
        "normal": ["高考加油！明天就要进考场了", "高考期间考点周边交通管制提醒"],
        "rumor_scale": 0.7, "debunk_delay_h": 4,
    },
    {
        "slug": "earthquake_forecast",
        "start": "2026-09-14 13:00:00",
        "rumor": ["专家预测：本周末本市将发生7级地震，请大家做好准备，转给家人！",
                  "地震局内部人员透露，这两天可能有大地震，晚上别睡太死"],
        "debunk": ["【辟谣】市地震局：目前科学上无法准确预测地震，网传消息不实。",
                   "地震局官方：未发布任何地震预报，请以官方渠道信息为准。"],
        "normal": ["家庭应急包应该准备哪些东西？", "今天天气不错，出去走走"],
        "rumor_scale": 1.3, "debunk_delay_h": 18,
    },
]


def _followers(rng: random.Random, kind: str) -> int:
    if kind == "official":
        return rng.randint(800_000, 5_000_000)
    if kind == "bigv":
        return rng.randint(50_000, 400_000)
    return rng.randint(20, 8_000)


def _cascade(rng, root_id, root_time, root_followers, size, decay_h, user_pool, salt, counter):
    """Grow a repost tree; parent choice favours high-follower nodes."""
    nodes = [(root_id, root_time, root_followers)]
    weights = [root_followers ** 0.5 + 1]
    edges = []
    for _ in range(size):
        idx = rng.choices(range(len(nodes)), weights=weights)[0]
        parent_id, parent_time, _ = nodes[idx]
        t = parent_time + timedelta(hours=rng.expovariate(1 / decay_h))
        counter[0] += 1
        pid = f"r{counter[0]:07d}"
        raw_uid = rng.choice(user_pool)
        f = _followers(rng, "bigv" if rng.random() < 0.01 else "user")
        nodes.append((pid, t, f))
        weights.append(f ** 0.5 + 1)
        edges.append({"post_id": pid, "parent_post_id": parent_id,
                      "user_id": hash_user(raw_uid, salt),
                      "created_at": t.strftime("%Y-%m-%d %H:%M:%S")})
    return edges


def generate(event: dict, seed: int, salt: str = "rumoranalyze"):
    rng = random.Random(f"{seed}:{event['slug']}")
    start = datetime.strptime(event["start"], "%Y-%m-%d %H:%M:%S")
    user_pool = list(range(1, 6000))
    posts, reposts, counter = [], [], [0]
    specs = []
    for text in event["rumor"]:
        specs.append(("rumor", text, start + timedelta(hours=rng.uniform(0, 6)),
                      "user", int(rng.uniform(600, 1500) * event["rumor_scale"]), 5.0))
    for text in event["debunk"]:
        t = start + timedelta(hours=event["debunk_delay_h"] + rng.uniform(0, 8))
        specs.append(("debunk", text, t, "official", int(rng.uniform(250, 700)), 3.0))
    for text in event["normal"]:
        specs.append(("normal", text, start + timedelta(hours=rng.uniform(0, 48)),
                      "user", rng.randint(5, 60), 8.0))
    for n, (label, text, t, kind, size, decay) in enumerate(specs, 1):
        pid = f"{event['slug']}_p{n:03d}"
        f = _followers(rng, kind)
        posts.append({"post_id": pid, "user_id": hash_user(f"{kind}-{event['slug']}-{n}", salt),
                      "created_at": t.strftime("%Y-%m-%d %H:%M:%S"), "text": text,
                      "followers": f, "label": label})
        reposts += _cascade(rng, pid, t, f, size, decay, user_pool, salt, counter)
    return posts, reposts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    for event in EVENTS:
        posts, reposts = generate(event, args.seed)
        write_tables(args.out / event["slug"], posts, reposts)
        print(f"{event['slug']}: {len(posts)} posts, {len(reposts)} reposts")


if __name__ == "__main__":
    main()
