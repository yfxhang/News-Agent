import sqlite3


# =========================
# 数据库文件
# =========================

DATABASE_FILE = "news.db"


# =========================
# 获取数据库连接
# =========================

def get_connection():

    conn = sqlite3.connect(DATABASE_FILE)

    return conn


# =========================
# 初始化 / 升级数据库
# =========================

def initialize_database():

    conn = get_connection()

    cursor = conn.cursor()

    # -------------------------
    # 创建新闻表
    # -------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS news (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            title TEXT NOT NULL,

            link TEXT UNIQUE NOT NULL,

            summary TEXT,

            published TEXT,

            tags TEXT,

            ai_score INTEGER,

            ai_category TEXT,

            ai_metals TEXT,

            ai_industry_impact TEXT,

            ai_price_impact TEXT,

            ai_summary TEXT,

            ai_push INTEGER DEFAULT 0,

            processed INTEGER DEFAULT 0,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )
    """)

    # -------------------------
    # 数据库升级
    #
    # 如果 news.db 是旧版本创建的，
    # 自动增加缺少的 AI 字段。
    # -------------------------

    columns = [

        ("ai_score", "INTEGER"),

        ("ai_category", "TEXT"),

        ("ai_metals", "TEXT"),

        ("ai_industry_impact", "TEXT"),

        ("ai_price_impact", "TEXT"),

        ("ai_summary", "TEXT"),

        ("ai_push", "INTEGER DEFAULT 0"),

        ("processed", "INTEGER DEFAULT 0")

    ]

    for column_name, column_type in columns:

        try:

            cursor.execute(
                f"""
                ALTER TABLE news
                ADD COLUMN {column_name} {column_type}
                """
            )

        except sqlite3.OperationalError:

            # 如果字段已经存在，就跳过
            pass

    conn.commit()

    conn.close()


# =========================
# 检查新闻是否已经存在
# =========================

def news_exists(link):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id
        FROM news
        WHERE link = ?
        """,
        (link,)
    )

    result = cursor.fetchone()

    conn.close()

    return result is not None


# =========================
# 保存新闻
# =========================

def save_news(article):

    conn = get_connection()

    cursor = conn.cursor()

    try:

        cursor.execute("""
            INSERT INTO news (

                title,
                link,
                summary,
                published,
                tags

            )

            VALUES (?, ?, ?, ?, ?)
        """, (

            article["title"],

            article["link"],

            article["summary"],

            article["published"],

            ",".join(article["tags"])

        ))

        conn.commit()

        saved = True

    except sqlite3.IntegrityError:

        # URL 已经存在
        saved = False

    conn.close()

    return saved


# =========================
# 保存 AI 分析结果
# =========================

def save_ai_result(link, result):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        UPDATE news

        SET

            ai_score = ?,

            ai_category = ?,

            ai_metals = ?,

            ai_industry_impact = ?,

            ai_price_impact = ?,

            ai_summary = ?,

            ai_push = ?,

            processed = 1

        WHERE link = ?

    """, (

        result.get("importance"),

        result.get("category"),

        ",".join(result.get("metals", [])),

        result.get("industry_impact"),

        result.get("price_impact"),

        result.get("summary"),

        1 if result.get("push") else 0,

        link

    ))

    conn.commit()

    conn.close()


# =========================
# 获取尚未经过 AI 分析的新闻
# =========================

def get_unprocessed_news(limit=None):

    conn = get_connection()

    cursor = conn.cursor()

    sql = """
        SELECT
            id,
            title,
            link,
            summary,
            published,
            tags

        FROM news

        WHERE processed = 0

        ORDER BY published DESC
    """

    if limit is not None:

        sql += " LIMIT ?"

        cursor.execute(sql, (limit,))

    else:

        cursor.execute(sql)

    rows = cursor.fetchall()

    conn.close()

    news = []

    for row in rows:

        news.append({

            "id": row[0],

            "title": row[1],

            "link": row[2],

            "summary": row[3] or "",

            "published": row[4] or "",

            "tags": row[5].split(",") if row[5] else []

        })

    return news


# =========================
# 获取已经经过 AI 分析的新闻
# =========================

def get_processed_news(limit=None):

    conn = get_connection()

    cursor = conn.cursor()

    sql = """
        SELECT
            id,
            title,
            link,
            summary,
            published,
            tags,
            ai_score,
            ai_category,
            ai_metals,
            ai_industry_impact,
            ai_price_impact,
            ai_summary,
            ai_push

        FROM news

        WHERE processed = 1

        ORDER BY published DESC
    """

    if limit is not None:

        sql += " LIMIT ?"

        cursor.execute(sql, (limit,))

    else:

        cursor.execute(sql)

    rows = cursor.fetchall()

    conn.close()

    news = []

    for row in rows:

        news.append({

            "id": row[0],

            "title": row[1],

            "link": row[2],

            "summary": row[3] or "",

            "published": row[4] or "",

            "tags": row[5].split(",") if row[5] else [],

            "ai_score": row[6],

            "ai_category": row[7],

            "ai_metals": row[8].split(",") if row[8] else [],

            "ai_industry_impact": row[9],

            "ai_price_impact": row[10],

            "ai_summary": row[11],

            "ai_push": bool(row[12])

        })

    return news
