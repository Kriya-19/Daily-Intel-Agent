import feedparser
from datetime import datetime

# Each tuple: (feed URL, source name, category)
# Category is what we'll use later to route stories into sections
RSS_FEEDS = [
    # Tech
    ("https://hnrss.org/frontpage", "Hacker News", "tech"),
    ("https://techcrunch.com/feed/", "TechCrunch", "tech"),
    ("https://www.theverge.com/rss/index.xml", "The Verge", "tech"),
    ("https://feeds.arstechnica.com/arstechnica/index", "Ars Technica", "tech"),
    # Finance
    ("https://feeds.reuters.com/reuters/businessNews", "Reuters Business", "finance"),
    ("https://finance.yahoo.com/news/rssindex", "Yahoo Finance", "finance"),
    ("https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", "ET Markets", "finance"),
    ("https://www.moneycontrol.com/rss/marketreports.xml", "Moneycontrol", "finance"),
]

def fetch_all_feeds():
    """
    Fetches all RSS feeds and returns a flat list of article dicts.
    Each article has: title, summary, link, source, category, published
    """
    articles = []

    for url, source_name, category in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            
            for entry in feed.entries[:15]:  # cap at 15 per feed
                # feedparser normalizes most RSS formats
                # but field names vary across feeds, so we handle missing fields
                title = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                link = entry.get("link", "").strip()

                # Skip if no title or link — useless article
                if not title or not link:
                    continue

                # Truncate summary to 500 chars — we only need a hint for the dedup/summarizer
                # The LLM doesn't need the full article body
                if len(summary) > 500:
                    summary = summary[:500] + "..."

                articles.append({
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "source": source_name,
                    "category": category,
                    "published": entry.get("published", datetime.now().isoformat()),
                })

        except Exception as e:
            # Don't crash the whole pipeline if one feed fails
            # Just log and move on — reliability matters more than completeness
            print(f"[RSS] Failed to fetch {source_name}: {e}")

    print(f"[RSS] Fetched {len(articles)} articles total")
    return articles