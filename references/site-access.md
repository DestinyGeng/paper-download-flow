# 图书馆资源可达性实测（2026-11-18，经 WebVPN）

入口：`https://libvpn2.zuel.edu.cn/?id=1`（中文）/ `?id=2`（外文）。
**页面上的"进入"按钮会带校验参数开新窗口，直接拼 URL 会白屏**——这是本次最大的坑。

## 中文资源

| 资源 | 结果 | 证据 |
|---|---|---|
| CNKI 中国知网 | ✅ 可用 | 右上角显示"中南财经政法大学"；检索"配对交易"455 条 |
| 北大法宝 | ✅ 打开 | 法律法规数据库页正常 |
| 万方 | ✅ 可用 | "绑定机构 中南财经政法大学" |
| 威科先行 | ✅ 可用 | "您好，zuel_ip"（IP 认证） |
| 超星发现 | ✅ 可用 | "欢迎来自中南财经政法大学的朋友" |
| EPS 数据平台 | ✅ 打开 | 首页正常 |
| CSMAR | ⚠️ 页面开 | 代理域名已加载，正文空，需登录 |
| 读秀 | ⚠️ 部分 | 落到 duxiu.com 帮助页 |
| 维普 | ⚠️ 白屏 | 代理域名已加载，正文空 |
| RESSET | ⏳ 未测 | 入口需 signin |

## 外文资源

| 资源 | 结果 | 证据 |
|---|---|---|
| Web of Science | ✅ 打开 | 跳转 webofscience.clarivate.cn/wos |
| ScienceDirect | ✅ 打开 | 首页正常 |
| Wiley Online Library | ✅ 打开 | 首页正常 |
| HeinOnline | ❌ 400 | HTTP 400 |
| JSTOR | ❌ 挑战页 | Client Challenge |
| Westlaw | 🔑 需 CARSI | 跳 signon.thomsonreuters.com 联邦登录 |
| EBSCO | 🔑 验证页 | browserVerification |
| JCR | 🔑 验证页 | 点击可打开 |

## 操作要点

1. **必须走点击**：`POST /click?target=ID`，body 为 CSS 选择器；选择器必须**唯一匹配**，否则 400。同一资源在列表里常出现两次，要用更精确的选择器。
2. 点击后资源在**新标签页**打开，要用 `/targets` 重新枚举，不要在原 tab 上读。
3. 判断"是否认证"，看页面文本里的机构标识：CNKI/万方/超星显示学校名，威科显示 `zuel_ip`。
4. SPA 页面正文要用 `/eval` + `document.body.innerText`，`/readPage` 常只返回页脚。
