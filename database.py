import sqlite3


DATABASE_FILE = "news.db"


def get_connection():

    conn = sqlite3.connect(DATABASE_FILE)

    return conn


def initialize_database():

    conn = get_connection()

    cursor = conn.cursor()

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

            ai_summary TEXT,

            processed INTEGER DEFAULT 0,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )
    """)

    conn.commit()

    conn.close()


def news_exists(link):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM news WHERE link = ?",
        (link,)
    )

    result = cursor.fetchone()

    conn.close()

    return result is not None


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

        saved = False

    conn.close()

    return saved
