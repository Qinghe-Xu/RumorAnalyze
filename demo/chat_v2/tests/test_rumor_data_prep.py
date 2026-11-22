import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rumor" / "data_prep"))

import convert_pheme  # noqa: E402
import convert_weibo  # noqa: E402
from common import hash_user, write_tables  # noqa: E402


def _read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


class WeiboConvertTest(unittest.TestCase):
    def test_rumor_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp)
            (raw / "Weibo").mkdir()
            (raw / "Weibo.txt").write_text("eid:42 label:1 1 2 3\n", encoding="utf-8")
            items = [
                {"mid": "1", "uid": 100, "t": 1400000000, "text": "惊天消息", "followers_count": 5000, "parent": None},
                {"mid": "2", "uid": 101, "t": 1400003600, "text": "转发", "parent": "1"},
                {"mid": "3", "uid": 102, "t": 1400007200, "text": "这是谣言，官方已辟谣", "followers_count": 80, "parent": "1"},
            ]
            (raw / "Weibo" / "42.json").write_text(json.dumps(items), encoding="utf-8")
            posts, reposts = convert_weibo.convert(raw, "42", "s")
            out = raw / "out"
            write_tables(out, posts, reposts)
            p = _read(out / "posts.csv")
            r = _read(out / "reposts.csv")
        self.assertEqual([row["label"] for row in p], ["rumor", "debunk"])
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0]["parent_post_id"], "1")
        self.assertEqual(p[0]["created_at"], "2014-05-13 16:53:20")
        self.assertNotIn("100", p[0]["user_id"])
        self.assertEqual(p[0]["user_id"], hash_user(100, "s"))


class PhemeConvertTest(unittest.TestCase):
    def _tweet(self, tid, uid, text, reply=None):
        return {"id_str": tid, "user": {"id_str": uid, "followers_count": 10}, "text": text,
                "created_at": "Wed Jan 07 11:06:08 +0000 2015", "in_reply_to_status_id_str": reply}

    def test_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            ev = Path(tmp)
            for group, tid in (("rumours", "10"), ("non-rumours", "20")):
                (ev / group / tid / "source-tweets").mkdir(parents=True)
                (ev / group / tid / "reactions").mkdir()
                (ev / group / tid / "source-tweets" / f"{tid}.json").write_text(
                    json.dumps(self._tweet(tid, "u" + tid, "breaking")), encoding="utf-8")
            (ev / "rumours" / "10" / "reactions" / "11.json").write_text(
                json.dumps(self._tweet("11", "u11", "This is FAKE", reply="10")), encoding="utf-8")
            (ev / "non-rumours" / "20" / "reactions" / "21.json").write_text(
                json.dumps(self._tweet("21", "u21", "fake?", reply="20")), encoding="utf-8")
            posts, reposts = convert_pheme.convert(ev, "s")
        labels = sorted(p["label"] for p in posts)
        self.assertEqual(labels, ["debunk", "normal", "rumor"])
        self.assertEqual({r["parent_post_id"] for r in reposts}, {"10", "20"})
        self.assertEqual(posts[0]["created_at"], "2015-01-07 11:06:08")


class WriteTablesTest(unittest.TestCase):
    def test_rejects_bad_label(self):
        bad = [{"post_id": "1", "user_id": "u", "created_at": "x", "text": "", "followers": 0, "label": "fake"}]
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
            write_tables(Path(tmp), bad, [])


class SyntheticGeneratorTest(unittest.TestCase):
    def test_deterministic_and_consistent(self):
        import generate_synthetic as g
        event = g.EVENTS[0]
        posts, reposts = g.generate(event, 2026)
        self.assertEqual((posts, reposts), g.generate(event, 2026))
        ids = {p["post_id"] for p in posts} | {r["post_id"] for r in reposts}
        self.assertTrue(all(r["parent_post_id"] in ids for r in reposts))
        self.assertEqual({p["label"] for p in posts}, {"rumor", "debunk", "normal"})


if __name__ == "__main__":
    unittest.main()
