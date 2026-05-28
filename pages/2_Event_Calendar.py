import datetime as dt
import streamlit as st
from streamlit_calendar import calendar

from archway import watchlist
from archway.data import finnhub

st.set_page_config(page_title="Event Calendar | Archway", page_icon="📅", layout="wide")
st.title("Event Calendar")
st.caption("Upcoming earnings for tracked tickers, color-coded by sector.")

wl = watchlist.load()
all_sectors = sorted(s for s in wl["sector"].unique() if s)

if not all_sectors:
    st.info("No tickers in watchlist. Add some on the Watchlist page first.")
    st.stop()

PALETTE = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316"]
sector_colors = {s: PALETTE[i % len(PALETTE)] for i, s in enumerate(all_sectors)}

selected_sectors = st.multiselect("Sectors", all_sectors, default=all_sectors)

legend_html = " &nbsp;&nbsp; ".join(
    f"<span style='display:inline-block;width:12px;height:12px;background:{sector_colors[s]};"
    f"border-radius:3px;margin-right:6px;vertical-align:middle;'></span>{s}"
    for s in selected_sectors
)
if legend_html:
    st.markdown(legend_html, unsafe_allow_html=True)

filtered = wl[wl["sector"].isin(selected_sectors)]
tickers = filtered["ticker"].tolist()
ticker_to_sector = dict(zip(filtered["ticker"], filtered["sector"]))

today = dt.date.today()
from_date = (today - dt.timedelta(days=14)).isoformat()
to_date = (today + dt.timedelta(days=180)).isoformat()

events: list[dict] = []
errors: list[str] = []
with st.spinner("Loading events..."):
    for t in tickers:
        try:
            for row in finnhub.earnings_calendar(from_date, to_date, symbol=t):
                date = row.get("date")
                if not date:
                    continue
                hour = (row.get("hour") or "").lower()
                hour_label = {"bmo": "BMO", "amc": "AMC", "dmh": "MID"}.get(hour, "")
                title = f"{t} {hour_label}".strip()
                sector = ticker_to_sector.get(t, "")
                color = sector_colors.get(sector, "#6b7280")
                events.append({
                    "title": title,
                    "start": date,
                    "end": date,
                    "allDay": True,
                    "backgroundColor": color,
                    "borderColor": color,
                    "textColor": "#ffffff",
                    "extendedProps": {
                        "ticker": t,
                        "sector": sector,
                        "hour": hour,
                        "epsEstimate": row.get("epsEstimate"),
                        "revenueEstimate": row.get("revenueEstimate"),
                        "quarter": row.get("quarter"),
                        "year": row.get("year"),
                    },
                })
        except Exception as e:
            errors.append(f"{t}: {e}")

if errors:
    with st.expander(f"{len(errors)} fetch error(s)"):
        for e in errors:
            st.text(e)

calendar_options = {
    "headerToolbar": {
        "left": "today prev,next",
        "center": "title",
        "right": "dayGridMonth,timeGridWeek,listMonth",
    },
    "initialView": "dayGridMonth",
    "navLinks": True,
    "weekends": True,
    "height": 720,
    "dayMaxEvents": True,
}

custom_css = """
    .fc-event { font-weight: 600; padding: 2px 4px; }
    .fc-toolbar-title { font-size: 1.2rem; }
"""

result = calendar(
    events=events,
    options=calendar_options,
    custom_css=custom_css,
    key="earnings_cal",
)

clicked = (result or {}).get("eventClick")
if clicked:
    ev = clicked.get("event", {})
    props = ev.get("extendedProps", {})
    st.markdown("---")
    date_str = (ev.get("start") or "")[:10]
    st.subheader(f"{props.get('ticker', '')} — {date_str}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Sector", props.get("sector") or "—")
    c2.metric(
        "Timing",
        {"bmo": "Before market open", "amc": "After market close", "dmh": "During market hours"}
        .get(props.get("hour"), "Unspecified"),
    )
    q = props.get("quarter")
    y = props.get("year")
    c3.metric("Period", f"Q{q} {y}" if q and y else "—")
    c4, c5 = st.columns(2)
    eps = props.get("epsEstimate")
    rev = props.get("revenueEstimate")
    c4.metric("EPS estimate", f"{eps:.2f}" if isinstance(eps, (int, float)) else "—")
    c5.metric(
        "Revenue estimate",
        f"${rev/1e6:,.1f}M" if isinstance(rev, (int, float)) else "—",
    )
else:
    st.caption("Click any event for details.")
