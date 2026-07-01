# import yfinance as yf

# # Default tickers if user has no custom watchlist
# DEFAULT_INDIA = ["^NSEI", "^BSESN"]       # NIFTY 50, SENSEX
# DEFAULT_US = ["^GSPC", "^IXIC", "AAPL", "TSLA", "NVDA", "MSFT"]

# # Human-readable names for index tickers
# TICKER_LABELS = {
#     "^NSEI": "NIFTY 50",
#     "^BSESN": "SENSEX",
#     "^GSPC": "S&P 500",
#     "^IXIC": "NASDAQ",
# }

# def fetch_market_data(market="both", custom_tickers=None):
#     """
#     Fetches current price and % change for relevant tickers.
#     market: "india", "us", or "both"
#     custom_tickers: list of additional tickers from user's watchlist
#     Returns a list of dicts: {ticker, label, price, change_pct, currency}
#     """
#     tickers = []

#     if market in ("india", "both"):
#         tickers += DEFAULT_INDIA
#     if market in ("us", "both"):
#         tickers += DEFAULT_US
#     if custom_tickers:
#         tickers += custom_tickers

#     # Deduplicate while preserving order
#     seen = set()
#     tickers = [t for t in tickers if not (t in seen or seen.add(t))]

#     results = []

#     for ticker_symbol in tickers:
#         try:
#             ticker = yf.Ticker(ticker_symbol)
#             info = ticker.fast_info  # fast_info is lighter than full .info call

#             price = info.last_price
#             prev_close = info.previous_close

#             if price is None or prev_close is None:
#                 continue

#             change_pct = ((price - prev_close) / prev_close) * 100
            
#             # Use human label if available, else use ticker symbol directly
#             label = TICKER_LABELS.get(ticker_symbol, ticker_symbol)
            
#             # Determine currency — Indian tickers quote in INR
#             currency = "₹" if ticker_symbol.endswith(".NS") or ticker_symbol in ["^NSEI", "^BSESN"] else "$"

#             results.append({
#                 "ticker": ticker_symbol,
#                 "label": label,
#                 "price": round(price, 2),
#                 "change_pct": round(change_pct, 2),
#                 "currency": currency,
#             })

#         except Exception as e:
#             print(f"[Market] Failed to fetch {ticker_symbol}: {e}")

#     print(f"[Market] Fetched data for {len(results)} tickers")
#     return results






import yfinance as yf

DEFAULT_INDIA = ["^NSEI", "^BSESN"]
DEFAULT_US = ["^GSPC", "^IXIC", "AAPL", "TSLA", "NVDA", "MSFT"]

TICKER_LABELS = {
    "^NSEI": "NIFTY 50",
    "^BSESN": "SENSEX",
    "^GSPC": "S&P 500",
    "^IXIC": "NASDAQ",
}

def fetch_market_data(market="both", custom_tickers=None):
    tickers = []

    if market in ("india", "both"):
        tickers += DEFAULT_INDIA
    if market in ("us", "both"):
        tickers += DEFAULT_US
    if custom_tickers:
        tickers += custom_tickers

    # Deduplicate while preserving order
    seen = set()
    tickers = [t for t in tickers if not (t in seen or seen.add(t))]

    results = []

    for ticker_symbol in tickers:
        try:
            ticker = yf.Ticker(ticker_symbol)
            
            # Use history() instead of fast_info — more reliable on cloud IPs
            hist = ticker.history(period="2d")
            
            if hist.empty or len(hist) < 2:
                # Try just 1 day — markets may be closed yesterday
                hist = ticker.history(period="5d")
            
            if hist.empty or len(hist) < 1:
                print(f"[Market] No data for {ticker_symbol}")
                continue

            # Latest close and previous close
            latest = hist["Close"].iloc[-1]
            previous = hist["Close"].iloc[-2] if len(hist) >= 2 else hist["Close"].iloc[-1]

            change_pct = ((latest - previous) / previous) * 100
            label = TICKER_LABELS.get(ticker_symbol, ticker_symbol)
            currency = "₹" if ticker_symbol.endswith(".NS") or ticker_symbol in ["^NSEI", "^BSESN"] else "$"

            results.append({
                "ticker": ticker_symbol,
                "label": label,
                "price": round(latest, 2),
                "change_pct": round(change_pct, 2),
                "currency": currency,
            })

        except Exception as e:
            print(f"[Market] Failed to fetch {ticker_symbol}: {e}")

    print(f"[Market] Fetched data for {len(results)} tickers")
    return results