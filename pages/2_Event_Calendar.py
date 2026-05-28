import datetime as dt
import pandas as pd
import streamlit as st

from archway import watchlist
from archway.data import finnhub

st.set_page_config(page_title="Event Calendar | Archway", page_icon="📅", layout="wide")
st.title("Event Calendar")
st.caption("Upcoming earnings for tickers on the selected sector watchlist.")

sectors = watchlist.sectors()
if not sectors:
    st.info("No sectors found. Add tickers on the Watchlist page first.")
    st.stop()

col1, col2 = st.columns([2, 3])
sector = col1.selectbox("Sector", sectors)
days = col2.slider("Window (days ahead)", 7, 180, 90)

tickers = watchlist.tickers_for(sector)
st.write(f"Tracking **{len(tickers)}** tickers in **{sector}**: {', '.join(tickers)}")

from_date = dt.date.today().isoformat()
to_date = (dt.date.today() + dt.timedelta(days=days)).isoformat()

rows: list[dict] = []
errors: list[str] = []
with st.spinner("Fetching earnings calendar..."):
    for t in tickers:
        try:
            rows.extend(finnhub.earnings_calendar(from_date, to_date, symbol=t))
        except Exception as e:
            errors.append(f"{t}: {e}")

if errors:
    with st.expander(f"{len(errors)} fetch error(s)"):
        for e in errors:
            st.text(e)

if not rows:
    st.info("No upcoming earnings in this window.")
    st.stop()

df = pd.DataFrame(rows)
cols = [c for c in ["date", "hour", "symbol", "epsEstimate", "epsActual", "revenueEstimate", "revenueActual", "quarter", "year"] if c in df.columns]
df = df[cols].sort_values("date").reset_index(drop=True)
st.dataframe(df, use_container_width=True, hide_index=True)
