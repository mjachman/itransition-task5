import pandas as pd


def compute_metrics(series: pd.Series) -> dict[str, float]:
    q25, q75 = series.quantile(0.25), series.quantile(0.75)
    mean, std = round(series.mean(), 2), round(series.std(ddof=1), 2)
    med, iqr = round(series.median(), 2), round(q75 - q25, 2)
    return {"mean": mean, "std": std, "median": med, "iqr": iqr}


def calculate_mine_stats(df: pd.DataFrame) -> pd.DataFrame:
    items = [
        {"mine": m, **compute_metrics(g["extraction"]), "is_total": False}
        for m, g in df.groupby("mine")
    ]
    return pd.DataFrame(items)


def calculate_total_stats(df: pd.DataFrame) -> dict[str, float]:
    daily_totals = df.groupby("date")["extraction"].sum()
    return compute_metrics(daily_totals)


def build_full_stats_summary(df: pd.DataFrame) -> pd.DataFrame:
    m_df = calculate_mine_stats(df)
    tot = {"mine": "Total Output", **calculate_total_stats(df), "is_total": True}
    return pd.concat([m_df, pd.DataFrame([tot])], ignore_index=True)
