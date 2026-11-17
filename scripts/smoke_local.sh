#!/usr/bin/env bash
# Local fake publish + publishedOnly assertion (no R2 keys required)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
JSON="$ROOT/public/data/wallpapers.json"
BACKUP="$JSON.smoke.bak"
cp "$JSON" "$BACKUP"
trap 'mv "$BACKUP" "$JSON"' EXIT

python3 - << PY
import json
from pathlib import Path
p = Path("$JSON")
doc = json.loads(p.read_text())
fake = {
    "id": "wp-smoke-local",
    "title": "Smoke local fake",
    "cdn_url": "https://picsum.photos/id/1015",
    "status": "published",
    "w": 1600,
    "h": 900,
    "ratio": "desktop",
    "style": "nature",
    "device_tags": ["desktop"],
    "tags": ["smoke"],
    "created_at": "2026-11-01",
    "batch_id": "smoke-local",
    "object_key": "wallpapers/wp-smoke-local/fake.png",
}
items = doc.get("items", [])
items = [i for i in items if i.get("id") != "wp-smoke-local"]
items.append(fake)
# ensure unlisted sample exists
if not any(i.get("id") == "wp-draft" for i in items):
    items.append({
        "id": "wp-draft",
        "title": "Draft (unlisted sample)",
        "cdn_url": "https://picsum.photos/id/999",
        "status": "unlisted",
        "w": 1600, "h": 900, "ratio": "desktop",
        "style": "minimal", "device_tags": ["desktop"], "tags": ["draft"],
        "created_at": "2026-10-29", "batch_id": "smoke-local", "object_key": "",
    })
doc["items"] = items
p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
print("wrote fake published + ensured wp-draft unlisted")
PY

# Assert publishedOnly logic (mirrors wallpapers.js)
node -e '
const fs = require("fs");
const doc = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
function publishedOnly(items) {
  return (items || []).filter(it => !it.status || it.status === "published");
}
const items = Array.isArray(doc) ? doc : (doc.items || []);
const pub = publishedOnly(items);
const ids = new Set(pub.map(i => i.id));
if (!ids.has("wp-smoke-local")) { console.error("FAIL: smoke published missing"); process.exit(1); }
if (ids.has("wp-draft")) { console.error("FAIL: unlisted wp-draft leaked"); process.exit(1); }
const draft = items.find(i => i.id === "wp-draft");
if (!draft || draft.status !== "unlisted") { console.error("FAIL: wp-draft missing"); process.exit(1); }
console.log("PASS publishedOnly: published=" + pub.length + " total=" + items.length + " excluded=wp-draft");
' "$JSON"

# real wallpapers.js: img block wins, download name keeps the real extension
node -e '
const fs = require("fs");
const path = require("path");
const root = process.argv[1];
const win = { document: { getElementById: () => null } };
new Function("window", fs.readFileSync(path.join(root, "wallpapers.js"), "utf8"))(win);
const webp = { id: "paper-01", download_filename: "paper-01.webp",
  img: { thumb: "https://img.example/t.webp", strip: "https://img.example/t.webp", full: "https://img.example/w/paper-01/hd-q95.webp" } };
const picsum = { id: "wp-1029", download_filename: "wp-1029.jpg",
  img: { thumb: "https://picsum.photos/id/1029/480/270", strip: "https://picsum.photos/id/1029/480/270", full: "https://picsum.photos/id/1029/1600/900" } };
if (win.T9_src(webp, "full") !== webp.img.full) { console.error("FAIL src full"); process.exit(1); }
if (win.T9_src(picsum, "thumb") !== picsum.img.thumb) { console.error("FAIL src thumb"); process.exit(1); }
if (win.T9_downloadName(webp, webp.img.full) !== "paper-01.webp") { console.error("FAIL downloadName webp"); process.exit(1); }
if (win.T9_downloadName(picsum, picsum.img.full) !== "wp-1029.jpg") { console.error("FAIL downloadName jpg"); process.exit(1); }
console.log("PASS wallpapers.js src() + downloadName()");
' "$ROOT/public"

echo "smoke_local OK"
