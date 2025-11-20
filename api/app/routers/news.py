# api/app/routers/news.py
from __future__ import annotations

import os
from typing import Any, Dict, List

import requests
from fastapi import APIRouter, HTTPException, Query
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

router = APIRouter(prefix="/news", tags=["news"])

ALPHAVANTAGE_KEY = os.getenv("ALPHAVANTAGE_KEY")

if not ALPHAVANTAGE_KEY:
    print("⚠ ALPHAVANTAGE_KEY não encontrado no .env")


def _fetch_alpha_news(symbol: str) -> Dict[str, Any]:
    """
    Chama o endpoint NEWS_SENTIMENT da Alpha Vantage.
    """
    if not ALPHAVANTAGE_KEY:
        raise HTTPException(500, "ALPHAVANTAGE_KEY em falta")

    base_symbol = symbol.split(".")[0]  # ASML.AS -> ASML

    url = (
        "https://www.alphavantage.co/query"
        f"?function=NEWS_SENTIMENT&tickers={base_symbol}&apikey={ALPHAVANTAGE_KEY}"
    )

    res = requests.get(url, timeout=10)
    if res.status_code != 200:
        raise HTTPException(
            500,
            f"AlphaVantage HTTP error: {res.status_code} {res.text}",
        )

    data = res.json()

    if "feed" not in data:
        if "Note" in data:
            raise HTTPException(429, f"AlphaVantage limit: {data['Note']}")
        raise HTTPException(404, f"Sem notícias para {symbol}")

    return data


def _parse_alpha_time(raw: str | None) -> str | None:
    """
    Converte '20251118T203000' -> '2025-11-18T20:30:00Z'
    para o JS conseguir fazer new Date(...).
    """
    if not raw:
        return None
    try:
        # Formato: YYYYMMDDThhmmss
        year = int(raw[0:4])
        month = int(raw[4:6])
        day = int(raw[6:8])
        hour = int(raw[9:11])
        minute = int(raw[11:13])
        second = int(raw[13:15])

        dt = datetime(
            year=year,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            second=second,
            tzinfo=timezone.utc,
        )
        return dt.isoformat()
    except Exception:
        return None


@router.get("/items")
def get_news_items(symbol: str = Query(...)) -> List[Dict[str, Any]]:
    """
    Lista de notícias para o símbolo (título, publisher, link, data).
    """
    data = _fetch_alpha_news(symbol)
    feed = data.get("feed", [])

    out: List[Dict[str, Any]] = []

    for item in feed:
        out.append(
            {
                "title": item.get("title", ""),
                "publisher": item.get("source", ""),
                "link": item.get("url", ""),
                "time": _parse_alpha_time(item.get("time_published")),
                "type": "article",
            }
        )

    return out


@router.get("/sentiment")
def get_sentiment(symbol: str = Query(...)) -> Dict[str, Any]:
    """
    Sentimento médio com base no ticker_sentiment dos artigos.
    """
    data = _fetch_alpha_news(symbol)
    feed = data.get("feed", [])

    if not feed:
        return {"label": "neutral", "score": 0.0, "count": 0}

    scores: List[float] = []

    base = symbol.split(".")[0].upper()

    for item in feed:
        for ts in item.get("ticker_sentiment", []):
            ticker = (ts.get("ticker") or "").upper()
            if not ticker.startswith(base):
                continue
            try:
                s = float(ts.get("ticker_sentiment_score", 0.0))
                scores.append(s)
            except Exception:
                continue

    if not scores:
        return {"label": "neutral", "score": 0.0, "count": 0}

    avg = sum(scores) / len(scores)

    if avg > 0.15:
        label = "positive"
    elif avg < -0.15:
        label = "negative"
    else:
        label = "neutral"

    return {
        "label": label,
        "score": avg,
        "count": len(scores),
    }
