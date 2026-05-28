import streamlit as st
from archway import watchlist

st.set_page_config(page_title="Watchlist | Archway", page_icon="📋", layout="wide")
st.title("Watchlist")
st.caption("Each sector team maintains its own tickers. Edit rows, add new ones, then click Save.")

df = watchlist.load()

edited = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "ticker": st.column_config.TextColumn("Ticker", required=True),
        "sector": st.column_config.TextColumn("Sector", required=True),
        "notes": st.column_config.TextColumn("Notes"),
    },
    key="watchlist_editor",
)

col1, col2 = st.columns([1, 5])
with col1:
    if st.button("Save", type="primary"):
        watchlist.save(edited)
        st.success(f"Saved {len(edited)} tickers.")
with col2:
    st.caption(
        "Saves to `data/watchlist.csv`. On Streamlit Cloud the filesystem is ephemeral — "
        "commit and push the CSV to share edits with the team."
    )
