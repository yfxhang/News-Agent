import feedparser

from datetime import datetime, timedelta, timezone

from config import KEYWORDS, EXCLUDE_KEYWORDS


RSS_URLS = [
    "https://news.smm.cn/rss/original",
    "https://news.smm.cn/rss/industry",
    "https://news.smm.cn/rss/spot",
    "https://news.smm.cn/rss/macro",
]


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

            news.append({
                "title": title,
                "summary": summary,
                "link": link,
                "published": published,
            })

    return news


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


def filter_news(news):

    results = []

    for article in news:

        # 排除不需要的内容
        if should_exclude(article):

            continue

        # 匹配关键词
        tags = match_keywords(article)

        # 没有任何关键词就跳过
        if not tags:

            continue

        article["tags"] = tags

        results.append(article)

    return results


if __name__ == "__main__":

    print("开始获取 SMM 新闻...")

    news = fetch_news()

    print(f"原始新闻数量：{len(news)}")

    filtered_news = filter_news(news)

    print(f"筛选后新闻数量：{len(filtered_news)}")

    print()
    print("=" * 60)
    print("筛选结果")
    print("=" * 60)

    for article in filtered_news[:30]:

        print()
        print("标题：", article["title"])
        print("标签：", ", ".join(article["tags"]))
        print("时间：", article["published"])
        print("链接：", article["link"])
