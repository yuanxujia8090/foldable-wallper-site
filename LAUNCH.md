# Unfold Paper（Batch Light）上线操作手册

日期：2026-11-17（内容清理与品牌统一已执行，见 §1）  
目标域名：`https://unfoldpaper.com`（图床：`https://img.unfoldpaper.com`）  
栈：Cloudflare R2（公开读）+ Cloudflare Pages（静态 `public/`）  
本仓：`yuanxujia8090/foldable-wallper-site`（独立仓，勿合入 ZKK666/website）

日常下架 / 重跑 / 预览见 [OPS.md](./OPS.md)。访客冒烟见 [SMOKE.md](./SMOKE.md)。

---

## 0. 当前状态（2026-11-17 实测）

| 项 | 状态 |
|---|---|
| 图床 `img.unfoldpaper.com` | **可用**。真图 HTTP 200；带 `Origin: https://unfoldpaper.com` 时返回 `access-control-allow-origin`。`http://127.0.0.1:8765` 与 `*.pages.dev` **不在**允许列表，用这两个源下载会失败（见 §2.1） |
| 站点域名 | **未上线**。权威 DNS：`unfoldpaper.com` 无 A / CNAME 记录；`www.unfoldpaper.com`、`foldable-wallper-site.pages.dev` 均 NXDOMAIN。本机看到的 `198.19.*` 是本机代理的 fake-ip，与本结论无关 |
| 页面内容 | 25 张占位图已改 `unlisted`（24 张 picsum + `mist-01`），现 **29 张真图 published**；两页 HTML 里 `picsum` 出现 0 次；构建脚本会在发现占位域名时直接失败 |
| 品牌 | 页内统一 **Unfold Paper**，`Batch Light` 降为这一批次的代号（页脚 `Unfold Paper · Batch Light`） |
| 筛选 | 只剩 **搜索 + 风格**（暗/极简/自然/抽象各 10 张）。机型 chip（iPhone / Pixel）与比例 chip（手机/桌面）已移除：本批 29 张全是折叠屏，留着必然空态 |
| 本机 `.env` / `.venv` | 仍没有（要从本仓跑真上传前再建，见 §2.4） |
| 本地自检 | `python3 scripts/build_pages.py --check` 通过（29 items，四文件 in sync）；`./scripts/smoke_local.sh` 通过；headless 实测两页 51 张图 0 破图、无横向溢出、亮条 14 / 印样 29 / 秀栏 7 |

**结论：** 仓内内容已可公开展示；**唯一阻塞是 Pages 项目与自定义域还没建**，需要你登录 Cloudflare 操作。

---

## 1. 已定决策（2026-11-17，已执行）

1. **占位图**：24 张 picsum 全部 `unlisted`，只留 29 张真图（含 `mist-01` 也被下架）。
2. **机型 / 比例筛选**：iPhone、Pixel 两个 chip 与「手机 / 桌面」两个比例 chip 已从两页移除；页脚英文改 `2026 · Foldable batch only`、中文改 `2026 · 本批以折叠屏为主`。等有手机竖图批次再放回来。
3. **`mist-01`**：改 `unlisted`（R2 上的 `test-only/` 对象保留，没删）。要正式收录时再迁路径 + 改标题。
4. **品牌名**：对外统一 **Unfold Paper**；`<title>`、`<h1>`、About 正文、页脚都改了，`Batch Light` 只作批次代号。
5. **隐私 / 版权**：占位句换成联系方式 `hello@unfoldpaper.com`，页脚已加 `/privacy/`、`/copyright/` 链接（中英页都链到英文法律页）。
6. **favicon**：新增 `public/favicon.svg`（金色 U 字标），四个页面都引了。
7. **删除「Phone frames」区块**：本批没有手机竖图，该区块的静态内容全是占位图，直接删掉；「One lifted」秀栏保留并改为按数据生成。

**遗留待办（非阻塞）**：`hello@unfoldpaper.com` 这个邮箱还没建，需要用 Cloudflare Email Routing 转发到你常用信箱，否则页面上留的是一个收不到信的地址。

---

## 2. Cloudflare 一次性配置

### 2.1 R2（bucket 已有，只需核 CORS）

1. Bucket：文档约定名 `foldable-wallpapers`（以控制台实际为准）。
2. **Public access** 已开；自定义域 **`img.unfoldpaper.com`** 指向该 bucket（已实测出图）。
3. API Token：Object Read & Write → 记 Account ID / Access Key / Secret（填进 `.env`）。
4. **CORS 要补**：现在只允许 `https://unfoldpaper.com`。要支持 `*.pages.dev` 预览域和本机 `http://127.0.0.1:8765` 验下载，用仓里的 `r2-cors.json`（包含主域、`https://*.pages.dev`、127.0.0.1 与 localhost），不要把主域那条删了。两条路选一：

   - 控制台：R2 → bucket → Settings → CORS policy → 粘贴 `r2-cors.json` 全文 → Save。
   - 命令行（需先 `npx wrangler login`）：

     ```bash
     npx wrangler r2 bucket cors set <bucket-name> --file r2-cors.json
     npx wrangler r2 bucket cors list <bucket-name>   # 回读确认
     ```

   不改的后果：预览域与本机点 Download 会失败（`fetch`→blob 被浏览器跨源拦），正式域名不受影响。

5. **核对方法**：

   ```bash
   curl -sI -H "Origin: https://unfoldpaper.com" "https://img.unfoldpaper.com/<任一真图URL>" | grep -i access-control
   ```

   回 `access-control-allow-origin: https://unfoldpaper.com` 才算对。

### 2.2 Pages（**尚未做，这是当前阻塞项**）

任选其一（推荐先 A 验证，再绑 Git）：

**A. Wrangler 直推**

```bash
npx wrangler login   # 首次，需要浏览器授权
npx wrangler pages deploy public --project-name=foldable-wallper-site
```

**B. Git 接入**

- Cloudflare Dashboard → Pages → Connect to Git → `yuanxujia8090/foldable-wallper-site`
- Production branch：`main`
- Build command：**留空**
- Output directory：`public`

> 现在 `foldable-wallper-site.pages.dev` 是 NXDOMAIN，说明该名字下还没有成功部署过。

### 2.3 自定义域

1. Pages → Custom domains → 加 `unfoldpaper.com`（以及可选 `www`）。
2. DNS 按 CF 提示指到 Pages（橙云）。当前根域**一条记录都没有**，加完才会有 A/CNAME。
3. SSL 状态变 Active 后再测。
4. 确认 `public/config/site.json` 的 `origin` 为 `https://unfoldpaper.com`（已是），换域必须改这里并 `python3 scripts/build_pages.py`。

### 2.4 本机密钥与依赖（真上传才需要）

```bash
cp .env.example .env
# 填：R2_ACCOUNT_ID R2_ACCESS_KEY_ID R2_SECRET_ACCESS_KEY R2_BUCKET R2_PUBLIC_BASE_URL
# R2_PUBLIC_BASE_URL 示例：https://img.unfoldpaper.com（无尾斜杠）

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

`.env` 已在 `.gitignore`，**禁止提交**。

---

## 3. 推荐上线当天流程（可复制）

在仓库根目录执行。

### 3.1 看内容就够，不用再清占位图

占位图这一步已经做完了：`public/data/wallpapers.json` 里 24 张 picsum 与 `mist-01` 都是 `unlisted`。要再下架别的：

```bash
# 需要 .env 与 .venv；不下架则跳过
.venv/bin/python scripts/publish.py --unpublish <id>
# 或直接改 public/data/wallpapers.json 里对应条目 status → unlisted，改完必须 rebuild
```

中文标题 / alt / 搜索词：编辑 `public/data/wallpapers.zh-Hans.json`（`{id: {title, alt, searchTerms}}`）。缺条目时中文页退回英文。

### 3.2 重建静态页

```bash
python3 scripts/build_pages.py
python3 scripts/build_pages.py --check   # 期望全部 in sync，退出码 0
```

会重写：

- `public/index.html`、`public/zh/index.html` 内 `#app-data` 的 `items`
- hero 亮条（真图优先、按 `created_at` 新的优先，14 张）
- 接触印样 `#sheetGrid` 的无脚本兜底（全部已发布条目）
- 「One lifted」秀栏 `#showRun`（最新 7 张，第 3 张放大）与 `#showNote` 文案
- `#countLine` 计数文案
- `robots.txt`、`sitemap.xml`（来自 `site.json` 的 `origin`）

**注意两点：**

- 对**已在页面里**的条目，build 保留页面现有内容（`search` 索引是手写的），只追加新 id。所以改某条的中文覆盖后若文案没变，需先把该 id 从 `#app-data` 里清掉再 build。
- 上面四处图片 + 两个文案是每次全量重算的，手改会被覆盖。构建时若发现页面里还有 `picsum.photos`，会直接报错退出——这是故意的，防止占位图再混上线。

### 3.3 本地预览

```bash
./scripts/smoke_local.sh
cd public && python3 -m http.server 8765
# 打开 http://127.0.0.1:8765/ 与 /zh/
```

最少点一遍：搜索 → 风格筛选 → 灯箱 → Esc → `/zh/` 语言切换 → `/privacy/` `/copyright/` → `/favicon.svg`。

⚠️ 本机预览时 **Download 会失败**：R2 的 CORS 只允许 `https://unfoldpaper.com`。要本机验下载，先把 `http://127.0.0.1:8765` 加进 R2 CORS（§2.1）。线上域名下不受影响。

### 3.4 提交并部署

```bash
git status
# 确认无 .env
git add -A   # 或按需挑选；勿加 .env
git commit -m "…"
git push origin main
# 或：
npx wrangler pages deploy public --project-name=foldable-wallper-site
```

### 3.5 上线后核对（干净网络 / 无 WARP）

| 检查 | 期望 |
|---|---|
| `https://unfoldpaper.com/` | 200，英页 |
| `https://unfoldpaper.com/zh/` | 200，中页 |
| `https://unfoldpaper.com/privacy/` `…/copyright/` `…/robots.txt` `…/sitemap.xml` `…/favicon.svg` | 200 |
| 打开一张 `img.unfoldpaper.com` 的 full URL | 出图 |
| 灯箱 Download | Downloads 出现文件，地址栏仍在本站 |
| 列表总数 | 29 张，页脚写 `Foldable batch only`（中文页 `本批以折叠屏为主`） |
| 风格筛选 | 暗 / 极简 / 自然 / 抽象各 10 张，互不串味 |
| 搜索 `picsum` 或点机型 | 机型 chip 已移除；页面不应出现任何占位图 |

---

## 4. 上线后日常（发一张新图）

```bash
# 1) 上传 + 写 JSON（幂等，同 id 可重跑）
.venv/bin/python scripts/publish.py --dir /path/to/out --status published
# 或单张：
.venv/bin/python scripts/publish.py --dir /path/to/out --id my-id --title "My Title"

# 2) （可选）补中文
# 编辑 public/data/wallpapers.zh-Hans.json

# 3) 重建页面
python3 scripts/build_pages.py

# 4) 部署
npx wrangler pages deploy public --project-name=foldable-wallper-site
# 或 git push 触发 Pages
```

下架：

```bash
.venv/bin/python scripts/publish.py --unpublish <id>
python3 scripts/build_pages.py
# 再部署
```

**已知缺口（P2）：** 现仓里 29 张真图带 `img.thumb/strip/full` 三档；`scripts/publish.py` 只写单个 `cdn_url` + `object_key`。build 会用 `cdn_url` 兜底生成 `img` 块，所以**不会缺图**，但**缩略图 = 原图**：新批次一上线，列表和亮条会直接拉全尺寸 webp，首屏变重。给缩略图分档前，先对齐发布管线（让 `publish.py` 输出 `img{}`）。

---

## 5. 回滚

- **Pages：** Dashboard → Deployments → 选上一成功部署 → Retry / Rollback。
- **Git：** 在 `main` 上 `git revert` 后 push（勿强推除非你明确要求）。
- **单图：** `--unpublish <id>` + rebuild + 部署；默认不删 R2。
- **本轮内容改动：** 25 条只是把 `status` 改成 `unlisted`，把 `wallpapers.json` 里对应条目改回 `published` 再 build 即可复原；picsum 图仍在。

---

## 6. 未完成 / 风险清单（按优先级）

### P0 — 挡住「能给人看」

| # | 问题 | 证据 / 位置 |
|---|---|---|
| 1 | **站点还没上线**：根域无 A/CNAME 记录，`www` 与 `*.pages.dev` 均 NXDOMAIN | 权威 DNS 查询（2026-11-17）；需按 §2.2 / §2.3 建 Pages 项目并绑域 |
| 2 | **`hello@unfoldpaper.com` 还没建信箱** | `/privacy/`、`/copyright/` 已指向该地址。建法：Cloudflare Dashboard → Email → Email Routing → 启用（自动加 MX/TXT）→ Destination addresses 加你的真实信箱并收验证信 → Routing rules 把 `hello@unfoldpaper.com` 设成 Forward to 它。没做的话页面上那个地址收不到信 |
| 3 | **本机无 `.env`**，本仓跑不了真上传 / 真下架 CLI | 缺文件；不影响静态站上线 |

### P1 — 上线当天应处理

| # | 问题 | 说明 |
|---|---|---|
| 4 | **R2 CORS 只允许主域** | 仓里已备 `r2-cors.json`（含 `https://*.pages.dev`、`127.0.0.1:8765`、`localhost:8765`），按 §2.1 粘贴或 `wrangler r2 bucket cors set` 即可；没凭据时我做不了 |
| 5 | **中文法律页缺失** | 中文页脚链到英文 `/privacy/` `/copyright/`；V1 可接受 |
| 6 | **关于区块没有头像图** | 原 picsum 头像已删除，About 只剩文字；有真图再补 |
| 7 | 死 CSS 未清 | 已删的「Phone frames」区块样式、机型/比例 chip 样式仍在 `<style>` 里，不影响渲染 |
| 8 | `find.devicesAria` / `quiet.heading` 等字符串已无人使用 | 无害，后续清理 |

### P2 — 可跟进

| # | 问题 | 说明 |
|---|---|---|
| 9 | `publish.py` 与现网三档 `img{}` 格式不一致 | build 会兜底，但缩略图=原图，首屏变重（§4） |
| 10 | 中文覆盖只有 30 条（含已下架的 `mist-01`） | 现网 29 条都有中文 |
| 11 | `SMOKE.md` 浏览器步骤多数「待本机打开核对」 | 应用现网域名重跑一遍并改日期 |
| 12 | 无分析 / 无 404 页 / 无 Open Graph | V1 可接受，SEO 分享偏弱 |
| 13 | 机型维度缺失 | 29 张全是折叠屏；出手机竖图批次后恢复 chip 与「Phone frames」区块 |

### 明确可后置（V1 不做也不挡上线）

- 用户注册、后台、付费
- 真机边框预览（`devices.json` 已注明）
- 合入其他 website 仓

---

## 7. 最短路径（现在只剩部署）

1. 本轮改动已提交并 push 到 `origin/main`（`eba0900`）。
2. `npx wrangler login`（或 Dashboard 接 Git），建 Pages 项目 `foldable-wallper-site`。
3. 绑 `unfoldpaper.com`（和 `www`），等 SSL Active。
4. 干净网络打开 `/`、`/zh/`、`/privacy/`、`/copyright/`、`/robots.txt`、`/sitemap.xml`、`/favicon.svg`。
5. 点一张图 → Download，确认落盘且地址栏仍在本站。
6. 建 `hello@unfoldpaper.com` 转发（§6 P0#2 有步骤）。
7. 把 `r2-cors.json` 贴进 R2 CORS，方便用预览域验下载（§2.1）。

卡在「域名打不开」时：先看 Cloudflare Pages 是否有成功 Deployment、Custom domain 是否 Active，再查本机是否开了 WARP/代理（`198.19.*` 很像）。
