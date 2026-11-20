# CNKI 站点经验（经中南财大 WebVPN）

## 入口链路

1. WebVPN 首页：`https://libvpn2.zuel.edu.cn/?id=1`（中文资源导航），**打开即用，未要求单独登录**；
2. 列表里"CNKI中国知网"指向 `https://www.cnki.net/`；
3. CNKI 首页右上角显示 **中南财经政法大学**，即已带机构权限（不是个人账号）。

## 已验证的检索入口

```
https://kns.cnki.net/kns8s/defaultresult/index?kw=<关键词>&korder=SU
```

`korder=SU` 表示按"主题"检索；返回页标题为"检索-中国知网"。

## 实测（2026-11-18，主题=配对交易）

| 维度 | 数值 |
|---|---|
| 总库 | 455 |
| 学术期刊 | 118 |
| 学位论文 | 318 |
| 图书 | 4 |
| 会议 | 1 |
| 报纸 | 12 |
| 北大核心 | 41 |
| CSSCI | 26 |
| CSCD | 14 |
| AMI | 10 |
| WJCI | 7 |
| EI | 2 |

右侧筛选栏可直接用来源类别（北大核心 / CSSCI / CSCD）把结果压到"指南 C 级以上"的范围。

## 操作要点

- 页面是 SPA，`/readPage` 常只拿到页脚；**要取正文用 `/eval` + `document.body.innerText`**（POST body 为裸 JS 代码，不是 JSON）；
- 控制台弹窗（"个人登录"）会遮住首页检索框，直接走上面的检索 URL 更快；
- 下载按篇进行，不做批量翻页抓取（见 SKILL.md 3.1 的机构访问硬边界）。
