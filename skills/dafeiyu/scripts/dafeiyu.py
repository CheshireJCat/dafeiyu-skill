#!/usr/bin/env python3
"""Download a pinned personal-use pack or select local stickers. No uploads."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

PACK = "dafeiyu-001-v1.3.0"
URL = f"https://github.com/yyh-001/dsh-meme-packs/releases/download/{PACK}/{PACK}.zip"
SHA256 = "9fca6a4fc101232b39ab79181b9ed1b12289cf4890b3fadac89576545e51b3a4"
CATALOG = Path(__file__).resolve().parents[1] / "references/catalog.json"


def data_dir():
    value = os.environ.get("DAFEIYU_DATA_DIR")
    return Path(value).expanduser().resolve() if value else Path.home() / ".cache/dafeiyu-skill" / PACK


def catalog():
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def image_path(root, row):
    root = root.resolve()
    path = (root / row["path"]).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Image path leaves the cache directory")
    return path


def verify(root, rows):
    for row in rows:
        path = image_path(root, row)
        if not path.is_file():
            raise ValueError("Local pack is missing; run the fetch command first")
        if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError(f"Image checksum mismatch: {row['id']}; existing cache was not changed")


def unpack(archive, destination, rows, expected_sha=SHA256):
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected_sha:
        raise ValueError("Archive checksum mismatch; no images installed")
    if destination.exists():
        verify(destination, rows)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".dafeiyu-stage-", dir=destination.parent) as temporary:
        stage = Path(temporary) / "pack"
        stage.mkdir()
        with zipfile.ZipFile(archive) as bundle:
            # Only extract known images and the license manifest, never index.db or arbitrary entries.
            for name in [row["path"] for row in rows] + ["manifest.json"]:
                info = bundle.getinfo(name)
                if info.file_size > 2_000_000:
                    raise ValueError("Unexpected oversized pack member")
                target = image_path(stage, {"path": name})
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(bundle.read(info))
        manifest = json.loads((stage / "manifest.json").read_text(encoding="utf-8"))
        if (manifest.get("id"), manifest.get("version"), manifest.get("license")) != (
            "dafeiyu-001", "1.3.0", "personal"
        ):
            raise ValueError("Unexpected upstream pack identity or license")
        verify(stage, rows)
        stage.rename(destination)


def fetch(root, rows):
    if root.exists():
        verify(root, rows)
        return
    curl = shutil.which("curl")
    if not curl:
        raise ValueError("curl is required for fetch; local search needs only Python")
    print("Downloading upstream images for personal use; redistribution needs rights-holder permission.", file=sys.stderr)
    with tempfile.TemporaryDirectory(prefix="dafeiyu-download-") as temporary:
        archive = Path(temporary) / "pack.zip"
        subprocess.run([
            curl, "--fail", "--location", "--silent", "--show-error",
            "--proto", "=https", "--proto-redir", "=https", "--max-time", "60",
            "--max-filesize", "2000000", "--output", str(archive), URL,
        ], check=True, timeout=65)
        unpack(archive, root, rows)


def search(rows, query):
    tokens = query.casefold().split()
    scored = []
    for row in rows:
        haystack = " ".join(str(row[key]) for key in ("id", "tag", "caption", "keywords")).casefold()
        score = sum(token in haystack for token in tokens)
        if score:
            scored.append((score, row))
    return [row for _, row in sorted(scored, key=lambda item: -item[0])]


def rendered(root, row):
    path = image_path(root, row)
    # Angle brackets preserve paths with spaces in Markdown destinations.
    target = path.as_posix().replace("%", "%25").replace("<", "%3C").replace(">", "%3E")
    caption = row["caption"].replace("[", "").replace("]", "")
    return {"id": row["id"], "caption": row["caption"], "path": str(path),
            "markdown": f"![大肥鱼：{caption}](<{target}>)"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("fetch", help="Download personal-use images from the pinned upstream release")
    commands.add_parser("list", help="List all installed images without network access")
    find = commands.add_parser("search", help="Search IDs, tags, Chinese descriptions and keywords offline")
    find.add_argument("query")
    find.add_argument("--limit", type=int, choices=range(1, 25), default=3)
    args = parser.parse_args()
    try:
        root, rows = data_dir(), catalog()
        if args.command == "fetch":
            fetch(root, rows)
            print(json.dumps({"count": len(rows), "directory": str(root), "license": "personal"}, ensure_ascii=False))
        else:
            selected = rows if args.command == "list" else search(rows, args.query)[:args.limit]
            verify(root, selected)
            print(json.dumps([rendered(root, row) for row in selected], ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, subprocess.SubprocessError) as error:
        print(f"dafeiyu: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
