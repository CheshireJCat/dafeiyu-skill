#!/usr/bin/env python3
"""Select local stickers or explicitly sync and fetch upstream packs. No uploads."""
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
    get = commands.add_parser("fetch", help="Download the original pack, a selected pack, or one catalog image")
    target = get.add_mutually_exclusive_group()
    target.add_argument("--id", help="Exact sticker ID returned by extended search")
    target.add_argument("--pack", help="Archive-backed pack ID returned by packs")
    listing = commands.add_parser("list", help="List catalog entries without network access")
    listing.add_argument("--pack")
    listing.add_argument("--limit", type=int, choices=range(1, 101), default=24)
    listing.add_argument("--offset", type=int, default=0)
    commands.add_parser("sync", help="Explicitly sync DSH packs and the full GengJing DeepSeek catalog")
    commands.add_parser("packs", help="List synced pack IDs, counts and licenses offline")
    find = commands.add_parser("search", help="Search IDs, tags, Chinese descriptions and keywords offline")
    find.add_argument("query")
    find.add_argument("--limit", type=int, choices=range(1, 25), default=3)
    find.add_argument("--pack", help="Restrict extended search to a pack ID")
    choose = commands.add_parser("pick", help="Pick a relevant random image across packs; requires sync")
    choose.add_argument("query", nargs="?", help="Optional keywords; omit only for unrestricted random selection")
    choose.add_argument("--pack", help="Use a specific pack only when requested")
    choose.add_argument("--fetch", action="store_true", help="Explicitly fetch/verify the selected image and remember it")
    args = parser.parse_args()
    try:
        import library
        extended_root = library.root_dir()
        use_extended = args.command in ("sync", "packs", "pick") or bool(getattr(args, "id", None)) or bool(getattr(args, "pack", None))
        use_extended = use_extended or (args.command in ("search", "list") and (extended_root / "index.json").is_file())
        if use_extended:
            if args.command == "sync":
                output = library.sync(extended_root)
            else:
                index = library.load(extended_root)
                if args.command == "packs":
                    output = list(index["packs"].values())
                elif args.command == "pick":
                    output = library.pick(extended_root, index, args.query, args.pack, args.fetch)
                elif args.command == "fetch":
                    if args.id:
                        output = library.fetch_one(extended_root, index, args.id)
                    else:
                        pack = index["packs"].get(args.pack)
                        if not pack or "archiveUrl" not in pack:
                            raise ValueError("Choose an archive pack from packs; CDN galleries use fetch --id")
                        entries = [r for r in index["stickers"] if r["pack"] == args.pack]
                        library.fetch_archive(extended_root, pack, entries)
                        output = {"pack": args.pack, "count": len(entries), "license": pack["license"]}
                else:
                    if getattr(args, "offset", 0) < 0:
                        raise ValueError("offset must not be negative")
                    output = library.select(extended_root, index, getattr(args, "query", None), args.pack,
                                            args.limit, getattr(args, "offset", 0))
            print(json.dumps(output, ensure_ascii=False, indent=2))
            return 0
        root, rows = data_dir(), catalog()
        if args.command == "fetch":
            fetch(root, rows)
            print(json.dumps({"count": len(rows), "directory": str(root), "license": "personal"}, ensure_ascii=False))
        else:
            if args.command == "list" and args.offset < 0:
                raise ValueError("offset must not be negative")
            selected = rows[args.offset:args.offset + args.limit] if args.command == "list" else search(rows, args.query)[:args.limit]
            verify(root, selected)
            print(json.dumps([rendered(root, row) for row in selected], ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, subprocess.SubprocessError) as error:
        print(f"dafeiyu: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
