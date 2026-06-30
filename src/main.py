import os
import sys
import tempfile
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Add project root to path so imports work from GitHub Actions
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.collectors.rss_collector import fetch_all_feeds
from src.collectors.market_collector import fetch_market_data
from src.processing.dedup import deduplicate_articles
from src.processing.summarizer import generate_digest
from src.charts.chart_generator import generate_market_chart
from src.delivery.telegram_sender import send_digest_sync
from src.storage.user_store import get_all_active_users, initialize_db
from src.storage.digest_store import save_digest
from src.dashboard.build_dashboard import build_dashboard

def run():
    print(f"\n{'='*50}")
    print(f"Daily Intel Agent — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    # 1. Collect news
    articles = fetch_all_feeds()

    # 2. Dedup
    articles = deduplicate_articles(articles)

    # 3. Summarize — one call, all sections
    digest = generate_digest(articles)

    # 4. Save digest JSON for button replay later
    date_str = datetime.now().strftime("%Y-%m-%d")
    save_digest(digest, date_str)
    # build_dashboard(digest, [], date_str)


    # 5. Get all registered users
    initialize_db()
    users = get_all_active_users()

    if not users:
        print("[Main] No active users found. Add yourself via user_store.add_user().")
        return

    # 6. For each user: fetch their market data, generate their chart, send
    for user in users:
        print(f"\n[Main] Processing user {user['chat_id']}...")

        # Fetch market data personalised to this user
        market_data = fetch_market_data(
            market=user["market"],
            custom_tickers=user["watchlist"],
        )

        # Generate chart to a temp file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            chart_path = f.name

        generate_market_chart(market_data, chart_path)
        build_dashboard(digest, market_data, date_str)


        # Send both messages
        send_digest_sync(
            chat_id=user["chat_id"],
            digest=digest,
            market_data=market_data,
            chart_path=chart_path,
            date_str=date_str,
        )

        # Clean up temp chart file
        os.unlink(chart_path)

    print(f"\n[Main] Done. Digest sent to {len(users)} user(s).")

if __name__ == "__main__":
    run()