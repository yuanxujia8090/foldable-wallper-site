# Foldable Wallpaper Site（图片站 V1）

**用户目标：** 尽快可上线的折叠壁纸静态站：无用户注册；管理员能发布；打通 生图→R2→JSON→Pages；全免费额度栈。

独立仓：`yuanxujia8090/foldable-wallper-site`。Aaron 自管 Cloudflare（R2 + Pages）。**不要**合入 ZKK666/website。

## 架构（最小）

```
本地出图目录 → scripts/publish.py → Cloudflare R2（公开读）
                              ↘ 更新 public/data/wallpapers.json
访客浏览器 ← Cloudflare Pages（部署 public/）← JSON + 壳 HTML/JS
```

- 无账号、无后端。管理员本机持有 `.env` 跑 CLI。
- 访客只看见 `status === "published"`（或缺省）；`unlisted` 不下架删对象，只不进列表。

## Aaron 上线步骤

### 1. Cloudflare R2

1. 建 bucket（如 `foldable-wallpapers`）。
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

部署后把 `public/robots.txt` / `sitemap.xml` 里的 `example.com` 换成真实域名。

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
cd public && python3 -m http.server 8765
```

## 数据形状（wallpapers.json item）

`id, title, cdn_url, status (published|unlisted), w, h, ratio, style, device_tags[], tags[], created_at, batch_id, object_key`

`cdn_url` 为完整公开读 URL 时，壳 `wallpapers.js` 的 `src()` **不再**拼 picsum 风格 `/w/h`。旧 picsum 前缀仍兼容。

## PR / 分支说明

空仓首次可直接推 `main`（本 V1 即如此）。若走 PR：分支 `feat/v1-publish`，**draft** PR，描述写清「独立仓、Aaron 自管 CF，勿碰 website」。

## 运维

见 [OPS.md](./OPS.md)。访客冒烟见 [SMOKE.md](./SMOKE.md)。
