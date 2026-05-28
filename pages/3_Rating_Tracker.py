import pandas as pd
import streamlit as st

from archway import watchlist
from archway.data import finnhub

st.set_page_config(page_title="Rating Tracker | Archway", page_icon="⭐", layout="wide")
st.title("Analyst Rating Tracker")
st.caption("Current sell-side recommendation distribution per ticker, from Finnhub.")

sectors = watchlist.sectors()
if not sectors:
    st.info("No sectors found. Add tickers on the Watchlist page first.")
    st.stop()

sector = st.selectbox("Sector", sectors)
tickers = watchlist.tickers_for(sector)

rows: list[dict] = []
errors: list[str] = []
with st.spinner("Fetching recommendations..."):
    for t in tickers:
        try:
            trends = finnhub.recommendation_trends(t)
            if not trends:
                continue
            latest = trends[0]
            rows.append({
                "Ticker": t,
                "Period": latest.get("period"),
                "Strong Buy": latest.get("strongBuy", 0),
                "Buy": latest.get("buy", 0),
                "Hold": latest.get("hold", 0),
                "Sell": latest.get("sell", 0),
                "Strong Sell": latest.get("strongSell", 0),
            })
        except Exception as e:
            errors.append(f"{t}: {e}")

if errors:
    with st.expander(f"{len(errors)} fetch error(s)"):
        for e in errors:
            st.text(e)

if not rows:
    st.info("No rating data available.")
    st.stop()

df = pd.DataFrame(rows)
df["Total"] = df[["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"]].sum(axis=1)
st.dataframe(df, use_container_width=True, hide_index=True)
