# SMOKE — V1 访客主路径（A）

日期：2026-10-29（Asia/Shanghai）  
范围：open → filter → lightbox → download。无 Duo 边框。

服务：`cd site/public && python3 -m http.server 8765` → http://127.0.0.1:8765/

| # | 步骤 | 期望 | 观察 |
|---|---|---|---|
| 1 | 打开首页 | 近黑底 + 琥珀按钮；hero 亮条可拖；印样格有图 | 待本机打开核对 |
| 2 | 搜索框输入 `ochre` | 只剩 Ochre alley（或含该词）；count 更新 | 待本机打开核对 |
| 3 | 清空搜索，点 Device **Fold** | 仅 `device_tags` 含 foldable 的帧 | 待本机打开核对 |
| 4 | 再点 Style **Nature**（与 Fold 组合） | 同时满足 foldable ∩ nature | 待本机打开核对 |
| 5 | 点 Ratio **Phone**（可再开） | 与机型/风格可组合；不符则空态 | 待本机打开核对 |
| 6 | 搜不到的词如 `zzzz` | 空态人话：*This batch does not have that yet…* | 待本机打开核对 |
| 7 | 点任意帧开灯箱 | 大图 + Ratio/Style/Devices/Batch date/Id；无手机边框 | 待本机打开核对 |
| 8 | 点 **Download** / **Save wallpaper** | **真落盘**：Downloads 出现 `wp-*.jpg`（fetch→blob，非导航 picsum） | **Pass**（2026-10-29）`wp-1029.jpg` 263229 B + `wp-1029 (1).jpg`；仍留 `127.0.0.1:8765`；截图 `foldable-smoke-shots/10-download-blob-*.png` |
| 9 | Esc 或 Close | 灯箱关闭 | 待本机打开核对 |
| 10 | 系统开「减少动态效果」 | 无入场位移/strip breathe；仍可筛可下 | 待本机打开核对 |

## 静态资源自检（可在 box 用 curl）

```bash
curl -sI http://127.0.0.1:8765/ | head -1
curl -s http://127.0.0.1:8765/data/wallpapers.json | head -c 120
curl -s http://127.0.0.1:8765/config/devices.json
```

期望：`index.html` 200；JSON 可读；`status=unlisted` 的 `wp-draft` 不出现在访客列表。

## 反 AI 味三问（书面）

1. 截掉标题是否仍像通用 AI 图库模板？→ 印样密度 + 暗室琥珀，非紫粉三列英雄。  
2. 有无具体品类词？→ phone / desktop / foldable wallpapers。  
3. 关动效能否用？→ 是（reduced-motion 已挂）。


## Box 静态自检结果（2026-10-29 Asia/Shanghai）

| 检查 | 结果 |
|---|---|
| `GET /` | 200 |
| `GET /wallpapers.js` | 200 |
| `GET /data/wallpapers.json` | 200；25 条，published 24，unlisted `wp-draft` 1 |
| `GET /config/devices.json` | 200；iphone / pixel / foldable |
| HTML 相对资源 | `src="wallpapers.js"`；脚本 fetch `data/` + `config/` |
| Duo / bezel 字样 | 无 |

浏览器交互步骤 1–10 的 **观察** 仍标「待本机打开核对」。


## 2026-10-29 Download 修单（Worker2）

- 问题：跨域 `<a download>` 被浏览器忽略 → 导航 picsum、不落盘（checker #8 Fail）。
- 修法：`downloadBlob` = `fetch(cors)` → `blob` → `URL.createObjectURL` → 临时 `<a download>` click；Download/Save 均走此路径。
- 顺手：灯箱属性与 showcase 标题改 `textContent`/DOM，去掉 manifest→`innerHTML`。
- 复测门槛：GUI 点 Download 后下载目录出现文件；再喊 checker。


## 2026-10-29 GUI 复测 #8（Worker2）

服务：`http://127.0.0.1:8765/`（`wallpaper-site-build/site/public`，与本机 `site/public` 同步）  
帧：Park towers haze / `wp-1029`

| 项 | 结果 |
|---|---|
| Download | **Pass** — blob 下载 `wp-1029.jpg`（263229 B，JPEG `ffd8ff`）；地址仍 `127.0.0.1:8765`；灯箱未关；未导航 picsum |
| Save wallpaper | **Pass** — 第二文件 `wp-1029 (1).jpg`（同大小） |
| 落盘路径 | `/home/box/Downloads/` |
| 截图 | `10-download-blob-lightbox-before.png` / `after-download` / `after-save` / `address-bar.png` |

修法摘要：`downloadBlob` = cors fetch → blob → objectURL → 临时 `<a download>`；顺手灯箱/showcase 去 `innerHTML`。

---

## V1 publish 冒烟（2026-11-01）

范围：生图目录 → `scripts/publish.py` → R2 + JSON；壳 `src()` 全 URL；`publishedOnly`。

| # | 步骤 | 期望 |
|---|---|---|
| P1 | `python3 scripts/publish.py --dir …/aigc-mvp1/out --dry-run` | 打印将上传的 key / cdn_url，不写盘 |
| P2 | （有 .env）去掉 `--dry-run` 发布一张 | R2 公开 URL 浏览器可开；JSON 有 `status: published` + `object_key` |
| P3 | `./scripts/smoke_local.sh` | PASS：published 进列表；`wp-draft` unlisted 被过滤；R2 全 URL 不拼 `/w/h` |
| P4 | `cd public && python3 -m http.server 8765`；curl `/` `/data/wallpapers.json` `/privacy/` `/robots.txt` | 均为 200 |
| P5 | `--unpublish <id>` | 该条 `status=unlisted`，首页消失 |

阻塞：无 R2 真密钥时跳过 P2；Aaron 填 `.env` 后执行：

```bash
.venv/bin/python scripts/publish.py --dir /workspace/aigc-mvp1/out --id mvp1-mock-llm-01 --title "Mock LLM 01"
npx wrangler pages deploy public --project-name=foldable-wallper-site
```
