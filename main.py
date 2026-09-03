import feedparser
import json

from datetime import datetime, timedelta, timezone

from config import RSS_FEEDS, KEYWORDS, EXCLUDE_KEYWORDS

from database import (
    initialize_database,
    news_exists,
    save_news,
    save_ai_result,
    get_unprocessed_news
)

from ai import analyze_news


# ============================================================
# 配置
# ============================================================

# 第一次测试只处理 5 条 AI 新闻
# 跑通以后可以改成 None，处理所有未分析新闻
AI_LIMIT = 5


# ============================================================
# 工具函数
# ============================================================

def parse_time(entry):

    """
    将 RSS 发布时间转换成 datetime。
    """

    if hasattr(entry, "published_parsed") and entry.published_parsed:

        dt = datetime(
            *entry.published_parsed[:6],
            tzinfo=timezone.utc
        )

        return dt

    return None


def article_matches_keywords(article):

    """
    根据标题、摘要、RSS标签进行关键词筛选。
    """

    text = " ".join([
        article.get("title", ""),
        article.get("summary", ""),
        " ".join(article.get("tags", []))
    ]).lower()

    # 排除关键词
    for keyword in EXCLUDE_KEYWORDS:

        if keyword.lower() in text:

            return False

    # 包含关键词
    for keyword in KEYWORDS:

        if keyword.lower() in text:

            return True

    return False


# ============================================================
# RSS 抓取
# ============================================================

def fetch_rss():

    all_articles = []

    print("=" * 60)
    print("SMM 新闻 Agent 启动")
    print("=" * 60)

    for rss_url in RSS_FEEDS:

        print()
        print("正在读取：")
        print(rss_url)

        try:

            feed = feedparser.parse(rss_url)

            for entry in feed.entries:

                published = parse_time(entry)

                if not published:

                    continue

                article = {

                    "title": entry.get("title", "").strip(),

                    "link": entry.get("link", "").strip(),

                    "summary": entry.get("summary", "").strip(),

                    "published": published.isoformat(),

                    "tags": [
                        tag.get("term", "").strip()
                        for tag in entry.get("tags", [])
                        if tag.get("term")
                    ]

                }

                all_articles.append(article)

        except Exception as e:

            print("RSS读取失败：")
            print(repr(e))

    return all_articles


# ============================================================
# 过滤最近 24 小时
# ============================================================

def filter_last_24_hours(articles):

    now = datetime.now(timezone.utc)

    cutoff = now - timedelta(hours=24)

    result = []

    for article in articles:

        try:

            published = datetime.fromisoformat(
                article["published"]
            )

            if published >= cutoff:

                result.append(article)

        except Exception:

            continue

    return result


# ============================================================
# 新闻去重
# ============================================================

def deduplicate_articles(articles):

    seen = set()

    result = []

    for article in articles:

        link = article["link"]

        if not link:

            continue

        if link in seen:

            continue

        seen.add(link)

        result.append(article)

    return result


# ============================================================
# 主程序
# ============================================================

def main():

    # --------------------------------------------------------
    # 初始化数据库
    # --------------------------------------------------------

    initialize_database()

    # --------------------------------------------------------
    # 读取 RSS
    # --------------------------------------------------------

    articles = fetch_rss()

    print()
    print("原始新闻数量：", len(articles))

    # --------------------------------------------------------
    # 最近24小时
    # --------------------------------------------------------

    articles = filter_last_24_hours(articles)

    print("过去24小时：", len(articles))

    # --------------------------------------------------------
    # 去重
    # --------------------------------------------------------

    articles = deduplicate_articles(articles)

    print("去重后：", len(articles))

    # --------------------------------------------------------
    # 关键词筛选
    # --------------------------------------------------------

    filtered_news = [

        article

        for article in articles

        if article_matches_keywords(article)

    ]

    print("关键词筛选后：", len(filtered_news))

    # ========================================================
    # 保存新新闻
    # ========================================================

    new_count = 0

    old_count = 0

    for article in filtered_news:

        if news_exists(article["link"]):

            old_count += 1

        else:

            saved = save_news(article)

            if saved:

                new_count += 1

    print()
    print("=" * 60)
    print("数据库")
    print("=" * 60)

    print()
    print("新新闻：", new_count)

    print("数据库中已有：", old_count)

    # ========================================================
    # 查询尚未进行 AI 分析的新闻
    # ========================================================

    unprocessed_news = get_unprocessed_news(
        limit=AI_LIMIT
    )

    print()
    print("=" * 60)
    print("AI 新闻分析")
    print("=" * 60)

    print()
    print("待 AI 分析：", len(unprocessed_news))

    # ========================================================
    # 如果没有需要分析的新闻
    # ========================================================

    if not unprocessed_news:

        print()
        print("没有需要进行 AI 分析的新闻。")

        return

    # ========================================================
    # 逐条调用 DeepSeek
    # ========================================================

    success_count = 0

    failed_count = 0

    for index, article in enumerate(
        unprocessed_news,
        start=1
    ):

        print()
        print("-" * 60)

        print(
            f"正在分析第 {index}/{len(unprocessed_news)} 条"
        )

        print()
        print(article["title"])

        try:

            result = analyze_news(article)

            print()
            print("AI 返回结果：")

            print(
                json.dumps(
                    result,
                    ensure_ascii=False,
                    indent=2
                )
            )

            # ------------------------------------------------
            # 保存 AI 结果
            # ------------------------------------------------

            save_ai_result(
                article["link"],
                result
            )

            print()
            print("✓ AI 分析结果已保存")

            success_count += 1

        except Exception as e:

            print()
            print("✗ AI 分析失败：")

            print(repr(e))

            failed_count += 1

    # ========================================================
    # 最终统计
    # ========================================================

    print()
    print("=" * 60)
    print("AI 分析完成")
    print("=" * 60)

    print()
    print("成功：", success_count)

    print("失败：", failed_count)

    print()
    print("=" * 60)
    print("任务完成")
    print("=" * 60)


# ============================================================
# 程序入口
# ============================================================

if __name__ == "__main__":

    main()
