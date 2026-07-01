# import feedparser
# from datetime import datetime

# # Each tuple: (feed URL, source name, category)
# # Category is what we'll use later to route stories into sections
# RSS_FEEDS = [
#     # Tech
#     ("https://hnrss.org/frontpage", "Hacker News", "tech"),
#     ("https://techcrunch.com/feed/", "TechCrunch", "tech"),
#     ("https://www.theverge.com/rss/index.xml", "The Verge", "tech"),
#     ("https://feeds.arstechnica.com/arstechnica/index", "Ars Technica", "tech"),
#     # Finance
#     ("https://feeds.reuters.com/reuters/businessNews", "Reuters Business", "finance"),
#     ("https://finance.yahoo.com/news/rssindex", "Yahoo Finance", "finance"),
#     ("https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", "ET Markets", "finance"),
#     ("https://www.moneycontrol.com/rss/marketreports.xml", "Moneycontrol", "finance"),
# ]

# def fetch_all_feeds():
#     """
#     Fetches all RSS feeds and returns a flat list of article dicts.
#     Each article has: title, summary, link, source, category, published
#     """
#     articles = []

#     for url, source_name, category in RSS_FEEDS:
#         try:
#             feed = feedparser.parse(url)
            
#             for entry in feed.entries[:15]:  # cap at 15 per feed
#                 # feedparser normalizes most RSS formats
#                 # but field names vary across feeds, so we handle missing fields
#                 title = entry.get("title", "").strip()
#                 summary = entry.get("summary", entry.get("description", "")).strip()
#                 link = entry.get("link", "").strip()

#                 # Skip if no title or link — useless article
#                 if not title or not link:
#                     continue

#                 # Truncate summary to 500 chars — we only need a hint for the dedup/summarizer
#                 # The LLM doesn't need the full article body
#                 if len(summary) > 500:
#                     summary = summary[:500] + "..."

#                 articles.append({
#                     "title": title,
#                     "summary": summary,
#                     "link": link,
#                     "source": source_name,
#                     "category": category,
#                     "published": entry.get("published", datetime.now().isoformat()),
#                 })

#         except Exception as e:
#             # Don't crash the whole pipeline if one feed fails
#             # Just log and move on — reliability matters more than completeness
#             print(f"[RSS] Failed to fetch {source_name}: {e}")

#     print(f"[RSS] Fetched {len(articles)} articles total")
#     return articles







































import feedparser
import re
import socket
from datetime import datetime

RSS_FEEDS = [
    ("https://techcrunch.com/category/artificial-intelligence/feed/", "TechCrunch AI", "ai"),
    ("https://venturebeat.com/category/ai/feed/", "VentureBeat AI", "ai"),
    ("https://www.theverge.com/rss/index.xml", "The Verge", "tech"),
    ("https://feeds.arstechnica.com/arstechnica/index", "Ars Technica", "tech"),
    ("https://techcrunch.com/feed/", "TechCrunch", "tech"),
    ("https://feeds.reuters.com/reuters/businessNews", "Reuters Business", "finance"),
    ("https://feeds.reuters.com/reuters/technologyNews", "Reuters Tech", "tech"),
    ("https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", "ET Markets", "finance"),
    ("https://economictimes.indiatimes.com/tech/rssfeeds/13357270.cms", "ET Tech", "tech"),
    ("https://techcrunch.com/category/startups/feed/", "TechCrunch Startups", "funding"),
    ("https://hnrss.org/frontpage?points=100", "Hacker News", "tech"),
]

NOISE_KEYWORDS = [
    "good stock to buy", "should you buy", "price target",
    "analyst rating", "stock forecast", "buy or sell",
    "dividend", "earnings estimate", "price prediction",
    "here's why", "here is why", "is it a buy",
    "reddit", "wallstreetbets", "meme stock",
]

MIN_TITLE_LENGTH = 20

def clean_text(text):
    text = text.replace("&#8216;", "'").replace("&#8217;", "'")
    text = text.replace("&#8220;", '"').replace("&#8221;", '"')
    text = text.replace("&#39;", "'").replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&nbsp;", " ")
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()

def is_noise(title):
    title_lower = title.lower()
    return any(kw in title_lower for kw in NOISE_KEYWORDS)

def fetch_feed_with_timeout(url, timeout=8):
    """Wraps feedparser.parse with a socket timeout."""
    old_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(timeout)
        return feedparser.parse(url)
    finally:
        # Always restore original timeout even if parse throws
        socket.setdefaulttimeout(old_timeout)

def fetch_all_feeds():
    articles = []
    seen_titles = set()

    for url, source_name, category in RSS_FEEDS:
        print(f"[RSS] Fetching {source_name}...")
        try:
            feed = fetch_feed_with_timeout(url, timeout=8)
            count = 0

            for entry in feed.entries:
                cap = 8 if category == "ai" else 6
                if count >= cap:
                    break

                title = clean_text(entry.get("title", "").strip())
                summary = clean_text(entry.get("summary", entry.get("description", "")).strip())
                link = entry.get("link", "").strip()

                if not title or not link:
                    continue
                if len(title) < MIN_TITLE_LENGTH:
                    continue
                if is_noise(title):
                    continue
                if title.lower() in seen_titles:
                    continue

                seen_titles.add(title.lower())

                if len(summary) > 400:
                    summary = summary[:400] + "..."

                articles.append({
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "source": source_name,
                    "category": category,
                    "published": entry.get("published", datetime.now().isoformat()),
                })
                count += 1

        except Exception as e:
            print(f"[RSS] Failed to fetch {source_name}: {e}")

    print(f"[RSS] Fetched {len(articles)} articles after quality filtering")
    return articles