import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "users.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def initialize_db():
    """Creates the users table if it doesn't exist. Run once on setup."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                chat_id     TEXT PRIMARY KEY,
                username    TEXT,
                market      TEXT DEFAULT 'both',
                watchlist   TEXT DEFAULT '[]',
                active      INTEGER DEFAULT 1,
                created_at  TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
    print("[UserStore] DB initialized.")

def add_user(chat_id, username=""):
    """Registers a new user. Does nothing if already exists."""
    with get_connection() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO users (chat_id, username)
            VALUES (?, ?)
        """, (str(chat_id), username))
        conn.commit()

def get_all_active_users():
    """Returns list of all active user dicts."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT chat_id, username, market, watchlist
            FROM users WHERE active = 1
        """).fetchall()
    return [
        {
            "chat_id": row[0],
            "username": row[1],
            "market": row[2],
            "watchlist": json.loads(row[3]),
        }
        for row in rows
    ]

def update_market(chat_id, market):
    """market must be 'india', 'us', or 'both'"""
    assert market in ("india", "us", "both"), "Invalid market value"
    with get_connection() as conn:
        conn.execute("UPDATE users SET market = ? WHERE chat_id = ?", (market, str(chat_id)))
        conn.commit()

def update_watchlist(chat_id, tickers):
    """tickers: list of strings e.g. ['AAPL', 'RELIANCE.NS']"""
    with get_connection() as conn:
        conn.execute("UPDATE users SET watchlist = ? WHERE chat_id = ?",
                     (json.dumps(tickers), str(chat_id)))
        conn.commit()