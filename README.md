# arxiv-digest

**arXiv 论文日报管道**：定时抓取指定类目的新论文 → 本地状态去重 → LLM 中文总结 + 1–5 相关度评级 → 生成 Markdown 日报。**没有 API key 也能跑**（`--no-llm` 模式只列论文不做总结）。


## 用法

```bash
# 安装（Python 3.11+）
uv venv && uv pip install -e ".[llm,dev]"

# 无 key 快速体验：抓最近 3 天 cs.AI/cs.CL/cs.LG 新论文，只列条目
arxiv-digest run --no-llm

# 完整模式：设置任一 OpenAI 兼容服务的 key（默认 DeepSeek）
set AD_LLM_API_KEY=sk-xxx          # Windows
set AD_LLM_BASE_URL=https://api.deepseek.com   # 可选，默认即此
set AD_LLM_MODEL=deepseek-chat                  # 可选
arxiv-digest run                    # 产出 digests/2026-XX-XX.md

# 常用参数
arxiv-digest run --days 3 --categories cs.AI,cs.CL,cs.LG --max 40
arxiv-digest run --include-seen     # 包含已见过的论文
```

想每天自动跑：把命令挂进任务计划（Windows Task Scheduler）或 cron 即可——本工具本身是单次执行的 CLI，不常驻。

## 管道五步（也是面试讲法）

1. **抓取**：arXiv API 按类目 + 提交日期窗口查询（只敢用 `cat:` 查询——自由文本搜索接口限流狠得多）；每类目一请求、间隔 3 秒、尊重 `Retry-After`
2. **去重**：`digests/state.json` 记录见过的论文 ID，跨运行只报新论文（版本号 `v1/v2` 归一化后再比对）
3. **总结**：每篇论文一次 LLM 调用，Prompt 要求稳定输出 JSON（一句话概括 + 为什么关注 + 1–5 相关度，相关性锚定在「LLM 应用 / Agent 开发」）
4. **容错**：JSON 解析失败自动重试一次（更严格的提示），再失败就降级为只列条目——单篇坏响应不会杀掉整次运行；`--max` 限制单次调用量控成本
5. **成报**：≥4 分的进「今日值得关注」，全部按分数排序，文件名按日期自动避让重名

## 成本

默认 **GLM-4-Flash 为免费模型**（智谱开放平台），本项目量级下零成本。
换 DeepSeek 参考价：40 篇 × 约 1.2k token 输入 ≈ 每次运行不到 ¥0.05。

## 测试与 CI

- 15 个离线单元测试：Atom 解析（乱空白）、状态去重往返、JSON 提取（含 ```json 围栏、夹带前后文）、重试与降级、日报排序与文件名避让、CLI 端到端（monkeypatch 抓取，不起网络）
- `ruff check` 干净；GitHub Actions：Python 3.11–3.13，pytest + ruff

## 工程上踩过/规避的坑

- arXiv API 必须用 `https://`（`http://` 301 重定向叠加重试会让请求翻倍——同 arxiv-mcp 项目）
- `cat:` + `submittedDate` 组合查询稳定；`all:关键词` 自由文本查询在共享出口 IP 下常被 429
- LLM 输出 JSON 不能裸信：围栏、前后闲话、字段越界都要处理，且失败要局部降级而不是全盘报错
- 论文 ID 带版本号（`2410.12345v2`），去重键必须先归一化，否则同一篇论文改版后会重复上报

## 贡献边界（如实声明）

- 「抓取 → 处理 → LLM 总结 → 生成报告」的管道模式是业界通用做法，无原创性主张；本仓库的实现（Atom 解析、状态去重、JSON 容错、日报渲染、测试）为本人从零编写
- arXiv 数据来自其公开 API，遵循其使用条款；总结由 LLM 生成，仅供个人筛选参考
- 依赖仅 `httpx`（LLM 调用用 `openai` SDK，作为可选依赖）
