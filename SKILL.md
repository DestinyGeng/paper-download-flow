---
name: paper-download-flow
description: 待填：说明何时该用这个技能（DSH 把这段放进技能目录，决定模型会不会自动加载）。例如：当用户要求按主题批量检索、筛选、下载可核验的学术论文 PDF 时使用。
---

# 论文下载流

> 这是自建技能，下面是待填骨架。每节先写结论，再写理由。

## 0. 目标与完成标准

把「下载 X 主题的论文」变成三件可追溯的东西：

1. **候选清单**（检索式、来源、时间、命中数）
2. **可复现的下载**（manifest：每篇的 URL、状态、字节数、sha256）
3. **可核验的产物**（PDF + 身份核对 + 失败原因）

完成标准：`manifest.json` 里每一项都有明确状态；未完成项有证据与原因。

## 1. 何时使用 / 何时不用

- 用：
- 不用：

## 2. 输入

| 项 | 缺省策略 |
|---|---|
| 主题 / 关键词 | |
| 数量上限 | |
| 年份范围 | |
| 语言 | |
| 来源偏好 | |
| 是否需要全文 / 只要题录 | |

## 3. 流程

### 3.1 检索：来源分层（学校订阅 + 开放源）

学校已购资源分四层，**按 L0 → L3 顺序使用**，能不开登录就不开。

| 层 | 来源 | 访问方式 | 用途 | 预算 |
|---|---|---|---|---|
| **L0 开放源**（无需登录，先扫） | arXiv、OpenAlex、Crossref、Unpaywall、RePEc/IDEAS、NBER、SSRN、机构库 | API / 直链 | 拿题录 + OA PDF | 每查询 1 次 |
| **L1 元数据源**（登录，只查不批量导） | Web of Science 核心合集、JCR | 校园网 IP / CARSI | 引文、被引、期刊分区 → 只用于排序筛选 | 每篇 ≤ 1 次 |
| **L2 全文源**（登录，**按篇**下载） | ScienceDirect、Wiley、EBSCO、JSTOR、CNKI、万方、维普、读秀 | 校园网 IP / CARSI | 取订阅 PDF | 每篇 ≤ 1 次，不翻页抓取 |
| **L3 数据源**（非论文） | CSMAR、RESSET、EPS | 校园网 IP / 专用客户端 | 实证数据，**不产出 PDF** | 另立任务 |

中文库补充：北大法宝、威科先行、Lexis、Westlaw、HeinOnline 属法律/案例库，只在涉及法条、案例、监管文本时使用，不用于论文全文。

#### 机构访问的硬边界

- **登录由本人在浏览器里完成**，技能不保存、不代填账号密码；专用 profile：`~/.local/share/academic-search/chrome-profile`
- **不做批量自动下载**。出版社许可普遍禁止 systematic downloading（连续抓取），触发后按 IP 段封禁，代价是整个学校访问中断；
- 单篇获取视为"代替用户点击一次"：一次请求、一个文件、有记录；
- 遇到 402/403/验证码/挑战页，**立即停止该来源并记录**（见 3.5），不换工具重试。

#### 检索记录（每次必留）

- 平台、检索式原文、时间、命中数、翻到的页数
- 筛选理由（为什么排除）
- 若走浏览器：目标 URL、动作、结果证据（截图或页面标题）

#### 站点经验

按域名记在 `bench/site-notes.md`：URL 模式、选择器、登录方式、已知坑（如 CNKI 的详情页必须走 kcms2、ScienceDirect 的 PDF 在 `/pdfft` 路径）。

### 3.2 筛选：三道闸（相关性 → 来源质量 → 时间/引用）

每篇论文必须**依次**过三道闸，任一道不过即拒，并记录 `decision_reason`。

#### 闸 A：相关性（必要）

主题命中任一即可：`pairs trading` / `pair trading` / `statistical arbitrage` /（`copula` 且 `cointegration|trading|arbitrage`）。
排除：水文、气象、合成数据、纯 copula 理论（无金融应用）、勘误/社论/书评。

#### 闸 B：来源质量（基准 = 中南财经政法大学《学术期刊指引（2025 版）》）

校定口径：**A+ / A / A- / B / C** 五级；其中 **B = JCR Q1 或 ABS ≥ 2 星**，**A = CCF A**，**C = CSSCI / CSCD 核心 / SSCI / SCI / A&HCI / EI 核心收录**，**预警期刊剔除**。

阅读范围取并集（命中任一即通过）：

| 路径 | 条件 | 对应校定 |
|---|---|---|
| B1 | **JCR Q1** | B |
| B2 | **ABS/AJG ≥ 2 星** | B |
| B3 | **中科院 1 区或 2 区**（升级版优先，基础版对照） | 校定不直接认，但你要读 |
| B4 | CCF A 期刊/会议，或有已发表版本的顶刊工作论文 | A |
| ✗ | 预警名单（中科院 / 新锐） | 一票否决，不看分区与引用 |
| ✗ | Q3/Q4 且非中科院 1–2 区、且无 ABS | 拒：`venue_below_threshold` |

> 注意口径差异：JCR Q1 = 学科前 25%，中科院 1 区 ≈ 前 5%。两者不可互替，必须分别判定后取并集。

> 分区数据：SJR 开放（scimagojr 年度 CSV，可自动）；JCR 需登录（你有订阅）；中科院分区只有 Excel 表。
> 自动化用 SJR，**决赛名单再用 JCR / 中科院表复核**——这是唯一需要人工的一步。

#### 闸 C：时间 / 引用（按你定的规则）

| 条件 | 处置 | 理由 |
|---|---|---|
| 被引 **≥ 500** | **必收**，不看年份 | 领域绕不过去的经典 |
| 被引 **≥ 100** | 收，不看年份，但闸 B 必须过（Q1/Q2） | 高影响且来源可信 |
| 无上述引用，发表 ≤ 5 年（2021 起） | 收（闸 B 过 Q1/Q2） | 新文献代表当前方法 |
| 无上述引用，发表 6–10 年（2016–2020） | Q1 收；Q2 进备选 | 中段年份只留强刊 |
| 发表 > 10 年且被引 < 100 | 仅收白名单内的奠基性文献 | 老文低引基本是噪音 |

#### 跨领域校正（重要）

绝对引用数偏袒两个群体：**老论文**和**机器学习论文**。所以另存一个标准化指标：

- OpenAlex `cited_by_percentile_year.max`（同年同领域百分位）：
  - `≥ 95` → 视为"高影响"，等价于 ≥ 500 规则；
  - `≥ 85` → 视为"合格"，等价于 ≥ 100 规则；
  - 两者冲突时**取更高的判定**，并在 `decision_reason` 里写明用了哪条。

#### 中文文献的等效规则

CNKI / 万方 无期刊分区，用近似：`CSSCI` 或 `北大核心` 视作 Q1/Q2；被引 ≥ 30 视作"合格"，≥ 100 视作"高影响"。

#### 去重

1. DOI 相同 → 合并，保留信息更全的一条；
2. 无 DOI → 标题规范化后**完全相同**才算重复（保守），预印本与正式版保留对应关系、标注 `preprint_of`；
3. 标题相似但不完全相同 → 只标 `possible_duplicate`，交人工。

#### 输出

`refs/selected.json`（通过）+ `refs/rejected.json`（拒绝，带理由），每条含：
`title / year / venue / quartile / cited_by_count / cited_percentile / gate_b / gate_c / decision_reason`。
阈值集中放在 `config.yaml`，改数字不用改代码。

### 3.3 下载

- 工具：
- 命名规则：
- 幂等策略：

### 3.4 核验：成功判据 C（字节 → 结构 → 身份）

三级判定，逐级严格，任一级失败即停并记录原因。**只有三级全过才叫「下载成功」。**

| 级 | 检查 | 通过条件 | 失败码 |
|---|---|---|---|
| L1 字节 | HTTP 200、Content-Type 含 pdf、前 5 字节为 `%PDF-`、字节数 ≥ 20 KB | 全部满足 | `fetch_failed` / `http_4xx` / `http_5xx` / `timeout` / `not_pdf` |
| L2 结构 | `pdfinfo` 能解析出 `Pages: N` 且 N ≥ 1 | 解析成功 | `corrupt_pdf` |
| L3 身份 | `pdftotext -f 1 -l 1` 取首页文本，与目标记录比对 | 见下方规则 | `identity_mismatch` / `identity_unverifiable` |

#### L3 身份比对规则

**标题召回率**：把目标标题与首页文本都规范化（小写、去标点、压缩空白、去停用词），取目标标题的词元集合 T 与首页文本词元集合 P：

```
title_recall = |T ∩ P| / |T|
```

**作者命中**：目标第一作者的姓氏（姓名最后一个词，ASCII 化）是否出现在首页文本中。

| 判定 | 条件 | `paper_identity_status` |
|---|---|---|
| 通过 | `title_recall ≥ 0.95`，**或** `0.80 ≤ title_recall < 0.95` 且任一作者姓氏命中 | `verified` |
| 待人工 | `0.50 ≤ title_recall < 0.80` | `mismatch` |
| 可疑 | 标题够（≥ 0.80）但作者没命中 | `unverifiable_author`（保留文件，人工扫一眼） |
| 无法判定 | 首页文本 < 200 字符（扫描版/无文本层） | `unverifiable` |

**为什么不用"标题 0.80 且作者必中"**：2026-11-18 在 15 篇真实 PDF 上实测，标题召回 **全部为 1.00**，
但首作者姓氏有 1 篇没命中（PDF 首页只印了缩写/通讯作者顺序不同）。作者命中作为**辅助降级**，不作硬门槛。

阈值 0.80 / 0.50 是**初始值**，跑满 20 篇后按实测误判率调整，调整记录写进 `bench/runs.md`。
比对证据要留：`title_recall`、`author_hit`、首页前 300 字符（截断），写进 manifest，便于事后复查。

### 3.5 失败标注：打不开 vs 付费

三类信息**分开存**，不要挤进一个字段：

- `download_status`：`not_requested` / `eligible` / `downloaded` / `skipped` / `failed`
- `failure_reason`：具体原因码（下表）
- `access_status`：`open` / `paywalled` / `restricted` / `unknown`

| 现象 | failure_reason | access_status | 处理 |
|---|---|---|---|
| 来源已声明非开放（OpenAlex `oa_status=closed` 且无 OA 地址） | `declared_closed` | `paywalled` | 不请求，直接标注，记入「需机构权限」清单 |
| HTTP 402 | `paywall_402` | `paywalled` | 停止，换合法来源 |
| HTTP 403 且落地页含 subscribe / purchase / access denied | `paywall_403` | `paywalled` | 停止，**不换工具硬闯** |
| HTTP 401 或 302 跳登录页 | `login_required` | `restricted` | 记录，提示需账号 |
| DNS / TLS / 连接被拒 | `fetch_failed` | `unknown` | **这是「打不开」**，可重试 + 换备用 OA 地址 |
| HTTP 4xx（非 401/402/403） | `http_4xx` | `unknown` | 换备用地址 |
| HTTP 5xx | `http_5xx` | `unknown` | 重试 1 次（退避 2s），仍失败则标 502/503 |
| HTML、挑战页（Just a moment / captcha） | `blocked_challenge` | `restricted` | 停止，不绕验证码 |
| 有字节但 pdfinfo 失败 | `corrupt_pdf` | `open` | 重下 1 次，仍坏则标损坏 |
| 首页是另一篇论文 | `identity_mismatch` | `open` | 保留文件但标 mismatch，人工确认 |

**判定顺序**：先看来源声明（不花请求），再看 HTTP 响应，最后才看文件内容。声明为 closed 的记录不要浪费请求。

### 3.6 交付物

- `refs/papers.json` / `refs/manifest.json` / `refs/ref.bib`
- `pdfs/`
- `logs/`（检索日志 + 每次运行的耗时与 token）

## 4. 失败与边界

- 403 / 429 / 超时：
- 付费墙：
- 中文库（知网）：

## 5. 评测口径

见 `bench/runs.md`：每次改动后记录「token 用量 / 墙钟时间 / 产物完整度」，并与对照实现（academic-search v1.4.0）比。

## 6. 文件索引

| 文件 | 用途 |
|---|---|
| `references/runbook.md` | **操作手册**：环境、进资源、检索、下载、核验 |
| `references/levels-rules.md` | 级别判定规则 A+/A/A-/B+/B/C |
| `references/easyscholar.md` | easyScholar 插件与数据集分析 |
| `references/site-cnki.md` | CNKI 实测经验 |
| `references/site-access.md` | 图书馆资源可达性实测 |
| `data/zuel-guide.json` | 校定指南 1605 条 |
| `scripts/classify.py` | 定级引擎（含自测） |
| `scripts/jcr_import.py` | JCR 导出 CSV → 结构化 |
| `bench/runs.md` | 评测台账 |
