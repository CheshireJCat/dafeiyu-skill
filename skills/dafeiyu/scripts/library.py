"""Optional upstream catalogs and on-demand image cache; never redistributes images."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import random
import re
import shutil
import subprocess
import tempfile
from urllib.parse import urlparse
import zipfile

DSH_REV = "1004d77910a4612727b3aba17c683f4b75ec01e5"
DSH_BASE = f"https://raw.githubusercontent.com/yyh-001/dsh-meme-packs/{DSH_REV}"
GALLERY_URL = "https://aigengtu.com/gallery-index.json"
GALLERY_REPO = "https://github.com/the-beating-light-of-the-nail/deepseek-chan-meme-pack"
IMAGE_HOST = "img.aigengtu.com"
MAX_IMAGE = 8_000_000
MAX_ARCHIVE = 80_000_000
RECENT_LIMIT = 20


def root_dir():
    return Path(os.environ.get("DAFEIYU_LIBRARY_DIR", "~/.cache/dafeiyu-skill/library")).expanduser().resolve()


def safe_path(root, relative):
    part = PurePosixPath(relative)
    if not relative or part.is_absolute() or ".." in part.parts or "\\" in relative or ":" in relative:
        raise ValueError("Unsafe cache path")
    result = (root / relative).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError("Cache path leaves its root")
    return result


def validate_image_url(url):
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != IMAGE_HOST or parsed.username or parsed.password or parsed.port:
        raise ValueError("Unexpected image origin")
    if not re.fullmatch(r"/(?:0_preview/)?meme/\d+\.(?:webp|png|jpg|jpeg|gif)", parsed.path):
        raise ValueError("Unexpected image URL path")
    return url


def download(url, output, maximum):
    curl = shutil.which("curl")
    if not curl:
        raise ValueError("curl is required for explicit network operations")
    subprocess.run([curl, "--fail", "--location", "--silent", "--show-error", "--proto", "=https",
                    "--proto-redir", "=https", "--max-time", "45", "--max-filesize", str(maximum),
                    "--output", str(output), url], check=True, timeout=50)


def remote_json(url):
    with tempfile.TemporaryDirectory(prefix="dafeiyu-index-") as temporary:
        target = Path(temporary) / "index.json"
        download(url, target, 15_000_000)
        return json.loads(target.read_text(encoding="utf-8"))


def normalize_dsh(catalog, stickers):
    packs = {}
    for item in catalog["packs"]:
        key = item["id"]
        if not re.fullmatch(r"[a-z0-9-]+", key) or not re.fullmatch(r"[0-9A-Za-z.-]+", item["version"]):
            raise ValueError("Unexpected pack identity")
        pack = {k: item[k] for k in ("id", "name", "version", "license", "count")}
        pack["source"] = item.get("homepage", "https://github.com/yyh-001/dsh-meme-packs")
        pack["licenseSource"] = f"{DSH_BASE}/LICENSES.md"
        if key in ("maid-emoji", "whale-girl-emoji"):
            pack["attribution"] = "女仆鲸鱼娘二次设计：ZipZipPipe；角色原作：上善无形。合集其他作品见许可来源。"
        if item.get("archiveUrl"):
            url = item["archiveUrl"]
            prefix = "https://github.com/yyh-001/dsh-meme-packs/releases/download/"
            if not url.startswith(prefix) or not re.fullmatch(r"[a-f0-9]{64}", item.get("sha256", "")):
                raise ValueError("Unexpected archive origin or missing SHA-256")
            pack.update(archiveUrl=url, sha256=item["sha256"])
        packs[key] = pack
    rows = []
    for item in stickers["stickers"]:
        pack = packs[item["pack"]]
        relative = item["path"]
        safe_path(Path("/cache"), relative)
        row = {"id": f"{pack['id']}/{relative}", "pack": pack["id"], "path": relative,
               "name": item.get("name", item.get("caption", relative)),
               "caption": item.get("description") or item.get("caption", ""),
               "keywords": item.get("search") or str(item.get("keywords", "")), "tag": item.get("tag", "")}
        # Archive-backed packs always use their checksum-verified archive, never preview mirrors.
        if "archiveUrl" not in pack:
            row["url"] = validate_image_url(item["imageUrl"])
        rows.append(row)
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate sticker IDs")
    for key, pack in packs.items():
        if sum(row["pack"] == key for row in rows) != pack["count"]:
            raise ValueError(f"Catalog count mismatch for {key}")
    return packs, rows


def normalize_gallery(data):
    rows, seen = [], set()
    # The same site also hosts other characters; only this repository's DeepSeek collection applies.
    for item in data["gallery"]["DeepSeek娘"]["images"]:
        url = validate_image_url(item["preview"])
        number = re.search(r"/(\d+)\.", url).group(1)
        if number in seen:
            continue
        seen.add(number)
        story = item.get("story", {})
        rows.append({"id": f"gengjing/{number}", "pack": "gengjing", "path": f"{number}.webp",
                     "name": item.get("name") or item.get("alt", number),
                     "caption": item.get("alt") or item.get("name", number),
                     "keywords": " ".join(str(item.get(k, "")) for k in ("name", "alt", "alt_en")) +
                                 " " + (story.get("zh", "") if isinstance(story, dict) else ""),
                     "tag": "DeepSeek娘", "url": url})
    if not rows:
        raise ValueError("Empty DeepSeek gallery")
    # The live site's generated_at is informational; content hash gives each explicit sync a version.
    version = hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
    return {"gengjing": {"id": "gengjing", "name": "梗鲸 DeepSeek娘", "version": version,
                         "license": "noncommercial-fan", "count": len(rows), "source": GALLERY_REPO,
                         "licenseSource": GALLERY_REPO + "#版权与侵权举报--copyright"}}, rows


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(data, stream, ensure_ascii=False)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def sync(root):
    packs, rows = normalize_dsh(remote_json(f"{DSH_BASE}/catalog.json"), remote_json(f"{DSH_BASE}/stickers.json"))
    gallery_packs, gallery_rows = normalize_gallery(remote_json(GALLERY_URL))
    packs.update(gallery_packs)
    rows.extend(gallery_rows)
    result = {"schemaVersion": 1, "dshRevision": DSH_REV, "gallerySource": GALLERY_URL,
              "packs": packs, "stickers": rows}
    # No index is changed if any download or normalization failed.
    save_json(root / "index.json", result)
    return {"packs": len(packs), "entries": len(rows), "directory": str(root)}


def load(root):
    path = root / "index.json"
    if not path.is_file():
        raise ValueError("Extended catalog missing; run sync first")
    return json.loads(path.read_text(encoding="utf-8"))


def pack_root(root, pack):
    return safe_path(root, f"packs/{pack['id']}-{pack['version']}")


def cached_path(root, pack, row):
    directory = pack_root(root, pack)
    path = safe_path(directory, row["path"])
    receipt = directory / "checksums.json"
    if not path.is_file() or not receipt.is_file():
        return None
    hashes = json.loads(receipt.read_text(encoding="utf-8"))
    if hashlib.sha256(path.read_bytes()).hexdigest() != hashes.get(row["path"]):
        raise ValueError(f"Cached image checksum mismatch: {row['id']}")
    return path


def check_image(data):
    valid = (data.startswith(b"\xff\xd8\xff") or data.startswith(b"\x89PNG\r\n\x1a\n") or
             data.startswith((b"GIF87a", b"GIF89a")) or (data[:4] == b"RIFF" and data[8:12] == b"WEBP"))
    if not valid:
        raise ValueError("Downloaded content is not a supported image")


def fetch_archive(root, pack, rows):
    directory = pack_root(root, pack)
    if directory.exists():
        if all(cached_path(root, pack, row) for row in rows):
            return
        raise ValueError("Incomplete pack cache; existing files were not overwritten")
    directory.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".dafeiyu-pack-", dir=directory.parent) as temporary:
        archive = Path(temporary) / "pack.zip"
        download(pack["archiveUrl"], archive, MAX_ARCHIVE)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != pack["sha256"]:
            raise ValueError("Archive checksum mismatch")
        stage = Path(temporary) / "images"
        stage.mkdir()
        hashes = {}
        with zipfile.ZipFile(archive) as bundle:
            manifest = json.loads(bundle.read("manifest.json"))
            if any(manifest.get(key) != pack[key] for key in ("id", "version", "license")):
                raise ValueError("Pack identity or license mismatch")
            if sum(i.file_size for i in bundle.infolist()) > 150_000_000:
                raise ValueError("Oversized expanded pack")
            for row in rows:
                info = bundle.getinfo(row["path"])
                if info.file_size > MAX_IMAGE:
                    raise ValueError("Oversized image")
                content = bundle.read(info)
                check_image(content)
                target = safe_path(stage, row["path"])
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                hashes[row["path"]] = hashlib.sha256(content).hexdigest()
        (stage / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        save_json(stage / "checksums.json", hashes)
        stage.rename(directory)


def fetch_one(root, index, identity):
    row = next((r for r in index["stickers"] if r["id"] == identity), None)
    if row is None:
        raise ValueError("Unknown sticker ID; select an exact ID from search")
    pack = index["packs"][row["pack"]]
    if cached_path(root, pack, row):
        return result(root, index, row)
    if "archiveUrl" in pack:
        fetch_archive(root, pack, [r for r in index["stickers"] if r["pack"] == pack["id"]])
    else:
        directory = pack_root(root, pack)
        directory.mkdir(parents=True, exist_ok=True)
        destination = safe_path(directory, row["path"])
        if destination.exists():
            raise ValueError("Unverified existing file was not overwritten")
        with tempfile.TemporaryDirectory(prefix=".dafeiyu-image-", dir=directory) as temporary:
            image = Path(temporary) / "image"
            download(validate_image_url(row["url"]), image, MAX_IMAGE)
            content = image.read_bytes()
            check_image(content)
            receipt = directory / "checksums.json"
            hashes = json.loads(receipt.read_text()) if receipt.exists() else {}
            destination.parent.mkdir(parents=True, exist_ok=True)
            image.rename(destination)
            hashes[row["path"]] = hashlib.sha256(content).hexdigest()
            save_json(receipt, hashes)
    return result(root, index, row)


def result(root, index, row):
    pack = index["packs"][row["pack"]]
    path = cached_path(root, pack, row)
    output = {k: row[k] for k in ("id", "pack", "name", "caption")}
    output.update(license=pack["license"], source=pack["source"], cached=path is not None)
    for key in ("licenseSource", "attribution"):
        if key in pack:
            output[key] = pack[key]
    if path:
        target = path.as_posix().replace("%", "%25").replace("<", "%3C").replace(">", "%3E")
        label = re.sub(r"[\[\]\r\n]", " ", row["name"])
        output.update(path=str(path), markdown=f"![{label}](<{target}>)")
    else:
        output["fetchArgs"] = ["fetch", "--id", row["id"]]
    return output


def image_key(row):
    return row.get("url", row["id"]).replace("/0_preview/", "/")


def ranked(index, query=None, pack=None):
    if pack and pack not in index["packs"]:
        raise ValueError("Unknown pack; run packs to see available IDs")
    rows = [r for r in index["stickers"] if pack is None or r["pack"] == pack]
    if query is None:
        return [(0, row) for row in rows]
    tokens = query.casefold().split()
    scored = []
    for row in rows:
        haystack = " ".join(str(row[k]) for k in ("id", "name", "caption", "keywords", "tag")).casefold()
        score = sum(token in haystack for token in tokens)
        if score:
            scored.append((score, row))
    return sorted(scored, key=lambda pair: -pair[0])


def select(root, index, query=None, pack=None, limit=3, offset=0, rng=None):
    scored = ranked(index, query, pack)
    if query is None:
        return [result(root, index, row) for _, row in scored[offset:offset + limit]]
    rng = rng or random.SystemRandom()
    # Keep relevance order, but rotate equally relevant packs and shuffle within each pack.
    # Round-robin candidates keep a large gallery from occupying every result slot.
    levels = {}
    for score, row in scored:
        levels.setdefault(score, {}).setdefault(row["pack"], []).append(row)
    selected, seen = [], set()
    for groups in levels.values():
        packs = list(groups)
        rng.shuffle(packs)
        for rows in groups.values():
            rng.shuffle(rows)
        while packs:
            remaining = []
            for key in packs:
                rows = groups[key]
                while rows:
                    row = rows.pop()
                    identity = image_key(row)
                    if identity not in seen:
                        seen.add(identity)
                        selected.append(row)
                        break
                if len(selected) >= limit:
                    return [result(root, index, row) for row in selected]
                if rows:
                    remaining.append(key)
            packs = remaining
    return [result(root, index, row) for row in selected]


def recent_choices(root):
    try:
        data = json.loads((root / "recent.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    return [r for r in data if isinstance(r, dict) and
            all(isinstance(r.get(k), str) for k in ("id", "pack", "key"))][-RECENT_LIMIT:]


def pick(root, index, query=None, pack=None, fetch=False, rng=None):
    scored = ranked(index, query, pack)
    if not scored:
        raise ValueError("No matching stickers; try a shorter keyword")
    rng = rng or random.SystemRandom()
    # Randomness never promotes a weaker keyword match over the best match tier.
    rows = [row for score, row in scored if score == scored[0][0]]
    recent = recent_choices(root)
    seen = {r["key"] for r in recent}
    fresh = [row for row in rows if image_key(row) not in seen]
    if fresh:
        rows = fresh
    elif recent:
        # Small matching pools can exhaust the window; still avoid an immediate repeat if possible.
        rows = [row for row in rows if image_key(row) != recent[-1]["key"]] or rows
    groups = {}
    for row in rows:
        groups.setdefault(row["pack"], {})[image_key(row)] = row
    recent_packs = {r["pack"] for r in recent[-2:]}
    last_pack = recent[-1]["pack"] if recent else None
    packs = ([key for key in groups if key not in recent_packs] or
             [key for key in groups if key != last_pack] or list(groups))
    key = rng.choice(packs)
    row = rng.choice(list(groups[key].values()))
    output = fetch_one(root, index, row["id"]) if fetch else result(root, index, row)
    if fetch:
        # Selection history, not a delivery receipt. Record only after successful image verification.
        recent.append({"id": row["id"], "pack": key, "key": image_key(row)})
        save_json(root / "recent.json", recent[-RECENT_LIMIT:])
    return output
