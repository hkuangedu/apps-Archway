import streamlit as st

st.set_page_config(page_title="Archway", page_icon="📈", layout="wide")

st.title("Archway")
st.subheader("Investment workflow tools for the student-managed fund")

st.markdown(
    """
Use the sidebar to open a tool:

- **Watchlist** — your sector team's tracked tickers
- **Event Calendar** — upcoming earnings for the selected sector
- **Rating Tracker** — current analyst recommendation distribution

This is a sandbox for the fund to explore using AI to build small tools that improve daily research workflow.
"""
)
