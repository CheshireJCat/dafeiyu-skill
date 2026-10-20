import hashlib
import importlib.util
import json
from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()
