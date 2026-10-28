import numpy as np
import pandas as pd
from scipy import stats as sp_stats


def detect_iqr_outliers(series: pd.Series, factor: float = 1.5) -> pd.Series:
    q25, q75 = series.quantile(0.25), series.quantile(0.75)
    iqr = q75 - q25
    low, high = q25 - factor * iqr, q75 + factor * iqr
    return (series < low) | (series > high)


def detect_zscore_outliers(series: pd.Series, threshold: float = 2.5) -> pd.Series:
    mean, std = series.mean(), series.std(ddof=1)
    if std == 0 or np.isnan(std):
        return pd.Series(False, index=series.index)
    z = (series - mean).abs() / std
    return z > threshold


def detect_ma_outliers(
    series: pd.Series, window: int = 7, pct_threshold: float = 40.0
) -> pd.Series:
    ma = series.rolling(window=window, min_periods=1, center=True).mean()
    diff_pct = ((series - ma).abs() / ma.replace(0, np.nan)) * 100.0
    return (diff_pct > pct_threshold).fillna(False)


def compute_grubbs_critical(n: int, alpha: float = 0.05) -> float:
    t_val = sp_stats.t.ppf(1.0 - alpha / (2.0 * n), n - 2)
    numerator = (n - 1) * np.sqrt(t_val**2)
    return float(numerator / np.sqrt(n * (n - 2 + t_val**2)))


def detect_grubbs_outliers(series: pd.Series, alpha: float = 0.05) -> pd.Series:
    n, std = len(series), series.std(ddof=1)
    if n < 3 or std == 0:
        return pd.Series(False, index=series.index)
    g_stat = (series - series.mean()).abs() / std
    return g_stat > compute_grubbs_critical(n, alpha)


def append_stat_masks(masks: dict, s: pd.Series, params: dict) -> None:
    if params.get("iqr_k") is not None:
        masks["IQR"] = detect_iqr_outliers(s, params["iqr_k"])
    if params.get("z_thresh") is not None:
        masks["Z-Score"] = detect_zscore_outliers(s, params["z_thresh"])


def append_adv_masks(masks: dict, s: pd.Series, params: dict) -> None:
    if params.get("ma_w") is not None:
        masks["Moving Avg"] = detect_ma_outliers(s, params["ma_w"], params["ma_pct"])
    if params.get("alpha") is not None:
        masks["Grubbs"] = detect_grubbs_outliers(s, params["alpha"])


def compute_test_masks(series: pd.Series, params: dict) -> dict[str, pd.Series]:
    masks: dict[str, pd.Series] = {}
    append_stat_masks(masks, series, params)
    append_adv_masks(masks, series, params)
    return masks


def format_detection_tags(flags_df: pd.DataFrame) -> list[str]:
    return [", ".join(flags_df.columns[row]) for row in flags_df.values]


def extract_flagged_rows(df: pd.DataFrame, masks: pd.DataFrame) -> pd.DataFrame:
    any_flag = masks.any(axis=1)
    res = df[any_flag].copy()
    res["detected_by"] = format_detection_tags(masks[any_flag])
    return res


def detect_multi_test_anomalies(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    raw_masks = compute_test_masks(df["extraction"], params)
    if not raw_masks:
        empty = df.iloc[0:0].copy()
        empty["detected_by"] = pd.Series(dtype=str)
        return empty
    return extract_flagged_rows(df, pd.DataFrame(raw_masks, index=df.index))


def detect_per_mine_anomalies(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    groups = [detect_multi_test_anomalies(g, params) for _, g in df.groupby("mine")]
    return (
        pd.concat(groups, ignore_index=True)
        if groups
        else pd.DataFrame(columns=df.columns)
    )


def compute_daily_totals(df: pd.DataFrame) -> pd.DataFrame:
    daily = df.groupby("date", as_index=False)["extraction"].sum()
    daily["mine"] = "Total Output"
    return daily


def detect_total_output_anomalies(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    daily = compute_daily_totals(df)
    return detect_multi_test_anomalies(daily, params)
