# Unfold Paper（Batch Light）上线操作手册

- 日期：2026-11-19（基线按当日只读核查改写；内容清理与品牌统一已在 `eba09005` 落地）
- 目标域名：`https://unfoldpaper.com`（图床：`https://img.unfoldpaper.com`）
- 栈：Cloudflare R2（公开读）+ Cloudflare Pages（静态 `public/`）
- 本仓：`yuanxujia8090/foldable-wallper-site`（独立仓，勿合入 ZKK666/website）
- 线上 R2 桶名：**`foldable`**（创建于 2026-11-07；不要另建或改用文档旧称 `foldable-wallpapers`）

日常下架 / 重跑 / 预览见 [OPS.md](./OPS.md)。访客冒烟见 [SMOKE.md](./SMOKE.md)。

---

## 0. 当前基线（2026-11-19 核查，Asia/Shanghai）

证据底稿：`/workspace/scratch/unfoldpaper-launch-prep-20261119.md`。本文件是仓内计划入口；本轮只保留本地文档补丁，不 push、不建 PR。

| 项 | 状态（实时，非沿用旧测试） |
|---|---|
| 代码 | GitHub `main` 与 Mac 规范仓 `/Users/yuanxj/Documents/github/foldable-wallper-site` 均为 `73bda355ac71678987a43faa2a72de7e939804aa`（2026-11-18 10:33:57 Asia/Shanghai）。Mac 当时工作树干净。本 box 验证在独立 worktree，不在 Mac 开发。 |
| 发布包 | 静态发布物就是仓内 `public/`（Pages build command 留空，output `public`）。无 `.github/` CI。 |
| 图床 `img.unfoldpaper.com` | **可用**。自定义域 SSL/ownership active。DoH HEAD `mineral-01/hd-q95.webp` → HTTP 200，`content-type: image/webp`，`content-length: 848632`。清单 29 张 published 的 thumb+full 共 58 个 key，与桶内 `wallpapers/*` 58 个对象全部对上（存在性对账，不是全量像素验收）。 |
| 线上 CORS | 只允许 `https://unfoldpaper.com` 与遗留 `http://localhost:3000`。主域已回 `access-control-allow-origin`。`http://127.0.0.1:8765`、`http://127.0.0.1:3000`、`*.pages.dev` **不在**允许列表。仓内 `r2-cors.json` 尚未应用到线上桶。本轮不改 CORS。 |
| 站点域名 | **未上线**。Cloudflare 本账户 Pages 项目数为 0，没有部署，也没有可回滚的旧 Pages 版本。zone `unfoldpaper.com` 为 active/full、plan 显示 `Free Website`；区记录只有 CNAME `img.unfoldpaper.com` → `public.r2.dev`（proxied）。DoH：apex 有 NS/SOA、无 A/AAAA/MX/TXT（NODATA）；`www.unfoldpaper.com` 与 `foldable-wallper-site.pages.dev` 为 NXDOMAIN。本机普通 DNS 若出现 `198.18.*` / `198.19.*` 是代理 fake-ip，不能当证据。 |
| 页面内容 | 55 条清单：29 published、26 unlisted（含 24 张 picsum + `mist-01` 等）。published 不含 picsum。风格实际为 dark 10 / abstract 10 / nature 9，无 published `minimal`（页上 Minimal chip 仍在，会空态）。`mist-01` 对象仍留在桶的 `test-only/`。 |
| 品牌与筛选 | 页内统一 **Unfold Paper**；筛选只剩搜索 + 风格。机型/比例 chip 已撤。 |
| 本机密钥 | 规范仓当时无 `.env` / `.env.local`。不影响静态首发。CLI 上传若以后要用，桶名必须填 `foldable`。正式凭据只走本机或 vault，不往聊天贴密钥。 |
| 待本人确认 | **Email Routing 未启用**（`enabled=false` / `unconfigured`，apex 尚无 MX/TXT）：页上 `hello@unfoldpaper.com` 目前收不到信，不挡静态页打开。可选处理见 §1，本轮不改站内地址、不索要目的邮箱、不启用 Routing。**账单接口 403**（无 Billing Read）：zone 显示 Free Website，但不能保证零费，也不可擅自开通或升级计费。两者都须 Aaron 本人在控制台确认，见 §6 与 §8。 |
| 浏览器实测（2026-11-19） | **未通过，当前产品阻塞**。DOM 29，风格 dark 10 / nature 9 / abstract 10 / minimal 0；搜索 `mineral-01` 到 1、恢复 29 均可。分类可视 FAIL：英页 `#find` / `#sheet` 滚动区截图全黑（父已 Read 确认）。高清灯箱 PASS。`http://localhost:3000` 抽查下载 PASS；`http://127.0.0.1:3000` 预期 CORS 失败 PASS，无新下载。`/zh/`、`/privacy/`、`/copyright/`、`/robots.txt`、`/sitemap.xml`、`/favicon.svg` 可开。只抽查 1 张（`mineral-01`），不是 29 张全验。截图与落盘 WebP 哈希见 `/workspace/scratch/unfoldpaper-verify-20261119/REPORT.md`。2026-11-19 08:07 Asia/Shanghai 运行时已核证：EN/ZH `#find`/`#sheet` 均有 `reveal is-in`，computed `opacity: 0`、`transform: translateY(20px)`，`visibility: visible`、`display: block`；图已解码。DevTools 中 `.js .reveal` 胜出，`.reveal.is-in` 被划掉，相同特异度 (0,2,0) 后规则胜。CEO 已于 08:00 给出最小可见性修复范围。本 worktree 已按根因只调整中英页 `<style>` 规则顺序（声明未改），待父派浏览器在新 SHA 上全新实测（须含 localhost 禁 JS 再恢复；禁 JS 本轮未核）。静态 cascade 回归不能替代该实测。 |

**结论：** 仓内清单与 R2 对象已对齐（存在性对账），这不等于验收通过，也不等于已经可以公开展示。分类可视失败的运行时根因已核证；CEO 于 2026-11-19 08:00 Asia/Shanghai 确定的最小范围是只修中英列表/分类滚动可见性（含必要页面样式同步与回归，不改风格内容、不重构）。本 worktree 已按该范围做源码顺序修复并留下静态回归，**不能声称可上线或浏览器已通过**。当前要等父派浏览器对修复后 SHA 做全新实测（含 localhost 禁 JS 再恢复）。最终审查仍由 CEO 独立安排。Pages 与自定义域仍未建，在复测通过之前不进入首发。

---

## 0.1 本阶段用例、范围与停点

### 用例

1. 查阅并冻结 2026-11-19 基线，避免把 PR1 / 旧 Worker3 / 2026-11-17 文档断言当成未复核的当前事实。
2. 在云端独立 worktree 核对 `73bda355` 真实静态发布包（`public/`）：清单与页面一致性、`--check`、本地 smoke、排密扫描（报告只写路径/规则/结果，不打印疑似密钥值）。
3. 改正文档与示例中的错误桶名（`foldable-wallpapers` → 现网 `foldable`）。
4. 提供本机只读 HTTP 预览（优先 `http://localhost:3000/`，以匹配线上已允许的 CORS），供随后浏览器实测：浏览列表、打开高清灯箱、下载。不规避 CORS，不改 Origin、代理或线上配置。
5. 把 Email Routing、账单 403、首发失败回撤方式写清楚，供 Aaron 决策。

### 范围与停点

做：只改上述文档与桶名口径；在 box 独立 worktree 验证 `public/`（只读托管预览）；记录 SHA、包 hash、清单、退出码与排密覆盖。

不做 / 停点：

- 不改业务功能或 `public/` 生成逻辑。若验证发现必须改代码才能继续，停止受影响部分并报告，不自行改功能代码。
- 不启用 CloudAgent，不在 Mac 做开发，不镜像 Mac，不 push、不建 PR、不对外提交。
- 不运行 `scripts/publish.py`（会读 `.env`，可写 R2）。不运行无 `--check` 的 `scripts/build_pages.py`（会重写页面与 crawl 文件）。
- 不改 R2 CORS、DNS、MX/TXT、权限、代理路由，不新建 Pages/桶，不部署，不升级套餐。
- 不索要邮箱或密钥，不改站内 `hello@unfoldpaper.com`。
- 旧测试、历史单例下载、PR1 仓外测试，不作为本轮通过证据。
- 源代码/产物不写入他人 checkout（含 `/workspace/foldable-wallper-site-repo` 的 `main` 工作树，以及 Mac 规范仓）。
- 可见性修复仅限中英列表/分类滚动区，以及必要的双页 `<style>` 同步与回归。不改风格内容，不重构，不用 Shell 开或操纵浏览器。最终渲染与禁 JS 复查由父派浏览器完成。执行方自检与静态 cascade 都不是独立审查，也不等于可上线。

### 可见性回归用例

1. **静态 cascade**（自动，须标明静态，不能替代浏览器）：在 JS 启用且 `#find` / `#sheet`（中英页）处于脚本 in-view 状态时，默认（非 reduced-motion）作者样式不得把该区域算成 opacity 0。不规定必须用某个选择器写法。入口：`python3 tests/test_list_visibility_cascade.py`。旧 SHA `73bda355` 应为红灯，修复后应为绿灯。
2. **`python3 scripts/build_pages.py --check`**：生成区（items / hero / 印样 / 秀栏 / 计数 / robots / sitemap）须仍 in sync。本修复不经过 `build_pages.py`（它不写 CSS）；两页 `<style>` 都是源，须保持同步。
3. **`./scripts/smoke_local.sh`**：既有发布过滤与下载名断言须保持通过。
4. **父派浏览器**（最终渲染，不用 Shell 开浏览器）：在修复后 SHA 上用 `http://localhost:3000/` 与 `/zh/` 全新实测 `#find` / `#sheet` 滚动可见性；并在 localhost **禁 JS 后恢复再验**（禁 JS 旧版未核）。抽查灯箱与下载仍用 localhost，不改 CORS。
5. 随后同版核对 check / smoke / 包 hash / 排密，并按 `heydamir-unslop` 做视觉退化检查（不是设计重做）。检查报告保留 Damir Sokolovsky / heydamir/unslop、CC BY 4.0 署名。最终审查仍由 CEO 独立安排。

---

## 1. 已定决策（2026-11-17 已执行，现行文件仍成立）

1. **占位图**：24 张 picsum 全部 `unlisted`，只留 29 张真图（`mist-01` 也被下架）。
2. **机型 / 比例筛选**：iPhone、Pixel 两个 chip 与「手机 / 桌面」两个比例 chip 已从两页移除；页脚英文改 `2026 · Foldable batch only`、中文改 `2026 · 本批以折叠屏为主`。等有手机竖图批次再放回来。
3. **`mist-01`**：改 `unlisted`（R2 上的 `test-only/` 对象保留，没删）。要正式收录时再迁路径 + 改标题。
4. **品牌名**：对外统一 **Unfold Paper**；`<title>`、`<h1>`、About 正文、页脚都改了，`Batch Light` 只作批次代号。
5. **隐私 / 版权**：占位句换成联系方式 `hello@unfoldpaper.com`，页脚已加 `/privacy/`、`/copyright/` 链接（中英页都链到英文法律页）。本轮不改这个地址。
6. **favicon**：新增 `public/favicon.svg`（金色 U 字标），四个页面都引了。
7. **删除「Phone frames」区块**：本批没有手机竖图，该区块的静态内容全是占位图，直接删掉；「One lifted」秀栏保留并改为按数据生成。

**遗留（不挡静态首发，但有实际影响）：** `hello@unfoldpaper.com` 还没收信。Email Routing 未启用时，访客按法律页/页脚发信会投递失败或进入空域，造成「写了联系方式却联系不到」的信任问题。可选处理（仅 Aaron 在控制台执行，本轮不做）：Cloudflare Dashboard → Email → Email Routing → 启用（将添加 MX/TXT；当前 apex 无 MX，不存在抢占已有邮箱的问题）→ Destination addresses 添加本人信箱并收验证信 → Routing rules 把 `hello@unfoldpaper.com` 设成 Forward 到该信箱。也可以暂缓，接受该地址暂时收不到信。不要为此改页面上的地址，也不要在聊天里收集目的邮箱。回撤：停用 Routing 并删除本次 MX/TXT。

---

## 2. Cloudflare 一次性配置（首发由 Aaron 本人执行）

### 2.1 R2（桶已有，只需核 CORS；本轮不改线上 CORS）

1. Bucket：现网名为 **`foldable`**。不要新建 `foldable-wallpapers`。
2. **Public access** 已开；自定义域 **`img.unfoldpaper.com`** 指向该桶（2026-11-19 已实测出图）。
3. API Token：Object Read & Write → 记 Account ID / Access Key / Secret（只填进本机 `.env` 或 vault，需要 CLI 上传时才建）。
4. **线上 CORS 现状**：允许 `https://unfoldpaper.com` 与 `http://localhost:3000`。要支持 `*.pages.dev` 预览域和本机 `http://127.0.0.1:8765`，需把仓里的 `r2-cors.json` 应用到桶 `foldable`（不要删掉主域那条）。这不是主域下载的前置，本轮也不执行。两条路选一（均须 Aaron 授权后亲自做）：

   - 控制台：R2 → `foldable` → Settings → CORS policy → 先保存当前规则，再粘贴 `r2-cors.json` 全文 → Save。
   - 命令行（需先 `npx wrangler login`）：

     ```bash
     npx wrangler r2 bucket cors set foldable --file r2-cors.json
     npx wrangler r2 bucket cors list foldable   # 回读确认
     ```

   不改的后果：预览域与 `127.0.0.1` 源点 Download 会失败（`fetch`→blob 被浏览器跨源拦）。`http://localhost:3000` 与正式域名不受影响。

5. **核对方法**（只读）：

   ```bash
   curl -sI -H "Origin: https://unfoldpaper.com" "https://img.unfoldpaper.com/<任一真图URL>" | grep -i access-control
   ```

   回 `access-control-allow-origin: https://unfoldpaper.com` 才算对。

### 2.2 Pages（**尚未做**；分类可视修复并复测通过之前，不进入首发）

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

> 2026-11-19：本账户 Pages 项目数为 0，账户内无同名项目。DoH 下 `foldable-wallper-site.pages.dev` 仍是 NXDOMAIN。账户内无冲突不证明该名全局可用，创建时仍须 Cloudflare 确认。

### 2.3 自定义域

以官方文档为准，不预先填写或猜测最终解析 IP：https://developers.cloudflare.com/pages/configuration/custom-domains/

2026-11-19 只读复核：zone `unfoldpaper.com` 已是本账户下 active/full 区，NS 已指向 `maya.ns.cloudflare.com` / `yahir.ns.cloudflare.com`。apex 与 `www` 当前没有 A / AAAA / CNAME，不构成绑域冲突。必须保留已有的 `img.unfoldpaper.com` CNAME → `public.r2.dev`（proxied）。

1. 先有 Pages 项目（§2.2），再在该项目 **Custom domains → Set up a domain** 添加 `unfoldpaper.com`（可选再加 `www`）。官方注明：必须先走 Pages 自定义域流程再让记录生效；只在 DNS 里手工加指向 Pages 的 CNAME、却未在项目里关联该域，会解析失败并出现 [522](https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-522/)。
2. 官方对「域名已作为本账户 Cloudflare zone、且 NS 已指向 Cloudflare」的说明：
   - apex：*If your nameservers are successfully pointed to Cloudflare, Cloudflare will proceed by creating a CNAME record for you.*
   - 已在 Cloudflare 管理的子域（如 `www`）：*If your site is already managed as a Cloudflare zone, the CNAME record will be added automatically after you confirm your DNS record.*
   - 若需手工对照（例如外部 DNS），文档中的记录形态是 CNAME，内容为 `<YOUR_SITE>.pages.dev`。本项目目标名是 `foldable-wallper-site`，对应 `foldable-wallper-site.pages.dev`，但该 `pages.dev` 要等项目成功创建后才存在。apex 由 Cloudflare 做 [CNAME flattening](https://developers.cloudflare.com/dns/cname-flattening/)，对外可能看到 A/AAAA，那是扁平化结果，**不要事先编造或填写 IP**。
3. 添加后在 DNS Records 回看实际记录（类型、名称、目标、是否橙云），确认没有改到 `img`。SSL 变为 Active 后再测。
4. `public/config/site.json` 的 `origin` 已是 `https://unfoldpaper.com`。若换域必须改这里并 `python3 scripts/build_pages.py`。

### 2.4 本机密钥与依赖（真上传才需要，静态首发可跳过）

```bash
cp .env.example .env
# 填：R2_ACCOUNT_ID R2_ACCESS_KEY_ID R2_SECRET_ACCESS_KEY R2_BUCKET R2_PUBLIC_BASE_URL
# R2_BUCKET=foldable
# R2_PUBLIC_BASE_URL=https://img.unfoldpaper.com（无尾斜杠）

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

`.env` 已在 `.gitignore`，**禁止提交**。不要把密钥贴到聊天。

---

## 3. 推荐上线当天流程（可复制；生产步骤仅 Aaron 执行）

在仓库根目录执行。发布包以 `73bda355` 的 `public/` 为准，除非随后另有已合并的同版变更。

### 3.1 看内容就够，不用再清占位图

占位图这一步已经做完了：`public/data/wallpapers.json` 里 24 张 picsum 与 `mist-01` 都是 `unlisted`。要再下架别的：

```bash
# 需要 .env 与 .venv；不下架则跳过
.venv/bin/python scripts/publish.py --unpublish <id>
# 或直接改 public/data/wallpapers.json 里对应条目 status → unlisted，改完必须 rebuild
```

中文标题 / alt / 搜索词：编辑 `public/data/wallpapers.zh-Hans.json`（`{id: {title, alt, searchTerms}}`）。缺条目时中文页退回英文。

### 3.2 重建静态页（仅内容变更后需要）

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

优先用 `http://localhost:3000/`（与线上已允许的 CORS 源一致）。`http://127.0.0.1:*` 会被跨源拦住 Download，这是线上 CORS 的真实限制，不要改 Origin 或代理来掩盖。

```bash
./scripts/smoke_local.sh   # 无密钥本地断言；会短暂改 wallpapers.json，退出时恢复
python3 tests/test_list_visibility_cascade.py   # 静态 cascade，不能替代浏览器
cd public && python3 -m http.server 3000 --bind 127.0.0.1
# 打开 http://localhost:3000/ 与 http://localhost:3000/zh/
# 若改用 8765 或 127.0.0.1，Download 会被现行 CORS 拦住（见 §2.1）
```

最少点一遍：搜索 → 风格筛选 → 灯箱高清 → Download 落盘 → Esc → `/zh/` 语言切换 → `/privacy/` `/copyright/` → `/favicon.svg`。

### 3.4 提交并部署（Aaron 本人；本轮文档补丁先不远程提交）

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
| 风格筛选 | 当前 published：dark 10、abstract 10、nature 9；页面仍有 Minimal chip，但本批 published 为 0，点开会空态。互不串味 |
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

## 5. 首发失败回撤（不是旧版回滚）

当前没有已成功的 Pages 部署，因此**不存在「滚回上一版站点」**。若 Aaron 的首次发布或绑域失败，做的是回撤，而不是回滚到旧生产版本：

- **Pages 项目刚创建、尚未绑域：** 停用或删除该项目（或保留但不要指向正式域）。Git 不必强推。R2 与 `img.unfoldpaper.com` 保持不动。
- **已绑自定义域：** 在 Pages 移除 `unfoldpaper.com` / `www`，并删除**本次新增**的 apex/www 记录。必须保留 `img.unfoldpaper.com` CNAME。
- **以后已有成功部署时：** Dashboard → Deployments → 选上一成功部署 → Rollback。Git 用 `git revert` 后 push（勿强推除非 Aaron 明确要求）。
- **单图：** `--unpublish <id>` + rebuild + 部署；默认不删 R2。
- **本轮内容改动（已在仓内）：** 25 条只是把 `status` 改成 `unlisted`，把 `wallpapers.json` 里对应条目改回 `published` 再 build 即可复原；picsum 图仍在。

生产部署、绑域、改 DNS、改 CORS、启用 Email Routing，只由 Aaron 本人执行。

---

## 6. 未完成 / 风险清单（按优先级，2026-11-19 复核）

### P0 — 挡住「能给人看」

| # | 问题 | 证据 / 位置 |
|---|---|---|
| 0 | **分类/列表可见性**：旧 SHA 英页 `#find` / `#sheet` 截图全黑，运行时已核证为相同特异度下 `.js .reveal` 盖过 `.reveal.is-in`。最小修复已在本 worktree 落地（只改中英页规则顺序）。 | 修复后的**父派浏览器全新实测尚未完成**（须含 localhost 禁 JS 再恢复）。静态 cascade 已在旧 SHA 红灯、修复后绿灯，不能当作渲染通过。未复测通过前不进入首发。 |
| 1 | **站点还没上线**：无 Pages 项目；apex 无 Web 记录；`www` 与 `*.pages.dev` 为 NXDOMAIN | Cloudflare 只读 GET 与 DoH（2026-11-19）。在 P0#0 的浏览器复测通过之前，不进入首发。 |
| 2 | **本机无 `.env`**，本仓跑不了真上传 / 真下架 CLI | 缺文件；不影响静态站本身，也不改变当前不可上线的判断 |

### 待 Aaron 本人确认（不挡静态页打开，不授权代处理）

| 项 | 现状 | 影响与可选处理 |
|---|---|---|
| Email Routing | 2026-11-19 只读：`enabled=false`，`status=unconfigured`；zone 无 MX/TXT | 页上联系地址目前收不到信。可选：Aaron 在控制台启用 Routing、验证目的信箱并转发（官方说明启用时会自动加 MX、DKIM，无 SPF 时再加 SPF；当前无 MX，不存在与其他邮服务冲突）。也可暂缓。不要改站内地址，不要在聊天收集目的邮箱，不要由他人代开。回撤：停用并删除本次 MX/TXT。文档：[Email Routing](https://developers.cloudflare.com/email-service/configuration/domains/)、[免费转发说明](https://developers.cloudflare.com/dns/manage-dns-records/how-to/email-records/) |
| 账单 / 是否零费 | 订阅接口 403，不能读用量或发票；zone plan 显示 Free Website | **不能保证零费**，也**不可擅自开通或升级计费**。上线前 Aaron 在控制台自行查看 Billing。免费档上限只作规划参考，见 §8，不是账单承诺 |

### P1 — 上线当天应处理

| # | 问题 | 说明 |
|---|---|---|
| 3 | **R2 CORS 尚未与 `r2-cors.json` 对齐** | 主域与 `http://localhost:3000` 已允许。`*.pages.dev` 与 `127.0.0.1` 源的 Download 会失败。本轮不改线上 CORS；若要预览域验下载，由 Aaron 按 §2.1 应用规则并可回写旧策略 |
| 4 | **中文法律页缺失** | 中文页脚链到英文 `/privacy/` `/copyright/`；V1 可接受 |
| 5 | **关于区块没有头像图** | 原 picsum 头像已删除，About 只剩文字；有真图再补 |
| 6 | 死 CSS 未清 | 已删的「Phone frames」区块样式、机型/比例 chip 样式仍在 `<style>` 里，不影响渲染 |
| 7 | `find.devicesAria` / `quiet.heading` 等字符串已无人使用 | 无害，后续清理 |

### P2 — 可跟进

| # | 问题 | 说明 |
|---|---|---|
| 8 | `publish.py` 与现网三档 `img{}` 格式不一致 | build 会兜底，但缩略图=原图，首屏变重（§4） |
| 9 | 中文覆盖只有 30 条（含已下架的 `mist-01`） | 现网 29 条都有中文 |
| 10 | `SMOKE.md` 浏览器步骤部分仍写已移除的机型 chip，且含历史日期结果 | 不能当本轮证据；应用现网域名重跑并改日期 |
| 11 | 无分析 / 无 404 页 / 无 Open Graph | V1 可接受，SEO 分享偏弱 |
| 12 | 机型维度缺失 | 29 张全是折叠屏；出手机竖图批次后恢复 chip 与「Phone frames」区块 |
| 13 | 排密 | 无 build 的静态站以 `public/` 为部署包，部署前即可扫、本 worktree 已扫该树。部署后回读线上产物是额外确认，不是部署前无法排密。 |

### 明确可后置（V1 不做也不挡上线）

- 用户注册、后台、付费
- 真机边框预览（`devices.json` 已注明）
- 合入其他 website 仓

---

## 7. 最短路径（分类可视修复并复测通过之前，不首发）

0. 最小可见性修复已按 CEO 范围落地，须由父派浏览器对**修复后 SHA** 全新实测（`http://localhost:3000/` 与 `/zh/` 的 `#find`/`#sheet` 可视；localhost 禁 JS 再恢复）。再按 `heydamir-unslop` 看修复后画面是否视觉退化（不是设计重做；截图须父派浏览器看，不用 Shell 开浏览器）。报告保留 Damir Sokolovsky / heydamir/unslop、CC BY 4.0 署名。最终审查仍由 CEO 独立安排；执行方自检不算独立审查。未完成前不部署，也不声称可上线。
1. 修复后发布包不再是 `73bda355` 的 `public/` 树，须以本 commit 的 `HEAD:public` 与新包哈希为准，不能沿用未修复包冒充已通过。文档与测试同在本地 worktree，等父协调后再考虑同步/PR。
2. 复测通过、独立审查完成之后，才由 Aaron 本人：`npx wrangler login`（或 Dashboard 接 Git），建 Pages 项目 `foldable-wallper-site`，发布当时的 `public/`。
3. 绑 `unfoldpaper.com`（和 `www`），等 SSL Active。不要动 `img` 记录。
4. 干净网络打开 `/`、`/zh/`、`/privacy/`、`/copyright/`、`/robots.txt`、`/sitemap.xml`、`/favicon.svg`，并确认分类/列表区域可见。
5. 点一张图 → Download，确认落盘且地址栏仍在本站。
6. 可选：建 `hello@unfoldpaper.com` 转发（§1 遗留段）。
7. 可选：把 `r2-cors.json` 应用到桶 `foldable`，方便用预览域或 `127.0.0.1` 验下载（§2.1）。`localhost:3000` 已允许。

卡在「域名打不开」时：先看 Cloudflare Pages 是否有成功 Deployment、Custom domain 是否 Active，再查本机是否开了 WARP/代理（`198.18.*` / `198.19.*` 很像）。

若首发失败：按 §5 回撤，而不是寻找不存在的旧生产版本回滚。

---

## 8. 最小单票代执行授权草案（只起草，尚未授权）

**状态：本稿不是授权。** 当前继续只做只读准备与本地验证：不代发布、不试写探测权限、不申请账号或新 key、不改 DNS/CORS/MX、不升级套餐。Aaron 将用手机在控制台操作。若以后要把最小生产动作交给他人代执行，只用这一张票勾选并明确确认；未确认前任何人不得执行下列生产写。

### 8.1 冻结要发布的包

| 项 | 值 |
|---|---|
| Git SHA | `73bda355ac71678987a43faa2a72de7e939804aa` |
| 提交说明 / 时间 | 文档：R2 CORS 规则落仓 + Email Routing 与部署步骤细化；2026-11-18 10:33:57 Asia/Shanghai |
| 发布目录 | `public/`（Pages：build command 留空，output `public`，production branch 若接 Git 则为 `main`） |
| 产物清单哈希 | `f77e62fcfa94bf57a598dc9a300259812a3a3e328d7ed1c3232f609148cfcbb6`（对 `public/` 13 个文件按路径、字节、每文件 sha256 排序后汇总；合计 221712 字节） |
| git tree | `HEAD:public` = `4965fff797d3255ca5561287def79d84dca1deda` |
| 仓库 | https://github.com/yuanxujia8090/foldable-wallper-site |

代执行前须再核：工作树干净，`git rev-parse HEAD` 与上面的 SHA 一致，或对 `public/` 重算清单哈希与上表一致。不一致则停止。

### 8.2 目标账户与冲突检查（2026-11-19 只读复核，未试写）

| 项 | 结果 |
|---|---|
| 账户 | 会话内唯一 standard 账户，Account ID `ccbfc8102912a2cf7b21006d1f460f9b`（账户 ID 不是密钥，可记入票面；不要在票面或聊天复制登录邮箱或 API 凭据） |
| Zone | `unfoldpaper.com`，Zone ID `66064a1144daae2c60aace8dd482c1c4`，active / full / 未 paused，plan 显示 `Free Website`，NS `maya.ns.cloudflare.com` / `yahir.ns.cloudflare.com` |
| Pages 项目名 | 目标名 `foldable-wallper-site`。本账户当前项目数 0，**本账户内无同名冲突**。这不证明该名在 Pages 全局可用；创建时仍须 Cloudflare 确认全局可用。 |
| DNS 冲突 | 区记录仅 1 条：CNAME `img.unfoldpaper.com` → `public.r2.dev`（proxied）。apex 与 `www` **无** A/AAAA/CNAME，绑 `unfoldpaper.com` / `www` **无现有 Web 记录冲突**。`img` 记录必须保留，不在授权范围内 |

### 8.3 若将来确认，本票仅允许的最小动作

默认不授权。若 Aaron 明确确认本票，允许且仅允许：

1. 在上述账户创建 Pages 项目 `foldable-wallper-site`，发布 §8.1 的 `public/`（Dashboard 直传或 Connect Git / wrangler pages deploy，不改构建命令、不改输出目录）。
2. 在该项目 Custom domains 添加 `unfoldpaper.com`，可选添加 `www`，按 §2.3 官方流程确认由 Cloudflare 创建记录；添加后回看 DNS，不得改 `img`。
3. 失败则按 §5 / §8.6 撤回，不得强推 git，不得删 R2 对象。

即使本票被确认，也**不包括**：改 R2 CORS、启用 Email Routing、升级或开通计费、新建或改名桶、申请 API token / 新 key、改站内邮箱、合并或推送未经 Aaron 同意的 git、对生产做权限试写。

### 8.4 绑 `unfoldpaper.com` 时的 DNS 动作（不猜 IP）

依据：https://developers.cloudflare.com/pages/configuration/custom-domains/（Pages Custom domains）

前提已满足：该域已是本账户 Cloudflare zone，NS 已指向 Cloudflare。

- 在 Pages 项目里添加自定义域并确认后，**由 Cloudflare 创建 CNAME**（apex 官方原句见 §2.3；已托管在 Cloudflare 的 `www` 会在确认 DNS 后自动加 CNAME）。
- 不要手工填写 A/AAAA 地址，不要使用示例 IP。若对外出现 A/AAAA，是 apex [CNAME flattening](https://developers.cloudflare.com/dns/cname-flattening/) 的解析结果，以控制台回看为准。
- 外部 DNS 场景下文档给出的形态是 `CNAME` → `<YOUR_SITE>.pages.dev`。本项目预期站点名为 `foldable-wallper-site.pages.dev`，须在项目创建成功后再核。
- 不经过 Pages 自定义域流程、只改 DNS，官方说明会 522。
- 撤回：删除本次为 Pages 新增的 apex/`www` 记录（或按官方步骤先改 DNS 再从项目卸域），保留 `img.unfoldpaper.com`。

### 8.5 免费资源上限（规划用，不是零费保证）

账单接口 403，**不能证明当前用量或保证零费**，也不可据此擅自开计费。下列为官方公开上限，供判断本包是否「看起来落在免费档规划内」：

- Pages Free（https://developers.cloudflare.com/pages/platform/limits/ ，文档更新 2026-09-05）：同时 1 个 build、每月 500 builds、单 build 20 分钟；每项目最多 100 个自定义域；每站点最多 20,000 文件、单文件 25 MiB；每账户最多 100 个 Pages 项目。另：新用 Pages 的账户前 48 小时可能暂时不能新建项目。本冻结包 13 个文件、最大页面约 71 KiB，远低于文件数与单文件上限。
- R2 Standard 免费档（https://developers.cloudflare.com/r2/pricing/ ，文档更新 2026-10-30）：10 GB-month 存储、每月 100 万次 Class A、1000 万次 Class B；出网 egress 免费。不适用于 Infrequent Access。现有桶 `foldable` 为 Standard，对象约 60 个；未读本月账单，故不能声称一定零费。
- Email Routing：官方写明可作为免费转发使用（https://developers.cloudflare.com/dns/manage-dns-records/how-to/email-records/）。限额见 https://developers.cloudflare.com/email-service/platform/limits/（每域 200 条规则、每账户 200 个目的地址、入库 25 MiB）。本票默认不启用。
- 免费 zone 的 DNS 记录配额见 https://developers.cloudflare.com/dns/manage-dns-records/（2024-09-01 后创建的免费区默认为 200 条/区）。本区现仅 1 条记录。

### 8.6 首发失败撤回

当前没有已成功的 Pages 部署，失败时是**撤回**，不是滚回旧生产版本。步骤与禁区见 §5（未绑域则停用或删除新项目；已绑域则卸域并删本次新增的 apex/`www` 记录；不改 `img`、不删 R2、不强制推 git）。

### 8.7 手机上 Aaron 本人可执行的最短步骤（默认仍由本人做，不视为已授权代发）

1. 打开 Cloudflare Dashboard（确认账户为 `ccbfc8102912a2cf7b21006d1f460f9b`）→ Workers & Pages → 创建 Pages 项目 `foldable-wallper-site`，上传或连接本仓 `public/`（空 build command）。
2. 部署完成后打开项目提供的 `*.pages.dev` 做一次冒烟（列表 29 张、无 picsum）。注意：该预览域当前不在线上 CORS 允许列表，Download 可能失败，这是预期，不要为此改 CORS。
3. Custom domains 添加 `unfoldpaper.com`（可选 `www`），确认让 Cloudflare 自动写记录；回看 DNS，确认 `img` 未改。等到 SSL Active。
4. 用干净网络（关 WARP/代理）打开 `https://unfoldpaper.com/` 与 `/zh/`，点 `mineral-01` 灯箱并 Download，文件名 `mineral-01.webp`，地址栏仍在本站。
5. 若失败：按 §8.6 撤回，再通知。不要升级套餐。

勾选（仅当 Aaron 以后要授权代执行时才填）：

- [ ] 我确认发布包 SHA 与产物哈希与 §8.1 一致
- [ ] 我确认目标就是账户 `ccbfc8102912a2cf7b21006d1f460f9b`、项目名 `foldable-wallper-site`、域 `unfoldpaper.com`
- [ ] 我已在控制台看过 Billing，接受可能产生费用，并禁止代执行人开通或升级计费
- [ ] 我授权按 §8.3 仅执行最小动作，失败按 §8.6 撤回
- [ ] 确认人 / 日期：____________
