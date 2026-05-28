# Archway

Lightweight investment workflow tools for our school's student-managed fund. Built as a sandbox for students to explore using AI to improve research and monitoring workflows.

## Tools

- **Watchlist** — each sector team manages the tickers they cover
- **Event Calendar** — upcoming earnings and corporate events for the selected sector
- **Rating Tracker** — current sell-side analyst recommendation distribution

## Setup

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit secrets.toml and paste your Finnhub API key
streamlit run app.py
```

Get a free Finnhub API key at https://finnhub.io/register.

## Deploying

Works on Streamlit Community Cloud. Add `FINNHUB_API_KEY` under app settings → Secrets.

Note: on Streamlit Cloud the filesystem is read-only between deploys, so watchlist edits made in the hosted UI won't persist. For shared edits, run locally, commit `data/watchlist.csv`, and push.

## Project layout

```
app.py                  Streamlit entry
pages/                  one file per tool (auto-loaded as sidebar pages)
archway/                shared helpers
  data/                 data adapters (Finnhub, future vendors)
  watchlist.py          load/save the sector watchlist
data/watchlist.csv      source of truth for tracked tickers
```
