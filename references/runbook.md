# 操作手册（Runbook）— 一条任务从头到尾怎么跑

> 本文件是"手怎么动"的部分；判据与规则见 `levels-rules.md`，站点细节见 `site-cnki.md` / `site-access.md`。

## 0. 环境（一次性）

| 项 | 值 |
|---|---|
| 专用 Chrome profile | `~/.local/share/academic-search/chrome-profile` |
| CDP 代理 | `http://127.0.0.1:3457`（`check-deps.sh` 启动） |
| 取正文 | SPA 页面用 `POST /eval` + `document.body.innerText`；`/readPage` 常只返回页脚 |
| 取链接/控件 | `/eval` 返回数组；操作前先用 `data-pick` 打标记再用 `/clickAt` |

## 1. 进资源（WebVPN）

1. 中文资源：`https://libvpn2.zuel.edu.cn/?id=1`；外文：`?id=2`
2. **必须点"进入"**：给 `a[href*="browserVerification"]` 打标记 → `/clickAt`；直接导航会白屏。
3. 点击后资源在**新标签页**打开，用 `/targets` 重新枚举。
4. 判断认证：页面文字里有学校名或 `zuel_ip` 即通。

## 2. 检索

### CNKI（中文）
- 直接构造：`https://kns.cnki.net/kns8s/defaultresult/index?kw=<关键词>&korder=SU`
- 右侧筛选"北大核心 / CSSCI"把范围压到指南 C 级及以上；
- 记录关键词、命中数、筛选条件。

### JCR（分区）
- 打开 JCR → `#search-bar` 填刊名 → `/press {"key":"Enter"}`
- 结果页用 `/clickAt` 进列表；
- **未登录只有基本信息，JIF Quartile 需登录**；拿不到就标 `待核`，不猜。

### WoS
- `https://webofscience.clarivate.cn/`，机构认证后可检索。

## 3. 定级

```bash
python3 scripts/classify.py --venue "Automatica" --cas 2 --jcr Q1 --indexed
```

优先级：预警剔除 > 指南列出 > 中科院1区=A > JCR Q1=B+ > 中科院2区=B > 索引=C > 不认定。

## 4. 下载

1. **先 L0 开放源**（arXiv/OpenAlex/Unpaywall），能拿到就不碰订阅库；
2. 订阅库按篇取，一次一篇，不翻页批量；
3. 命名 `年份_一作姓氏_短标题.pdf`（ASCII）；
4. 每篇记 manifest：URL、HTTP 状态、字节数、sha256、核验状态。

## 5. 核验（成功判据 C）

L1 字节（`%PDF-` + ≥20KB）→ L2 `pdfinfo` 可解析 → L3 首页标题/作者比对。

## 6. 交付

`refs/papers.json`、`refs/manifest.json`、`refs/ref.bib`、`pdfs/`、`logs/`。
