"""Download fundamental and historical price data from Yahoo Finance via yfinance."""

import time
import pandas as pd
import yfinance as yf


def _normalize_div_yield(raw) -> float:
    """
    yfinance inconsistently returns dividendYield as decimal (0.0376) or
    percentage (3.76) depending on the exchange. Normalize to decimal.
    """
    if not raw:
        return 0.0
    return raw / 100 if raw > 1.0 else raw


def fetch_fundamentals(ticker: str, sleep: float = 0.3) -> dict | None:
    """
    Return a dict of fundamental data for `ticker`, or None if data is insufficient.
    Sleeps `sleep` seconds after each call to avoid rate-limiting.
    """
    try:
        info = yf.Ticker(ticker).info
        time.sleep(sleep)

        pe = info.get("trailingPE")
        growth = info.get("earningsGrowth") or info.get("earningsQuarterlyGrowth")

        if pe is None or growth is None:
            return None
        if pe <= 0 or growth <= 0:
            return None

        return {
            "ticker": ticker,
            "name": info.get("shortName", ticker),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "price": info.get("currentPrice"),
            "market_cap": info.get("marketCap"),
            "pe": pe,
            "earnings_growth": growth,
            "debt_to_equity": info.get("debtToEquity"),
            "free_cash_flow": info.get("freeCashflow"),
            "dividend_yield": _normalize_div_yield(info.get("dividendYield")),
            "total_cash": info.get("totalCash"),
            "total_debt": info.get("totalDebt"),
            "trailing_eps": info.get("trailingEps"),
        }
    except Exception:
        time.sleep(sleep)
        return None


def fetch_fundamentals_lenient(ticker: str, sleep: float = 0.3) -> dict | None:
    """
    Like fetch_fundamentals but returns partial data even without PE/growth.
    Used for watchlist mode where we want technical data regardless.
    """
    try:
        info = yf.Ticker(ticker).info
        time.sleep(sleep)

        pe = info.get("trailingPE")
        growth = info.get("earningsGrowth") or info.get("earningsQuarterlyGrowth")

        if not info.get("shortName") and not info.get("currentPrice"):
            return None

        return {
            "ticker": ticker,
            "name": info.get("shortName", ticker),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "price": info.get("currentPrice"),
            "market_cap": info.get("marketCap"),
            "pe": pe if (pe and pe > 0) else None,
            "earnings_growth": growth if (growth and growth > 0) else None,
            "debt_to_equity": info.get("debtToEquity"),
            "free_cash_flow": info.get("freeCashflow"),
            "dividend_yield": _normalize_div_yield(info.get("dividendYield")),
            "total_cash": info.get("totalCash"),
            "total_debt": info.get("totalDebt"),
            "trailing_eps": info.get("trailingEps"),
        }
    except Exception:
        time.sleep(sleep)
        return None


def fetch_history(ticker: str, period: str = "1y", sleep: float = 0.2) -> pd.Series | None:
    """
    Return a pandas Series of daily closing prices for `ticker`.
    Returns None if fewer than 35 bars are available (minimum for MACD).
    """
    try:
        hist = yf.Ticker(ticker).history(period=period)
        time.sleep(sleep)
        if hist.empty or len(hist) < 35:
            return None
        return hist["Close"].dropna()
    except Exception:
        time.sleep(sleep)
        return None
