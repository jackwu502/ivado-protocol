"""A minimal MCP server exposing stock-market tools backed by yfinance.

Run directly:  python stock_mcp_server.py
This server speaks the Model Context Protocol over stdio.

In production you would point to a company-maintained MCP server such as
Alpha Vantage's official one (https://mcp.alphavantage.co/). yfinance is
used here so the lab runs without any API key.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import yfinance as yf
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("stock-server")


@mcp.tool()
def get_quote(ticker: str) -> dict:
    """Get the latest quote for a ticker (price, change, volume).

    Example: get_quote("NVDA")
    """
    t = yf.Ticker(ticker)
    info = t.fast_info
    hist = t.history(period="2d")
    if hist.empty:
        return {"error": f"no data for {ticker}"}
    last = hist.iloc[-1]
    prev = hist.iloc[-2] if len(hist) >= 2 else last
    change = float(last["Close"] - prev["Close"])
    pct = float((change / prev["Close"]) * 100) if prev["Close"] else 0.0
    return {
        "ticker": ticker.upper(),
        "price": float(last["Close"]),
        "change": change,
        "change_pct": pct,
        "volume": int(last["Volume"]),
        "currency": getattr(info, "currency", "USD"),
        "timestamp": str(hist.index[-1].date()),
    }


@mcp.tool()
def get_history(ticker: str, days: int = 30) -> dict:
    """Get daily closing prices for the last N days.

    Example: get_history("NVDA", days=7)
    """
    end = datetime.utcnow().date()
    start = end - timedelta(days=days * 2)  # buffer for weekends/holidays
    hist = yf.Ticker(ticker).history(start=start, end=end + timedelta(days=1))
    if hist.empty:
        return {"error": f"no data for {ticker}"}
    hist = hist.tail(days)
    return {
        "ticker": ticker.upper(),
        "dates": [str(d.date()) for d in hist.index],
        "closes": [float(x) for x in hist["Close"]],
        "highs": [float(x) for x in hist["High"]],
        "lows": [float(x) for x in hist["Low"]],
    }


@mcp.tool()
def get_company_info(ticker: str) -> dict:
    """Get company name, sector, industry, market cap.

    Example: get_company_info("NVDA")
    """
    info = yf.Ticker(ticker).info or {}
    return {
        "ticker": ticker.upper(),
        "name": info.get("longName") or info.get("shortName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "market_cap": info.get("marketCap"),
        "summary": (info.get("longBusinessSummary") or "")[:500],
    }


@mcp.tool()
def get_news_headlines(ticker: str, limit: int = 5) -> dict:
    """Get recent news headlines for a ticker.

    Example: get_news_headlines("NVDA", limit=3)
    """
    items = yf.Ticker(ticker).news or []
    headlines = []
    for it in items[:limit]:
        # yfinance recently changed schema; tolerate both shapes
        content = it.get("content") or it
        headlines.append({
            "title": content.get("title") or it.get("title"),
            "publisher": (content.get("provider") or {}).get("displayName") or it.get("publisher"),
            "url": (content.get("canonicalUrl") or {}).get("url") or it.get("link"),
        })
    return {"ticker": ticker.upper(), "headlines": headlines}


if __name__ == "__main__":
    mcp.run(transport="stdio")
