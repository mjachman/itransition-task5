import pandas as pd

SHEET_ID = "105EFki4awWcuEKCouSRobgXg-MvGx4xPOUaRTo05Shg"
VIEW_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"
DEFAULT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"


def normalize_url(url: str) -> str:
    if "/edit" in url:
        return url.split("/edit")[0] + "/gviz/tq?tqx=out:csv"
    return url


def load_raw_data(url: str = DEFAULT_URL) -> pd.DataFrame:
    try:
        target = normalize_url(url)
        return pd.read_csv(
            target, usecols=[0, 1, 2], names=["date", "mine", "extraction"]
        )
    except (OSError, ValueError):
        return pd.DataFrame(columns=["date", "mine", "extraction"])


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce").dt.date
    df["extraction"] = pd.to_numeric(df["extraction"], errors="coerce")
    df["mine"] = df["mine"].astype(str).str.strip().replace({"Total Output": "Total Output (Mine)"})
    return (
        df[df["extraction"].ge(0)]
        .dropna(subset=["date", "extraction"])
        .sort_values(["date", "mine"])
        .reset_index(drop=True)
    )


def fetch_production_data(url: str = DEFAULT_URL) -> pd.DataFrame:
    return clean_data(load_raw_data(url))
