# AI News Digest

每日聚合 AI 新闻到 Markdown,GitHub Actions 定时跑,无服务器无 LLM。

## 部署

1. 建一个 GitHub repo,把这三个文件推上去(保持目录结构)
2. repo Settings → Actions → General → Workflow permissions 选 **Read and write**
3. Actions 页面手动跑一次 `daily-ai-news` 验证,之后每天北京时间 07:00 自动执行
4. Obsidian 侧:把这个 repo clone 进 vault(或整个 vault 就是这个 repo),装 **obsidian-git** 插件,设置自动 pull 间隔(如 60 分钟)

## 调整

- 加减信息源:改 `fetch_news.py` 里的 `RSS_SOURCES`
- HN 热度门槛 / 关键词:`HN_MIN_POINTS` / `AI_KEYWORDS`
- 执行时间:`daily.yml` 里的 cron(注意是 UTC)

## 文件

- `fetch_news.py` — 抓取 + 去重 + 输出 `news/YYYY-MM-DD.md`
- `seen.json` — 已见 URL 记录(自动生成,30 天自动清理)
- `.github/workflows/daily.yml` — 定时任务
