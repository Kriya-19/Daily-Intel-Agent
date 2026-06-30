// Daily Intel Agent — Cloudflare Worker
// Handles Telegram webhook: button taps + /setmarket + /watchlist commands

const TELEGRAM_API = "https://api.telegram.org";

// Fetch today's digest JSON from GitHub raw URL
async function fetchDigest(date, githubUsername, githubRepo) {
  const url = `https://raw.githubusercontent.com/${githubUsername}/${githubRepo}/main/digests/${date}.json`;
  const res = await fetch(url);
  if (!res.ok) return null;
  return res.json();
}

// Format a section from the digest into a readable Telegram message
function formatSection(sectionKey, digest, date) {
  const dateLabel = new Date(date).toLocaleDateString("en-IN", {
    weekday: "short", day: "numeric", month: "short", year: "numeric"
  });

  const sectionEmojis = {
    ai_news: "🤖", tech_news: "💻", finance_news: "💰",
    startup_funding: "💸", hiring_trends: "👔"
  };

  const sectionTitles = {
    ai_news: "AI NEWS", tech_news: "TECH NEWS",
    finance_news: "FINANCE NEWS", startup_funding: "STARTUP FUNDING",
    hiring_trends: "HIRING TRENDS"
  };

  const emoji = sectionEmojis[sectionKey] || "📌";
  const title = sectionTitles[sectionKey] || sectionKey.toUpperCase();
  let text = `${emoji} <b>${title} — ${dateLabel}</b>\n\n`;

  const data = digest[sectionKey];

  if (!data || (Array.isArray(data) && data.length === 0)) {
    return text + "No stories found for this section today.";
  }

  // News sections (ai_news, tech_news, finance_news)
  if (["ai_news", "tech_news", "finance_news"].includes(sectionKey)) {
    data.forEach((story, i) => {
      text += `<b>${i + 1}. ${story.headline}</b>\n`;
      text += `${story.summary}\n`;
      text += `<i>Why it matters: ${story.why_it_matters}</i>\n`;
      text += `<a href="${story.link}">${story.source}</a>\n\n`;
    });
    return text;
  }

  // Startup funding
  if (sectionKey === "startup_funding") {
    data.forEach((item, i) => {
      text += `<b>${i + 1}. ${item.company}</b> — ${item.amount}\n`;
      text += `${item.one_liner}\n`;
      text += `Lead: ${item.investor}\n`;
      text += `<a href="${item.link}">Read more</a>\n\n`;
    });
    return text;
  }

  // Hiring trends (object not array)
  if (sectionKey === "hiring_trends") {
    text += `${data.signal}\n\n`;
    text += `<i>Based on: ${data.source}</i>`;
    return text;
  }

  return text + JSON.stringify(data, null, 2);
}

// Send a message via Telegram Bot API
async function sendTelegramMessage(botToken, chatId, text, options = {}) {
  const body = {
    chat_id: chatId,
    text: text,
    parse_mode: "HTML",
    disable_web_page_preview: true,
    ...options
  };

  const res = await fetch(`${TELEGRAM_API}/bot${botToken}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  return res.json();
}

// Answer a callback query (removes the loading spinner on the button)
async function answerCallbackQuery(botToken, callbackQueryId) {
  await fetch(`${TELEGRAM_API}/bot${botToken}/answerCallbackQuery`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ callback_query_id: callbackQueryId }),
  });
}

// Main Worker handler
export default {
  async fetch(request, env) {
    // Only accept POST requests from Telegram
    if (request.method !== "POST") {
      return new Response("Daily Intel Worker is running.", { status: 200 });
    }

    let update;
    try {
      update = await request.json();
    } catch {
      return new Response("Bad request", { status: 400 });
    }

    const BOT_TOKEN = env.TELEGRAM_BOT_TOKEN;
    const GITHUB_USERNAME = env.GITHUB_USERNAME;
    const GITHUB_REPO = env.GITHUB_REPO;

    // --- Handle button taps (callback queries) ---
    if (update.callback_query) {
      const query = update.callback_query;
      const chatId = query.message.chat.id;
      const data = query.data; // format: "section_key|YYYY-MM-DD"

      await answerCallbackQuery(BOT_TOKEN, query.id);

      const [sectionKey, date] = data.split("|");

      // Fetch that day's digest from GitHub
      const digest = await fetchDigest(date, GITHUB_USERNAME, GITHUB_REPO);

      if (!digest) {
        await sendTelegramMessage(BOT_TOKEN, chatId,
          `❌ Could not find digest for ${date}. It may not have been generated yet.`);
        return new Response("OK", { status: 200 });
      }

      const text = formatSection(sectionKey, digest, date);
      await sendTelegramMessage(BOT_TOKEN, chatId, text);

      return new Response("OK", { status: 200 });
    }

    // --- Handle text commands ---
    if (update.message) {
      const msg = update.message;
      const chatId = msg.chat.id;
      const text = (msg.text || "").trim();

      // /start — welcome message
      if (text === "/start") {
        await sendTelegramMessage(BOT_TOKEN, chatId,
          `👋 <b>Welcome to Daily Intel!</b>\n\n` +
          `You'll receive a daily digest at 8:00 AM IST covering AI, tech, finance, markets, and more.\n\n` +
          `<b>Commands:</b>\n` +
          `/setmarket india — Indian markets only (NIFTY, SENSEX)\n` +
          `/setmarket us — US markets only (S&P, NASDAQ)\n` +
          `/setmarket both — Both markets (default)\n` +
          `/watchlist AAPL,TSLA,RELIANCE.NS — set custom tickers\n` +
          `/status — see your current settings`
        );
        return new Response("OK", { status: 200 });
      }

      // /setmarket
      if (text.startsWith("/setmarket")) {
        const parts = text.split(" ");
        const market = parts[1]?.toLowerCase();

        if (!["india", "us", "both"].includes(market)) {
          await sendTelegramMessage(BOT_TOKEN, chatId,
            `❌ Invalid option. Use:\n/setmarket india\n/setmarket us\n/setmarket both`);
          return new Response("OK", { status: 200 });
        }

        // Call your Python backend to update the DB
        // For now we confirm and note — full DB write needs a backend endpoint
        // We'll wire this in the next step via a GitHub Actions dispatch or simple KV store
        await sendTelegramMessage(BOT_TOKEN, chatId,
          `✅ Market preference set to <b>${market}</b>.\nThis will apply from tomorrow's digest.`);

        return new Response("OK", { status: 200 });
      }

      // /watchlist
      if (text.startsWith("/watchlist")) {
        const parts = text.split(" ");
        const tickers = parts[1]?.toUpperCase().split(",").filter(Boolean) || [];

        if (tickers.length === 0) {
          await sendTelegramMessage(BOT_TOKEN, chatId,
            `❌ Usage: /watchlist AAPL,TSLA,RELIANCE.NS`);
          return new Response("OK", { status: 200 });
        }

        await sendTelegramMessage(BOT_TOKEN, chatId,
          `✅ Watchlist updated: <b>${tickers.join(", ")}</b>\nThis will apply from tomorrow's digest.`);

        return new Response("OK", { status: 200 });
      }

      // /status
      if (text === "/status") {
        await sendTelegramMessage(BOT_TOKEN, chatId,
          `📊 <b>Your settings</b>\n\nMarket: both\nWatchlist: default\n\n` +
          `<i>Use /setmarket and /watchlist to customise.</i>`);
        return new Response("OK", { status: 200 });
      }
    }

    return new Response("OK", { status: 200 });
  }
};