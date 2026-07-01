import asyncio
import os
from datetime import datetime
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def format_brief(digest, market_data):
    """
    Formats Message 1 — the short scannable brief.
    One line per section, most important headline only.
    """
    today = datetime.now().strftime("%a, %d %b")

    # Pull the top headline from each section
    ai_top = digest["ai_news"][0]["headline"] if digest.get("ai_news") else "No stories today"
    tech_top = digest["tech_news"][0]["headline"] if digest.get("tech_news") else "No stories today"
    finance_top = digest["finance_news"][0]["headline"] if digest.get("finance_news") else "No stories today"
    funding_top = (
        f"{digest['startup_funding'][0]['company']} raises {digest['startup_funding'][0]['amount']}"
        if digest.get("startup_funding") else "No funding news today"
    )
    contrarian = digest["contrarian_insight"]["take"][:80] + "..." if digest.get("contrarian_insight") else ""

    # Build market line from top 2-3 tickers
    market_line = "  ·  ".join([
        f"{d['label']} {'+' if d['change_pct'] >= 0 else ''}{d['change_pct']}%"
        for d in market_data[:3]
    ]) if market_data else "Market data unavailable"

    # Count total stories
    total = (
        len(digest.get("ai_news", [])) +
        len(digest.get("tech_news", [])) +
        len(digest.get("finance_news", []))
    )

    # Telegram MarkdownV2 requires escaping certain chars
    # We use HTML parse mode instead — much simpler to work with
    text = (
        f"☀️ <b>{today} · Daily Intel</b>\n\n"
        f"🤖 <b>AI</b>   {ai_top}\n"
        f"💻 <b>Tech</b>  {tech_top}\n"
        f"💰 <b>Finance</b>  {finance_top}\n"
        f"💸 <b>Funding</b>  {funding_top}\n"
        f"📈 <b>Markets</b>  {market_line}\n"
        f"🔥 <b>Take</b>  {contrarian}\n\n"
        f"<i>— {total} stories today · tap a section to expand</i>"
    )
    return text

def build_buttons(date_str):
    """
    Builds the inline keyboard for Message 1.
    callback_data format: "section|YYYY-MM-DD"
    The Worker uses this to know which section + which day's digest to serve.
    """
    keyboard = [
        [
            InlineKeyboardButton("🤖 AI", callback_data=f"ai_news|{date_str}"),
            InlineKeyboardButton("💻 Tech", callback_data=f"tech_news|{date_str}"),
            InlineKeyboardButton("💰 Finance", callback_data=f"finance_news|{date_str}"),
        ],
        [
            InlineKeyboardButton("💸 Funding", callback_data=f"startup_funding|{date_str}"),
            InlineKeyboardButton("👔 Hiring", callback_data=f"hiring_trends|{date_str}"),
            InlineKeyboardButton("📊 Dashboard", url="https://Kriya-19.github.io/Daily-Intel-Agent"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

def format_market_caption(market_data):
    """Caption for the chart image — Message 2."""
    lines = [f"{d['label']}: {d['currency']}{d['price']:,.2f} ({'+' if d['change_pct'] >= 0 else ''}{d['change_pct']}%)"
             for d in market_data]
    return "\n".join(lines)

async def send_digest(chat_id, digest, market_data, chart_path, date_str):
    """Sends Message 1 (brief + buttons) and Message 2 (chart image)."""
    bot = Bot(token=BOT_TOKEN)

    # Message 1 — The Brief
    await bot.send_message(
        chat_id=chat_id,
        text=format_brief(digest, market_data),
        parse_mode="HTML",
        reply_markup=build_buttons(date_str),
    )

    # Message 2 — Chart image
    # Message 2 — Chart image (only send if chart exists and has content)
    if chart_path and os.path.exists(chart_path) and os.path.getsize(chart_path) > 0:
        caption = format_market_caption(market_data)
        with open(chart_path, "rb") as photo:
            await bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=caption,
            )
    else:
        # Fallback — send market data as text if chart failed
        if market_data:
            caption = "📈 <b>Markets</b>\n\n" + format_market_caption(market_data)
            await bot.send_message(
                chat_id=chat_id,
                text=caption,
                parse_mode="HTML",
            )
        else:
            await bot.send_message(
                chat_id=chat_id,
                text="📈 <b>Markets</b>\n\nMarket data unavailable — exchanges may be closed.",
                parse_mode="HTML",
            )

    print(f"[Telegram] Sent digest to {chat_id}")

def send_digest_sync(chat_id, digest, market_data, chart_path, date_str):
    """Synchronous wrapper — use this from main.py"""
    asyncio.run(send_digest(chat_id, digest, market_data, chart_path, date_str))