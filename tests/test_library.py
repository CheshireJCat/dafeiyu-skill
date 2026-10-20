import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / "skills/dafeiyu/scripts/library.py"
spec = importlib.util.spec_from_file_location("library", SCRIPT)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.pack = {"id": "demo", "version": "1.0.0", "license": "personal", "count": 1,
                     "name": "Demo", "source": "https://example.com"}
        self.row = {"id": "demo/a.jpg", "pack": "demo", "path": "a.jpg", "name": "比心",
                    "caption": "微笑比心", "keywords": "开心", "tag": "happy",
                    "url": "https://img.aigengtu.com/0_preview/meme/077.webp"}
        self.index = {"packs": {"demo": self.pack}, "stickers": [self.row]}
        self.image = b"\xff\xd8\xffsynthetic image fixture"

    def test_unfetched_results_never_invent_path_or_markdown(self):
        result = app.select(self.root, self.index, "比心")[0]
        self.assertFalse(result["cached"])
        self.assertNotIn("path", result)
        self.assertNotIn("markdown", result)
        self.assertEqual(result["fetchArgs"], ["fetch", "--id", "demo/a.jpg"])
        self.assertEqual(result["license"], "personal")

    def test_image_origin_and_paths_are_restricted(self):
        for url in ["http://img.aigengtu.com/meme/077.webp", "https://localhost/meme/077.webp",
                    "https://user@img.aigengtu.com/meme/077.webp", "https://img.aigengtu.com:443/meme/077.webp",
                    "https://img.aigengtu.com/secret", "https://img.aigengtu.com/meme/../077.webp"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                app.validate_image_url(url)
        for relative in ["../escape", "/absolute", "C:\\file", "a/../../b"]:
            with self.subTest(path=relative), self.assertRaises(ValueError):
                app.safe_path(self.root, relative)

    def test_gallery_keeps_only_deepseek_and_deduplicates_ids(self):
        item = {"preview": "https://img.aigengtu.com/0_preview/meme/077.webp", "name": "吃白饭"}
        data = {"gallery": {"DeepSeek娘": {"images": [item, item]}, "Claude娘": {"images": [item]}}}
        packs, rows = app.normalize_gallery(data)
        self.assertEqual(packs["gengjing"]["count"], 1)
        self.assertEqual(rows[0]["id"], "gengjing/077")

    def test_shared_cdn_image_is_not_repeated_in_search(self):
        other = dict(self.row, id="gengjing/077", pack="gengjing")
        self.index["packs"]["gengjing"] = dict(self.pack, id="gengjing")
        self.index["stickers"].append(other)
        self.assertEqual(len(app.select(self.root, self.index, "比心")), 1)
        self.assertEqual(app.select(self.root, self.index, "比心", pack="gengjing")[0]["pack"], "gengjing")

    def test_cdn_fetch_is_reused_offline_and_detects_tampering(self):
        def download(url, path, maximum):
            path.write_bytes(self.image)
        with patch.object(app, "download", side_effect=download) as call:
            first = app.fetch_one(self.root, self.index, self.row["id"])
            second = app.fetch_one(self.root, self.index, self.row["id"])
            self.assertEqual(call.call_count, 1)
        self.assertTrue(first["cached"])
        self.assertEqual(first["markdown"], second["markdown"])
        Path(first["path"]).write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            app.select(self.root, self.index, "比心")

    def test_html_response_is_not_installed_as_an_image(self):
        with patch.object(app, "download", side_effect=lambda url, path, maximum: path.write_bytes(b"<html>error</html>")):
            with self.assertRaisesRegex(ValueError, "not a supported image"):
                app.fetch_one(self.root, self.index, self.row["id"])
        self.assertFalse((app.pack_root(self.root, self.pack) / "a.jpg").exists())

    def archive(self, bad_license=False):
        path = self.root / "pack.zip"
        manifest = dict(self.pack)
        if bad_license:
            manifest["license"] = "MIT"
        with zipfile.ZipFile(path, "w") as bundle:
            bundle.writestr("manifest.json", json.dumps(manifest))
            bundle.writestr("a.jpg", self.image)
            bundle.writestr("../../escape", "never extracted")
        self.pack.update(archiveUrl="https://github.com/yyh-001/dsh-meme-packs/releases/download/demo/demo.zip",
                         sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        return path

    def test_archive_identity_checksum_and_whitelist(self):
        archive = self.archive()
        def download(url, path, maximum):
            path.write_bytes(archive.read_bytes())
        with patch.object(app, "download", side_effect=download):
            app.fetch_archive(self.root, self.pack, [self.row])
        self.assertTrue(app.cached_path(self.root, self.pack, self.row).is_file())
        self.assertFalse((self.root / "escape").exists())

    def test_archive_license_change_is_rejected_without_partial_pack(self):
        archive = self.archive(bad_license=True)
        with patch.object(app, "download", side_effect=lambda url, path, maximum: path.write_bytes(archive.read_bytes())):
            with self.assertRaisesRegex(ValueError, "license mismatch"):
                app.fetch_archive(self.root, self.pack, [self.row])
        self.assertFalse(app.pack_root(self.root, self.pack).exists())

    def test_failed_sync_preserves_existing_index(self):
        app.save_json(self.root / "index.json", {"old": True})
        with patch.object(app, "remote_json", side_effect=ValueError("offline")):
            with self.assertRaises(ValueError):
                app.sync(self.root)
        self.assertEqual(json.loads((self.root / "index.json").read_text()), {"old": True})

    def test_list_is_paginated_and_unknown_pack_is_explicit(self):
        self.assertEqual(app.select(self.root, self.index, limit=1, offset=1), [])
        with self.assertRaisesRegex(ValueError, "Unknown pack"):
            app.select(self.root, self.index, pack="missing")

    def diverse_index(self, sizes):
        packs, rows = {}, []
        for number, size in enumerate(sizes):
            key = f"pack-{number}"
            packs[key] = dict(self.pack, id=key, count=size)
            for position in range(size):
                identity = number * 1000 + position
                rows.append(dict(self.row, id=f"{key}/{position}.jpg", pack=key, path=f"{position}.jpg",
                                 url=f"https://img.aigengtu.com/0_preview/meme/{identity}.webp"))
        return {"packs": packs, "stickers": rows}

    def test_search_distributes_equal_matches_across_packs(self):
        index = self.diverse_index([20, 1, 1])
        results = app.select(self.root, index, "比心", limit=3, rng=random.Random(9))
        self.assertEqual({r["pack"] for r in results}, set(index["packs"]))

    def test_search_randomizes_ties_but_preserves_relevance(self):
        index = self.diverse_index([10])
        weaker = dict(index["stickers"][0], id="pack-0/weak", keywords="", caption="比心", name="比心")
        index["stickers"].append(weaker)
        rng = random.Random(12)
        choices = [app.select(self.root, index, "比心 开心", limit=1, rng=rng)[0]["id"] for _ in range(30)]
        self.assertGreater(len(set(choices)), 1)
        self.assertNotIn(weaker["id"], choices)

    def test_pick_balances_packs_instead_of_image_counts(self):
        index = self.diverse_index([1, 200])
        rng = random.Random(42)
        small = sum(app.pick(self.root, index, "比心", rng=rng)["pack"] == "pack-0" for _ in range(400))
        self.assertGreater(small, 150)
        self.assertLess(small, 250)
        self.assertFalse((self.root / "recent.json").exists())

    def test_pick_fetch_avoids_recent_images_and_rotates_sources(self):
        index = self.diverse_index([8, 8, 8])
        rng = random.Random(7)
        with patch.object(app, "download", side_effect=lambda url, path, maximum: path.write_bytes(self.image)):
            choices = [app.pick(self.root, index, "比心", fetch=True, rng=rng) for _ in range(21)]
        self.assertEqual(len({r["id"] for r in choices}), 21)
        for i in range(2, len(choices)):
            self.assertEqual(len({r["pack"] for r in choices[i-2:i+1]}), 3)
        self.assertTrue(all(r["cached"] and Path(r["path"]).is_file() for r in choices))
        history = app.recent_choices(self.root)
        self.assertEqual(len(history), app.RECENT_LIMIT)
        self.assertTrue(all(set(r) == {"id", "pack", "key"} for r in history))

    def test_pick_excludes_recent_cdn_aliases_across_packs(self):
        index = self.diverse_index([2, 1])
        first = index["stickers"][0]
        alias = index["stickers"][-1]
        alias["url"] = first["url"].replace("/0_preview/", "/")
        app.save_json(self.root / "recent.json", [{"id": first["id"], "pack": first["pack"], "key": app.image_key(first)}])
        choice = app.pick(self.root, index, "比心", rng=random.Random(2))
        self.assertEqual(choice["id"], index["stickers"][1]["id"])

    def test_small_pool_relaxes_history_without_immediate_repeat(self):
        index = self.diverse_index([1, 1])
        rng = random.Random(3)
        with patch.object(app, "download", side_effect=lambda url, path, maximum: path.write_bytes(self.image)):
            choices = [app.pick(self.root, index, "比心", fetch=True, rng=rng) for _ in range(5)]
        self.assertTrue(all(left["id"] != right["id"] for left, right in zip(choices, choices[1:])))

    def test_pick_pack_constraint_no_matches_and_no_sync(self):
        index = self.diverse_index([4, 4])
        self.assertEqual(app.pick(self.root, index, "比心", pack="pack-1")["pack"], "pack-1")
        with self.assertRaisesRegex(ValueError, "No matching"):
            app.pick(self.root, index, "no-match")
        with self.assertRaisesRegex(ValueError, "Extended catalog missing"):
            app.load(self.root)

    def test_failed_fetch_does_not_record_selection(self):
        with patch.object(app, "download", side_effect=ValueError("offline")):
            with self.assertRaisesRegex(ValueError, "offline"):
                app.pick(self.root, self.index, "比心", fetch=True)
        self.assertFalse((self.root / "recent.json").exists())

    def test_invalid_optional_history_is_ignored(self):
        for value in ["invalid", "null", '[{}, {"id": 4}, 2]']:
            (self.root / "recent.json").write_text(value)
            self.assertEqual(app.recent_choices(self.root), [])

    def test_pick_cli_uses_extended_index_and_tracks_only_explicit_fetch(self):
        app.save_json(self.root / "index.json", self.index)
        with patch.object(app, "download", side_effect=lambda url, path, maximum: path.write_bytes(self.image)):
            app.fetch_one(self.root, self.index, self.row["id"])
        script = SCRIPT.with_name("dafeiyu.py")
        env = dict(os.environ, DAFEIYU_LIBRARY_DIR=str(self.root))
        command = [sys.executable, str(script), "pick", "比心"]
        preview = subprocess.run(command, env=env, capture_output=True, text=True, check=True)
        self.assertTrue(json.loads(preview.stdout)["cached"])
        self.assertFalse((self.root / "recent.json").exists())
        fetched = subprocess.run(command + ["--fetch"], env=env, capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(fetched.stdout)["id"], self.row["id"])
        self.assertEqual(len(app.recent_choices(self.root)), 1)


if __name__ == "__main__":
    unittest.main()
