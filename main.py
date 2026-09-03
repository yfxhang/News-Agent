import feedparser
import json
import requests

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from config import (
    RSS_FEEDS,
    KEYWORDS,
    EXCLUDE_KEYWORDS
)

from database import (
    initialize_database,
    news_exists,
    save_news,
    save_ai_result,
    get_unprocessed_news
)

from ai import analyze_news


# ============================================================
# AI 测试阶段限制
# ============================================================

# 第一次测试只处理 5 条
#
# 等整个系统确认稳定以后，
# 可以改成：
#
# AI_LIMIT = None
#
# 表示处理所有尚未分析的新闻。

AI_LIMIT = 5


# ============================================================
# 时间解析
# ============================================================

def parse_time(entry):

    """
    兼容 SMM RSS 的中文日期格式。

    例如：

    周三,02 9月 2026 11:43:37 +0800

    最终统一转换成 UTC datetime。
    """

    import re

    # ========================================================
    # 1. 优先使用 feedparser 已经解析好的时间
    # ========================================================

    if getattr(entry, "published_parsed", None):

        return datetime(
            *entry.published_parsed[:6],
            tzinfo=timezone.utc
        )

    if getattr(entry, "updated_parsed", None):

        return datetime(
            *entry.updated_parsed[:6],
            tzinfo=timezone.utc
        )

    # ========================================================
    # 2. 获取原始时间字符串
    # ========================================================

    time_strings = [

        entry.get("published"),

        entry.get("updated")

    ]

    # ========================================================
    # 3. 逐个尝试
    # ========================================================

    for time_string in time_strings:

        if not time_string:

            continue

        time_string = str(
            time_string
        ).strip()

        # ====================================================
        # 3.1 标准 RFC 日期
        # ====================================================

        try:

            dt = parsedate_to_datetime(
                time_string
            )

            if dt.tzinfo is None:

                dt = dt.replace(
                    tzinfo=timezone.utc
                )

            return dt.astimezone(
                timezone.utc
            )

        except Exception:

            pass

        # ====================================================
        # 3.2 SMM 中文日期格式
        #
        # 周三,02 9月 2026 11:43:37 +0800
        # ====================================================

        chinese_months = {

            "1月": 1,
            "2月": 2,
            "3月": 3,
            "4月": 4,
            "5月": 5,
            "6月": 6,
            "7月": 7,
            "8月": 8,
            "9月": 9,
            "10月": 10,
            "11月": 11,
            "12月": 12

        }

        # ----------------------------------------------------
        # 去掉星期
        #
        # 周三,02 9月 2026...
        #
        # ↓
        #
        # 02 9月 2026...
        # ----------------------------------------------------

        cleaned = re.sub(
            r"^周[一二三四五六日天],?",
            "",
            time_string
        ).strip()

        # ----------------------------------------------------
        # 匹配：
        #
        # 02 9月 2026 11:43:37 +0800
        # ----------------------------------------------------

        pattern = (
            r"(\d{1,2})\s+"
            r"(1月|2月|3月|4月|5月|6月|"
            r"7月|8月|9月|10月|11月|12月)\s+"
            r"(\d{4})\s+"
            r"(\d{1,2}):"
            r"(\d{2}):"
            r"(\d{2})\s+"
            r"([+-]\d{4})"
        )

        match = re.search(
            pattern,
            cleaned
        )

        if match:

            day = int(
                match.group(1)
            )

            month = chinese_months[
                match.group(2)
            ]

            year = int(
                match.group(3)
            )

            hour = int(
                match.group(4)
            )

            minute = int(
                match.group(5)
            )

            second = int(
                match.group(6)
            )

            timezone_string = (
                match.group(7)
            )

            # ------------------------------------------------
            # 解析 +0800
            # ------------------------------------------------

            sign = 1

            if timezone_string.startswith("-"):

                sign = -1

            timezone_hour = int(
                timezone_string[1:3]
            )

            timezone_minute = int(
                timezone_string[3:5]
            )

            offset_minutes = (
                sign *
                (
                    timezone_hour * 60
                    +
                    timezone_minute
                )
            )

            tz = timezone(
                timedelta(
                    minutes=offset_minutes
                )
            )

            # ------------------------------------------------
            # 创建 datetime
            # ------------------------------------------------

            dt = datetime(
                year,
                month,
                day,
                hour,
                minute,
                second,
                tzinfo=tz
            )

            # ------------------------------------------------
            # 转 UTC
            # ------------------------------------------------

            return dt.astimezone(
                timezone.utc
            )

    # ========================================================
    # 4. 全部失败
    # ========================================================

    return None

# ============================================================
# RSS 抓取
# ============================================================

def fetch_rss():

    """
    从 config.py 中配置的 RSS_FEEDS 抓取新闻。
    """

    all_articles = []

    print("=" * 60)
    print("SMM 新闻 Agent 启动")
    print("=" * 60)

    # --------------------------------------------------------
    # 请求头
    # --------------------------------------------------------

    headers = {

        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )

    }

    # --------------------------------------------------------
    # 逐个读取 RSS
    # --------------------------------------------------------

    for rss_url in RSS_FEEDS:

        print()
        print("正在读取：")
        print(rss_url)

        try:

            # ------------------------------------------------
            # HTTP 请求
            # ------------------------------------------------

            response = requests.get(
                rss_url,
                headers=headers,
                timeout=20
            )

            print(
                "HTTP状态：",
                response.status_code
            )

            print(
                "响应长度：",
                len(response.content)
            )

            # 如果 HTTP 不是 200，
            # requests 会抛出异常。

            response.raise_for_status()

            # ------------------------------------------------
            # feedparser 解析
            # ------------------------------------------------

            feed = feedparser.parse(
                response.content
            )

            print(
                "Feedparser解析状态：",
                feed.bozo
            )

            # ------------------------------------------------
            # 如果 RSS 存在解析警告
            # ------------------------------------------------

            if feed.bozo:

                print(
                    "Feedparser异常：",
                    repr(feed.bozo_exception)
                )

            print(
                "RSS新闻数量：",
                len(feed.entries)
            )

            # ------------------------------------------------
            # 读取每条新闻
            # ------------------------------------------------

            for entry in feed.entries:

                published = parse_time(
                    entry
                )

                # ------------------------------------------------
                # 无法解析时间
                # ------------------------------------------------

                if not published:

                    print()
                    print(
                        "⚠ 无法解析新闻时间："
                    )

                    print(
                        entry.get(
                            "title",
                            ""
                        )
                    )

                    print(
                        "published =",
                        repr(
                            entry.get(
                                "published"
                            )
                        )
                    )

                    print(
                        "updated =",
                        repr(
                            entry.get(
                                "updated"
                            )
                        )
                    )

                    continue

                # ------------------------------------------------
                # RSS 原始标签
                # ------------------------------------------------

                rss_tags = [

                    tag.get(
                        "term",
                        ""
                    ).strip()

                    for tag in entry.get(
                        "tags",
                        []
                    )

                    if tag.get("term")

                ]

                # ------------------------------------------------
                # 组装新闻
                # ------------------------------------------------

                article = {

                    "title": entry.get(
                        "title",
                        ""
                    ).strip(),

                    "link": entry.get(
                        "link",
                        ""
                    ).strip(),

                    "summary": entry.get(
                        "summary",
                        ""
                    ).strip(),

                    "published": published.isoformat(),

                    "tags": rss_tags

                }

                # ------------------------------------------------
                # 必须有标题和链接
                # ------------------------------------------------

                if not article["title"]:

                    continue

                if not article["link"]:

                    continue

                all_articles.append(
                    article
                )

        except Exception as e:

            print()
            print(
                "RSS读取失败："
            )

            print(
                type(e).__name__
            )

            print(
                repr(e)
            )

    return all_articles


# ============================================================
# 最近24小时筛选
# ============================================================

def filter_last_24_hours(
    articles
):

    """
    只保留最近24小时的新闻。
    """

    now = datetime.now(
        timezone.utc
    )

    cutoff = (
        now -
        timedelta(hours=24)
    )

    result = []

    for article in articles:

        try:

            published = datetime.fromisoformat(
                article["published"]
            )

            # ------------------------------------------------
            # 如果没有时区，默认 UTC
            # ------------------------------------------------

            if published.tzinfo is None:

                published = published.replace(
                    tzinfo=timezone.utc
                )

            # ------------------------------------------------
            # 最近24小时
            # ------------------------------------------------

            if published >= cutoff:

                result.append(
                    article
                )

        except Exception:

            continue

    return result


# ============================================================
# 新闻去重
# ============================================================

def deduplicate_articles(
    articles
):

    """
    根据新闻 URL 去重。
    """

    seen = set()

    result = []

    for article in articles:

        link = article["link"]

        if not link:

            continue

        if link in seen:

            continue

        seen.add(link)

        result.append(
            article
        )

    return result


# ============================================================
# 关键词匹配
# ============================================================

def match_keywords(
    article
):

    """
    根据 config.py 中的 KEYWORDS
    给新闻打标签。

    例如：

    铜
    锂
    新能源
    供应
    政策
    """

    text = " ".join([

        article.get(
            "title",
            ""
        ),

        article.get(
            "summary",
            ""
        ),

        " ".join(
            article.get(
                "tags",
                []
            )
        )

    ]).lower()

    matched_tags = []

    # --------------------------------------------------------
    # 遍历分类
    # --------------------------------------------------------

    for category, keywords in KEYWORDS.items():

        for keyword in keywords:

            if keyword.lower() in text:

                matched_tags.append(
                    category
                )

                # 一个分类命中一次即可
                break

    return matched_tags


# ============================================================
# 排除关键词
# ============================================================

def contains_exclude_keyword(
    article
):

    """
    如果新闻包含排除关键词，
    则不进入后续流程。
    """

    text = " ".join([

        article.get(
            "title",
            ""
        ),

        article.get(
            "summary",
            ""
        ),

        " ".join(
            article.get(
                "tags",
                []
            )
        )

    ]).lower()

    for keyword in EXCLUDE_KEYWORDS:

        if keyword.lower() in text:

            return True

    return False


# ============================================================
# 主程序
# ============================================================

def main():

    # ========================================================
    # 1. 初始化数据库
    # ========================================================

    initialize_database()

    # ========================================================
    # 2. 抓取 RSS
    # ========================================================

    articles = fetch_rss()

    print()
    print(
        "原始新闻数量：",
        len(articles)
    )

    # ========================================================
    # 3. 最近24小时
    # ========================================================

    articles = filter_last_24_hours(
        articles
    )

    print(
        "过去24小时：",
        len(articles)
    )

    # ========================================================
    # 4. 去重
    # ========================================================

    articles = deduplicate_articles(
        articles
    )

    print(
        "去重后：",
        len(articles)
    )

    # ========================================================
    # 5. 关键词筛选
    # ========================================================

    filtered_news = []

    for article in articles:

        # ----------------------------------------------------
        # 排除关键词
        # ----------------------------------------------------

        if contains_exclude_keyword(
            article
        ):

            continue

        # ----------------------------------------------------
        # 匹配关键词
        # ----------------------------------------------------

        matched_tags = match_keywords(
            article
        )

        # 没有匹配关键词
        # 不进入系统

        if not matched_tags:

            continue

        # ----------------------------------------------------
        # 使用我们的分类标签
        # ----------------------------------------------------

        article["tags"] = matched_tags

        filtered_news.append(
            article
        )

    print(
        "关键词筛选后：",
        len(filtered_news)
    )

    # ========================================================
    # 6. 保存新新闻
    # ========================================================

    new_count = 0

    old_count = 0

    for article in filtered_news:

        # ----------------------------------------------------
        # 数据库已经存在
        # ----------------------------------------------------

        if news_exists(
            article["link"]
        ):

            old_count += 1

        # ----------------------------------------------------
        # 新新闻
        # ----------------------------------------------------

        else:

            saved = save_news(
                article
            )

            if saved:

                new_count += 1

    # ========================================================
    # 数据库统计
    # ========================================================

    print()
    print("=" * 60)
    print("数据库")
    print("=" * 60)

    print()

    print(
        "新新闻：",
        new_count
    )

    print(
        "数据库中已有：",
        old_count
    )

    # ========================================================
    # 7. 获取尚未进行 AI 分析的新闻
    # ========================================================

    unprocessed_news = get_unprocessed_news(
        limit=AI_LIMIT
    )

    print()
    print("=" * 60)
    print("AI 新闻分析")
    print("=" * 60)

    print()

    print(
        "待 AI 分析：",
        len(unprocessed_news)
    )

    # ========================================================
    # 8. 没有待分析新闻
    # ========================================================

    if not unprocessed_news:

        print()

        print(
            "没有需要进行 AI 分析的新闻。"
        )

        print()

        print(
            "=" * 60
        )

        print(
            "任务完成"
        )

        print(
            "=" * 60
        )

        return

    # ========================================================
    # 9. DeepSeek AI 分析
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
            f"正在分析第 "
            f"{index}/{len(unprocessed_news)} 条"
        )

        print()

        print(
            article["title"]
        )

        try:

            # ------------------------------------------------
            # 调用 DeepSeek
            # ------------------------------------------------

            result = analyze_news(
                article
            )

            # ------------------------------------------------
            # 打印 AI 结果
            # ------------------------------------------------

            print()
            print(
                "AI 返回结果："
            )

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

            print(
                "✓ AI 分析结果已保存"
            )

            success_count += 1

        except Exception as e:

            print()

            print(
                "✗ AI 分析失败："
            )

            print(
                type(e).__name__
            )

            print(
                repr(e)
            )

            failed_count += 1

    # ========================================================
    # 10. 最终统计
    # ========================================================

    print()
    print("=" * 60)
    print("AI 分析完成")
    print("=" * 60)

    print()

    print(
        "成功：",
        success_count
    )

    print(
        "失败：",
        failed_count
    )

    print()

    print("=" * 60)
    print("任务完成")
    print("=" * 60)


# ============================================================
# 程序入口
# ============================================================

if __name__ == "__main__":

    main()
