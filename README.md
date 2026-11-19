# Foldable Wallpaper Site（图片站 V1）

**用户目标：** 尽快可上线的折叠壁纸静态站：无用户注册；管理员能发布；打通 生图→R2→JSON→Pages；全免费额度栈。

独立仓：`yuanxujia8090/foldable-wallper-site`。Aaron 自管 Cloudflare（R2 + Pages）。**不要**合入 ZKK666/website。

## 架构（最小）

```
本地出图目录 → scripts/publish.py → Cloudflare R2（公开读）
                              ↘ public/data/wallpapers.json
                                  ↘ scripts/build_pages.py → 页面 #app-data（items）
访客浏览器 ← Cloudflare Pages（部署 public/）← 页面自带 data，不在运行时取 JSON
```

- 无账号、无后端。管理员本机持有 `.env` 跑 CLI。
- 访客只看见 `status === "published"`（或缺省）；`unlisted` 不下架删对象，只不进列表。
- **改完数据必须重建页面**：`python3 scripts/build_pages.py`（`--check` 只看是否漂移）。重建会写入六处生成物：页面里的 `items`、hero 亮条（14 张）、接触印样 `#sheetGrid` 的无脚本兜底（全部已发布）、`#showRun`（最新 7 张，第 3 张放大）、`#countLine` / `#showNote` 文案，以及 `robots.txt` / `sitemap.xml`。
- 这四处图片都从已发布条目自动挑，按 `created_at` 新的优先；手动改会被下次 build 覆盖。构建时会拒绝写出仍含 `picsum.photos` 的页面。

## Aaron 上线步骤

### 1. Cloudflare R2

1. 使用已有 bucket **`foldable`**（不要另建 `foldable-wallpapers`）。
2. 开启 **Public access**（R2.dev subdomain 或自定义域）。
3. 建 API Token：Object Read & Write，记下 Account ID / Access Key / Secret。

### 2. 填环境变量

```bash
cp .env.example .env
# 编辑 .env：R2_ACCOUNT_ID R2_ACCESS_KEY_ID R2_SECRET_ACCESS_KEY R2_BUCKET R2_PUBLIC_BASE_URL
```

`R2_PUBLIC_BASE_URL` 示例：`https://pub-xxxx.r2.dev`（无尾斜杠）。

### 3. 依赖

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 4. 发布一张样图

```bash
# 先看计划（无密钥也可）
.venv/bin/python scripts/publish.py --dir /path/to/out --dry-run

# 真上传 + 写 JSON（需 .env）
.venv/bin/python scripts/publish.py --dir /path/to/out --status published
# 或指定单张 id/标题
.venv/bin/python scripts/publish.py --dir /path/to/out --id mvp1-mock-llm-01 --title "Mock LLM 01"
```

幂等：同 id 覆盖 R2 对象与 JSON 行，失败可重跑。

### 5. 部署 Pages

任选其一：

```bash
# CLI 直推静态目录
npx wrangler pages deploy public --project-name=foldable-wallper-site
```

或：Cloudflare Dashboard → Pages → Connect Git → 本仓 `main`，构建输出目录填 `public`（无构建命令）。

部署后确认 `public/config/site.json` 的 `origin` 是真实域名（`robots.txt` 与 `sitemap.xml` 都由它生成，不要手改这两个文件）。

### 6. 冒烟清单

| 检查 | 期望 |
|------|------|
| 浏览器打开某条 `cdn_url` | R2 公开 URL 直接出图 |
| `GET /data/wallpapers.json` | 含该条且 `status: published` |
| 首页列表 | 该条可见；`wp-draft`（unlisted）不可见 |
| `GET /privacy/` `GET /copyright/` `GET /robots.txt` | 200 |

无 R2 密钥时本地冒烟：

```bash
./scripts/smoke_local.sh
python3 tests/test_list_visibility_cascade.py   # 静态 cascade 回归，不能替代浏览器渲染验收
cd public && python3 -m http.server 8765
```

`public/config/site.json` 只有一个 `origin` 字段，`robots.txt` 与 `sitemap.xml` 由 `scripts/build_pages.py` 按它生成。换域名改这里，再跑一次 build。

## 数据形状（wallpapers.json item）

`id, title, cdn_url, status (published|unlisted), w, h, ratio, style, device_tags[], tags[], created_at, batch_id, object_key`

`cdn_url` 为完整公开读 URL 时，壳 `wallpapers.js` 的 `src()` **不再**拼 picsum 风格 `/w/h`。旧 picsum 前缀仍兼容。

## PR / 分支说明

空仓首次可直接推 `main`（本 V1 即如此）。若走 PR：分支 `feat/v1-publish`，**draft** PR，描述写清「独立仓、Aaron 自管 CF，勿碰 website」。

## 运维 / 上线

- **首次上线操作手册：** [LAUNCH.md](./LAUNCH.md)（含未完成清单）
- 日常运维：[OPS.md](./OPS.md)
- 访客冒烟：[SMOKE.md](./SMOKE.md)
