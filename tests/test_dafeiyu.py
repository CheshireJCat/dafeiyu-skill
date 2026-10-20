import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / "skills/dafeiyu/scripts/dafeiyu.py"
spec = importlib.util.spec_from_file_location("dafeiyu", SCRIPT)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class DafeiyuTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.payload = b"synthetic test data, not an upstream image"
        self.row = {"id": "bixin", "path": "memes/like/bixin.jpg", "tag": "like",
                    "caption": "双手比心", "keywords": "开心 比心",
                    "sha256": hashlib.sha256(self.payload).hexdigest()}

    def archive(self, missing=False):
        archive = self.root / "pack.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            if not missing:
                bundle.writestr(self.row["path"], self.payload)
            bundle.writestr("manifest.json", json.dumps({"id": "dafeiyu-001", "version": "1.3.0", "license": "personal"}))
            bundle.writestr("../../outside.txt", "must never be extracted")
        return archive, hashlib.sha256(archive.read_bytes()).hexdigest()

    def test_search_uses_semantics_and_does_not_invent_matches(self):
        self.assertEqual(app.search([self.row], "比心"), [self.row])
        self.assertEqual(app.search([self.row], "LIKE"), [self.row])
        self.assertEqual(app.search([self.row], "no-match"), [])

    def test_checksum_failure_leaves_destination_absent(self):
        archive, _ = self.archive()
        destination = self.root / "cache"
        with self.assertRaisesRegex(ValueError, "Archive checksum"):
            app.unpack(archive, destination, [self.row], "wrong")
        self.assertFalse(destination.exists())

    def test_only_known_files_are_installed_and_verified(self):
        archive, checksum = self.archive()
        destination = self.root / "cache"
        app.unpack(archive, destination, [self.row], checksum)
        app.verify(destination, [self.row])
        self.assertEqual(sorted(str(p.relative_to(destination)) for p in destination.rglob("*") if p.is_file()),
                         ["manifest.json", "memes/like/bixin.jpg"])
        self.assertFalse((self.root / "outside.txt").exists())

    def test_missing_member_does_not_leave_partial_install(self):
        archive, checksum = self.archive(missing=True)
        destination = self.root / "cache"
        with self.assertRaises(KeyError):
            app.unpack(archive, destination, [self.row], checksum)
        self.assertFalse(destination.exists())

    def test_existing_corrupt_cache_is_not_overwritten(self):
        archive, checksum = self.archive()
        destination = self.root / "cache"
        path = app.image_path(destination, self.row)
        path.parent.mkdir(parents=True)
        path.write_bytes(b"user changed this")
        with self.assertRaisesRegex(ValueError, "Image checksum"):
            app.unpack(archive, destination, [self.row], checksum)
        self.assertEqual(path.read_bytes(), b"user changed this")

    def test_markdown_uses_absolute_path_and_handles_spaces(self):
        result = app.rendered(self.root / "space here", self.row)
        self.assertTrue(Path(result["path"]).is_absolute())
        self.assertIn("space here", result["markdown"])
        self.assertIn("(<", result["markdown"])

    def test_paths_cannot_escape_cache(self):
        with self.assertRaisesRegex(ValueError, "leaves"):
            app.image_path(self.root, {"path": "../escape.jpg"})


if __name__ == "__main__":
    unittest.main()
