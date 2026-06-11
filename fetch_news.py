#!/usr/bin/env python3
"""每日 AI 新闻聚合:RSS + Hacker News,去重后输出 Markdown。

无 LLM、无数据库。状态只有一个 seen.json(已见 URL 的 hash)。
"""
import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import requests

ROOT = Path(__file__).parent
SEEN_FILE = ROOT / "seen.json"
OUT_DIR = ROOT / "news"
SEEN_TTL_DAYS = 30          # seen 记录保留天数,防止文件无限膨胀
HN_MIN_POINTS = 150          # HN 热度门槛
HN_HOURS = 24               # HN 只看最近 24 小时

# ---------------- 信息源 ----------------
RSS_SOURCES = {
    "Anthropic": "https://www.anthropic.com/rss.xml",
    "OpenAI": "https://openai.com/news/rss.xml",
    "Google DeepMind": "https://deepmind.google/blog/rss.xml",
    "HuggingFace": "https://huggingface.co/blog/feed.xml",
    "Simon Willison": "https://simonwillison.net/atom/everything/"
}

# HN 标题关键词过滤(小写匹配)
AI_KEYWORDS = [
    "ai", "llm", "gpt", "claude", "gemini", "openai", "anthropic",
    "deepmind", "machine learning", "neural", "transformer", "agent",
    "rag", "fine-tun", "diffusion", "mistral", "llama", "qwen", "deepseek",
]

# arXiv 类源每天上百篇,只取前 N 条
ARXIV_LIMIT = 15


def url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().lower().encode()).hexdigest()[:16]


def load_seen() -> dict:
    if SEEN_FILE.exists():
        return json.loads(SEEN_FILE.read_text())
    return {}


def save_seen(seen: dict) -> None:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=SEEN_TTL_DAYS)).isoformat()
    pruned = {h: ts for h, ts in seen.items() if ts >= cutoff}
    SEEN_FILE.write_text(json.dumps(pruned, indent=0, sort_keys=True))


def fetch_rss(name: str, url: str) -> list[dict]:
    items = []
    try:
        feed = feedparser.parse(url, request_headers={"User-Agent": "ai-news-digest/1.0"})
        entries = feed.entries
        if name.startswith("arXiv"):
            entries = entries[:ARXIV_LIMIT]
        for e in entries:
            link = getattr(e, "link", "")
            title = getattr(e, "title", "").strip()
            if link and title:
                items.append({"source": name, "title": title, "url": link})
    except Exception as exc:  # 单源失败不影响整体
        print(f"[warn] {name} failed: {exc}")
    return items


def fetch_hn() -> list[dict]:
    since = int(time.time()) - HN_HOURS * 3600
    api = (
        "https://hn.algolia.com/api/v1/search?tags=story"
        f"&numericFilters=points>{HN_MIN_POINTS},created_at_i>{since}"
        "&hitsPerPage=100"
    )
    items = []
    try:
        hits = requests.get(api, timeout=15).json().get("hits", [])
        for h in hits:
            title = (h.get("title") or "").strip()
            low = f" {title.lower()} "
            if not any(k in low for k in AI_KEYWORDS):
                continue
            url = h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}"
            items.append({
                "source": "Hacker News",
                "title": f"{title} ({h.get('points', 0)} pts)",
                "url": url,
            })
    except Exception as exc:
        print(f"[warn] HN failed: {exc}")
    return items


def main() -> None:
    seen = load_seen()
    now = datetime.now(timezone.utc)

    all_items = fetch_hn()
    for name, url in RSS_SOURCES.items():
        all_items.extend(fetch_rss(name, url))

    fresh = []
    for it in all_items:
        h = url_hash(it["url"])
        if h in seen:
            continue
        seen[h] = now.isoformat()
        fresh.append(it)

    if not fresh:
        print("no new items today")
        save_seen(seen)
        return

    # 按源分组输出
    by_source: dict[str, list[dict]] = {}
    for it in fresh:
        by_source.setdefault(it["source"], []).append(it)

    date_str = now.strftime("%Y-%m-%d")
    lines = [f"# AI News {date_str}", ""]
    order = ["Hacker News"] + list(RSS_SOURCES)
    for src in order:
        items = by_source.get(src)
        if not items:
            continue
        lines.append(f"## {src}")
        for it in items:
            lines.append(f"- [{it['title']}]({it['url']})")
        lines.append("")

    OUT_DIR.mkdir(exist_ok=True)
    out = OUT_DIR / f"{date_str}.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    save_seen(seen)
    print(f"wrote {out} ({len(fresh)} new items)")


if __name__ == "__main__":
    main()
