#!/usr/bin/env python3
"""Publish local wallpaper images to Cloudflare R2 and upsert public/data/wallpapers.json.

Idempotent: same --id (or derived id) overwrites the R2 object and JSON row.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = REPO_ROOT / "public" / "data" / "wallpapers.json"


def load_dotenv(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def env_cfg() -> dict[str, str]:
    file_env = load_dotenv(REPO_ROOT / ".env")
    keys = [
        "R2_ACCOUNT_ID",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_BUCKET",
        "R2_PUBLIC_BASE_URL",
    ]
    cfg = {}
    for k in keys:
        cfg[k] = os.environ.get(k) or file_env.get(k) or ""
    return cfg


def slug_id(stem: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "-", stem).strip("-").lower()
    return s or "wp"


def list_images(dir_path: Path) -> list[Path]:
    files = sorted(
        p for p in dir_path.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    )
    if not files:
        raise SystemExit(f"no images in {dir_path}")
    return files


def read_manifest(path: Path) -> dict:
    if not path.is_file():
        return {"generated_at": "", "batch_id": "", "items": []}
    doc = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(doc, list):
        return {"generated_at": "", "batch_id": "", "items": doc}
    doc.setdefault("items", [])
    return doc


def write_manifest(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def public_url(base: str, key: str) -> str:
    return base.rstrip("/") + "/" + key.lstrip("/")


def guess_dims(path: Path) -> tuple[int, int]:
    """Best-effort PNG/JPEG size without extra deps; fallback 1600x900."""
    data = path.read_bytes()[:64]
    try:
        if path.suffix.lower() == ".png" and data[:8] == b"\x89PNG\r\n\x1a\n":
            w = int.from_bytes(data[16:20], "big")
            h = int.from_bytes(data[20:24], "big")
            if w > 0 and h > 0:
                return w, h
        if path.suffix.lower() in {".jpg", ".jpeg"} and data[:2] == b"\xff\xd8":
            # scan SOF; may need more bytes
            raw = path.read_bytes()
            i = 2
            while i < len(raw) - 9:
                if raw[i] != 0xFF:
                    i += 1
                    continue
                marker = raw[i + 1]
                if marker in (0xC0, 0xC1, 0xC2):
                    h = int.from_bytes(raw[i + 5 : i + 7], "big")
                    w = int.from_bytes(raw[i + 7 : i + 9], "big")
                    return w, h
                if marker in (0xD8, 0xD9):
                    i += 2
                    continue
                length = int.from_bytes(raw[i + 2 : i + 4], "big")
                i += 2 + length
    except Exception:
        pass
    return 1600, 900


def ratio_for(w: int, h: int) -> str:
    if h >= w * 1.4:
        return "phone-portrait"
    if 0.7 <= (w / h) <= 1.4 and w >= 1000:
        return "foldable"
    return "desktop"


def upsert_item(items: list, item: dict) -> None:
    for i, old in enumerate(items):
        if old.get("id") == item["id"]:
            merged = dict(old)
            merged.update(item)
            items[i] = merged
            return
    items.append(item)


def r2_client(cfg: dict):
    try:
        import boto3
        from botocore.config import Config
    except ImportError as e:
        raise SystemExit(
            "boto3 missing. Create venv: python3 -m venv .venv && "
            ".venv/bin/pip install -r requirements.txt"
        ) from e
    endpoint = f"https://{cfg['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com"
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=cfg["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=cfg["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def require_r2(cfg: dict) -> None:
    missing = [k for k, v in cfg.items() if not v]
    if missing:
        raise SystemExit(
            "missing R2 env: " + ", ".join(missing) + " (copy .env.example → .env)"
        )


def upload_one(
    client,
    cfg: dict,
    local: Path,
    item_id: str,
    *,
    dry_run: bool,
) -> str:
    key = f"wallpapers/{item_id}/{local.name}"
    ctype = mimetypes.guess_type(local.name)[0] or "application/octet-stream"
    print(f"  upload s3://{cfg['R2_BUCKET']}/{key}  ({local})  content-type={ctype}")
    if dry_run:
        return key
    client.upload_file(
        str(local),
        cfg["R2_BUCKET"],
        key,
        ExtraArgs={"ContentType": ctype, "CacheControl": "public, max-age=31536000"},
    )
    return key


def cmd_unpublish(args: argparse.Namespace) -> None:
    cfg = env_cfg()
    path = Path(args.manifest)
    doc = read_manifest(path)
    found = None
    for it in doc["items"]:
        if it.get("id") == args.unpublish:
            found = it
            break
    if not found:
        raise SystemExit(f"id not found: {args.unpublish}")
    print(f"unpublish {args.unpublish}: status → unlisted")
    if args.delete_object and found.get("object_key"):
        print(f"  delete object {found['object_key']}")
        if not args.dry_run:
            require_r2(cfg)
            client = r2_client(cfg)
            client.delete_object(Bucket=cfg["R2_BUCKET"], Key=found["object_key"])
    if args.dry_run:
        print("dry-run: JSON not written")
        return
    found["status"] = "unlisted"
    doc["generated_at"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    write_manifest(path, doc)
    print(f"wrote {path}")


def cmd_publish(args: argparse.Namespace) -> None:
    cfg = env_cfg()
    directory = Path(args.dir)
    if not directory.is_dir():
        raise SystemExit(f"not a directory: {directory}")
    images = list_images(directory)
    if args.id and len(images) > 1:
        raise SystemExit("--id requires a directory with exactly one image (or pass a single file via --dir parent + filter)")

    if args.id:
        # Prefer matching filename stem; else first image
        match = [p for p in images if slug_id(p.stem) == slug_id(args.id) or p.stem == args.id]
        images = match or images[:1]

    path = Path(args.manifest)
    doc = read_manifest(path)
    batch_id = datetime.now().strftime("%Y-%m-%d") + "-pub"
    now_date = datetime.now().strftime("%Y-%m-%d")

    client = None
    if not args.dry_run:
        require_r2(cfg)
        client = r2_client(cfg)
    else:
        # dry-run may still show planned public URLs if base is set
        if not cfg.get("R2_PUBLIC_BASE_URL"):
            cfg["R2_PUBLIC_BASE_URL"] = "https://example.r2.dev"
        if not cfg.get("R2_BUCKET"):
            cfg["R2_BUCKET"] = "DRY_BUCKET"

    for local in images:
        item_id = slug_id(args.id) if args.id else slug_id(local.stem)
        w, h = guess_dims(local)
        title = args.title or local.stem.replace("_", " ").replace("-", " ")
        print(f"publish id={item_id} file={local.name} {w}x{h}")
        key = upload_one(client, cfg, local, item_id, dry_run=args.dry_run)
        cdn = public_url(cfg["R2_PUBLIC_BASE_URL"], key)
        item = {
            "id": item_id,
            "title": title,
            "cdn_url": cdn,
            "status": args.status,
            "w": w,
            "h": h,
            "ratio": ratio_for(w, h),
            "style": args.style,
            "device_tags": args.device_tags,
            "tags": args.tags,
            "created_at": now_date,
            "batch_id": batch_id,
            "object_key": key,
        }
        print(f"  cdn_url={cdn}")
        print(f"  status={args.status} object_key={key}")
        if not args.dry_run:
            upsert_item(doc["items"], item)

    if args.dry_run:
        print("dry-run: no upload, JSON unchanged")
        return

    doc["generated_at"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    doc["batch_id"] = batch_id
    write_manifest(path, doc)
    print(f"wrote {path} ({len(doc['items'])} items)")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Publish wallpapers to R2 + wallpapers.json")
    p.add_argument("--dir", help="local directory of images to publish")
    p.add_argument("--status", choices=["published", "unlisted"], default="published")
    p.add_argument("--dry-run", action="store_true", help="print actions only")
    p.add_argument("--id", help="force item id (single image)")
    p.add_argument("--title", help="force title (with --id or single file)")
    p.add_argument("--unpublish", metavar="ID", help="set status=unlisted for id")
    p.add_argument("--delete-object", action="store_true", help="with --unpublish, also delete R2 object")
    p.add_argument("--manifest", default=str(DEFAULT_JSON), help="path to wallpapers.json")
    p.add_argument("--style", default="ai")
    p.add_argument("--device-tags", nargs="*", default=["foldable", "desktop"])
    p.add_argument("--tags", nargs="*", default=["ai"])
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.unpublish:
        cmd_unpublish(args)
        return
    if not args.dir:
        raise SystemExit("need --dir <outdir> or --unpublish <id>")
    cmd_publish(args)


if __name__ == "__main__":
    main()
