from pathlib import Path
import pandas as pd

WATCHLIST_PATH = Path(__file__).resolve().parent.parent / "data" / "watchlist.csv"


def load() -> pd.DataFrame:
    df = pd.read_csv(WATCHLIST_PATH).fillna("")
    df["ticker"] = df["ticker"].str.upper().str.strip()
    df["sector"] = df["sector"].str.strip()
    return df


def save(df: pd.DataFrame) -> None:
    df = df.copy()
    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    df["sector"] = df["sector"].astype(str).str.strip()
    df = df[df["ticker"] != ""]
    df.to_csv(WATCHLIST_PATH, index=False)


def sectors() -> list[str]:
    return sorted(s for s in load()["sector"].unique() if s)


def tickers_for(sector: str) -> list[str]:
    df = load()
    return df.loc[df["sector"] == sector, "ticker"].tolist()
