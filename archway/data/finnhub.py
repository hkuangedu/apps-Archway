import os
import requests
import streamlit as st

BASE_URL = "https://finnhub.io/api/v1"


def _api_key() -> str:
    try:
        key = st.secrets.get("FINNHUB_API_KEY", "")
    except Exception:
        key = ""
    return key or os.environ.get("FINNHUB_API_KEY", "")


def _get(path: str, params: dict) -> dict | list:
    key = _api_key()
    if not key:
        raise RuntimeError(
            "FINNHUB_API_KEY is not set. Add it to .streamlit/secrets.toml or your environment."
        )
    params = {**params, "token": key}
    r = requests.get(f"{BASE_URL}{path}", params=params, timeout=15)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=900)
def earnings_calendar(from_date: str, to_date: str, symbol: str | None = None) -> list[dict]:
    params: dict = {"from": from_date, "to": to_date}
    if symbol:
        params["symbol"] = symbol
    data = _get("/calendar/earnings", params)
    return data.get("earningsCalendar", []) if isinstance(data, dict) else []


@st.cache_data(ttl=900)
def recommendation_trends(symbol: str) -> list[dict]:
    data = _get("/stock/recommendation", {"symbol": symbol})
    return data if isinstance(data, list) else []
