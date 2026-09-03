import feedparser
import json
from database import (
    initialize_database,
    news_exists,
    save_news
)
from datetime import datetime, timedelta, timezone

from config import KEYWORDS, EXCLUDE_KEYWORDS
from ai import analyze_news

# =========================
# SMM RSS
# =========================

RSS_URLS = [
    "https://news.smm.cn/rss/original",
    "https://news.smm.cn/rss/industry",
    "https://news.smm.cn/rss/spot",
    "https://news.smm.cn/rss/macro",
]


# =========================
# 获取新闻
# =========================

def fetch_news():

    news = []

    for rss_url in RSS_URLS:

        print(f"正在读取：{rss_url}")

        feed = feedparser.parse(rss_url)

        for entry in feed.entries:

            title = entry.get("title", "")
            summary = entry.get("summary", "")
            link = entry.get("link", "")

            published = entry.get("published", "")

            # RSS通常还会提供结构化时间
            published_time = entry.get("published_parsed")

            news.append({
                "title": title,
                "summary": summary,
                "link": link,
                "published": published,
                "published_time": published_time,
            })

    return news


# =========================
# 时间过滤
# =========================

def is_recent(article, hours=24):

    published_time = article.get("published_time")

    if not published_time:
        return True

    article_time = datetime(
        published_time.tm_year,
        published_time.tm_mon,
        published_time.tm_mday,
        published_time.tm_hour,
        published_time.tm_min,
        published_time.tm_sec,
        tzinfo=timezone.utc
    )

    now = datetime.now(timezone.utc)

    cutoff = now - timedelta(hours=hours)

    return article_time >= cutoff


def filter_by_time(news):

    results = []

    for article in news:

        if is_recent(article):

            results.append(article)

    return results


# =========================
# 关键词匹配
# =========================

def match_keywords(article):

    text = (
        article["title"]
        + " "
        + article["summary"]
    )

    matched_tags = []

    for tag, keywords in KEYWORDS.items():

        for keyword in keywords:

            if keyword in text:

                matched_tags.append(tag)

                break

    return matched_tags


# =========================
# 排除关键词
# =========================

def should_exclude(article):

    text = (
        article["title"]
        + " "
        + article["summary"]
    )

    for keyword in EXCLUDE_KEYWORDS:

        if keyword in text:

            return True

    return False


# =========================
# 新闻筛选
# =========================

def filter_news(news):

    results = []

    for article in news:

        # 排除不需要的新闻
        if should_exclude(article):

            continue

        # 时间过滤
        if not is_recent(article):

            continue

        # 关键词
        tags = match_keywords(article)

        # 没有匹配关键词
        if not tags:

            continue

        article["tags"] = tags

        results.append(article)

    return results


# =========================
# 去重
# =========================

def remove_duplicates(news):

    unique_news = []

    seen_links = set()

    for article in news:

        link = article["link"]

        if link in seen_links:

            continue

        seen_links.add(link)

        unique_news.append(article)

    return unique_news


# =========================
# 主程序
# =========================

if __name__ == "__main__":

    print("=" * 60)

    print("SMM 新闻 Agent 启动")

    print("=" * 60)

    # 初始化数据库
    initialize_database()

    # 获取新闻
    news = fetch_news()

    print()
    print(f"原始新闻数量：{len(news)}")

    # 时间过滤
    recent_news = filter_by_time(news)

    print(f"过去24小时：{len(recent_news)}")

    # 去重
    unique_news = remove_duplicates(recent_news)

    print(f"去重后：{len(unique_news)}")

    # 关键词筛选
    filtered_news = filter_news(unique_news)

    print(f"关键词筛选后：{len(filtered_news)}")

    # 保存新新闻
    new_count = 0
    old_count = 0

    for article in filtered_news:

        if news_exists(article["link"]):

            old_count += 1

            continue

        if save_news(article):

            new_count += 1

    print()
    print("=" * 60)

    print(f"新新闻：{new_count}")

    print(f"数据库中已有：{old_count}")

    print("=" * 60)

    for article in filtered_news:

        print()

        print("标题：")
        print(article["title"])

        print()

        print("标签：")
        print(", ".join(article["tags"]))

        print()

        print("时间：")
        print(article["published"])

        print()

        print("链接：")
        print(article["link"])

        print("-" * 60)
    # =========================
    # AI 测试
    # =========================

    if filtered_news:

        print()
        print("=" * 60)
        print("AI 测试")
        print("=" * 60)

        test_article = filtered_news[0]

        print()
        print("正在分析：")
        print(test_article["title"])

        try:

            result = analyze_news(test_article)

            print()
            print("AI 返回结果：")
            print(json.dumps(
                result,
                ensure_ascii=False,
                indent=2
            ))

        except Exception as e:

            print()
            print("AI 调用失败：")
            print(repr(e))
