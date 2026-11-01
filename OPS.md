# 运维一页（图片站 V1）

## 下架一张图

不下删 R2（默认），只把 JSON 里 `status` 改为 `unlisted`，访客列表立即不再展示（Pages 需已包含最新 JSON）。

```bash
.venv/bin/python scripts/publish.py --unpublish <id>
# 可选：连 R2 对象一起删
.venv/bin/python scripts/publish.py --unpublish <id> --delete-object
```

改完 JSON 后重新部署 Pages（或 Git push 触发）。

## 重跑失败上传

`publish.py` 按 id 幂等覆盖。网络中断或半成功时，用**同一** `--dir` / `--id` 再跑一次即可。

```bash
.venv/bin/python scripts/publish.py --dir /path/to/out --id <same-id> --dry-run   # 先确认
.venv/bin/python scripts/publish.py --dir /path/to/out --id <same-id>
```

## Pages 部署

```bash
# 方式 A：Wrangler
npx wrangler pages deploy public --project-name=foldable-wallper-site

# 方式 B：Git 接入 CF Pages
# Dashboard → Pages → Connect to Git → yuanxujia8090/foldable-wallper-site
# Production branch: main；Output directory: public；Build command: （留空）
git add -A && git commit -m "…" && git push origin main
```

## 本地预览

```bash
cd public && python3 -m http.server 8765
# http://127.0.0.1:8765/
```

## 密钥

`.env` 仅本机；已在 `.gitignore`。轮换 R2 Key 后更新 `.env`，旧 Key 在 CF 作废。
