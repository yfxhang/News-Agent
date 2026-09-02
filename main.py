import feedparser
from datetime import datetime


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
            news.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "summary": entry.get("summary", ""),
                "published": entry.get("published", ""),
            })

    return news


if __name__ == "__main__":

    news = fetch_news()

    print()
    print("=" * 60)
    print(f"获取到 {len(news)} 条新闻")
    print("=" * 60)

    for item in news[:10]:

        print()
        print("标题：", item["title"])
        print("时间：", item["published"])
        print("链接：", item["link"])
