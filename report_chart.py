import io

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from charts import fit_polynomial_trend


def plot_series_line(ax, df: pd.DataFrame) -> None:
    for m in df["mine"].unique():
        sub = df[df["mine"] == m]
        ax.plot(sub["date"], sub["extraction"], label=m, linewidth=1.2)


def plot_series_stacked_area(ax, df: pd.DataFrame) -> None:
    piv = df.pivot(index="date", columns="mine", values="extraction").fillna(0)
    ax.stackplot(
        piv.index, [piv[c] for c in piv.columns], labels=piv.columns, alpha=0.85
    )


def plot_series_stacked_bar(ax, df: pd.DataFrame) -> None:
    piv = df.pivot(index="date", columns="mine", values="extraction").fillna(0)
    bottom = np.zeros(len(piv))
    for col in piv.columns:
        ax.bar(piv.index, piv[col], bottom=bottom, label=col, width=0.8)
        bottom += piv[col].values


def plot_series_grouped_bar(ax, df: pd.DataFrame) -> None:
    piv = df.pivot(index="date", columns="mine", values="extraction").fillna(0)
    x_nums, w = mdates.date2num(pd.to_datetime(piv.index)), 0.25
    for i, col in enumerate(piv.columns):
        ax.bar(x_nums + (i - 1) * w, piv[col], width=w, label=col)


def plot_mine_bar(ax, df: pd.DataFrame, is_stacked: bool) -> None:
    if is_stacked:
        plot_series_stacked_bar(ax, df)
    else:
        plot_series_grouped_bar(ax, df)


def plot_mine_data(ax, df: pd.DataFrame, geom: str, is_stacked: bool) -> None:
    if geom == "bar":
        plot_mine_bar(ax, df, is_stacked)
    elif is_stacked:
        plot_series_stacked_area(ax, df)
    else:
        plot_series_line(ax, df)


def plot_anomalies_overlay(ax, anomalies: pd.DataFrame) -> None:
    if not anomalies.empty:
        ax.scatter(
            anomalies["date"],
            anomalies["extraction"],
            color="red",
            s=25,
            zorder=5,
            marker="x",
        )


def plot_trendline(ax, daily: pd.DataFrame, deg: int) -> None:
    trend = fit_polynomial_trend(daily["extraction"], deg)
    ax.plot(
        daily["date"],
        trend,
        color="#f59e0b",
        linestyle="--",
        linewidth=1.4,
        label=f"Trend (Deg {deg})",
    )


def plot_mine_dispatch(
    ax,
    df: pd.DataFrame,
    daily: pd.DataFrame,
    anomalies: pd.DataFrame,
    deg: int,
    geom: str,
    is_stacked: bool,
) -> None:
    plot_mine_data(ax, df, geom, is_stacked)
    if is_stacked:
        plot_trendline(ax, daily, deg)
    plot_anomalies_overlay(ax, anomalies)


def plot_total_bar(ax, daily: pd.DataFrame) -> None:
    ax.bar(
        daily["date"],
        daily["extraction"],
        color="#0284c7",
        alpha=0.7,
        label="Total Output",
        width=0.8,
    )


def plot_total_stacked(ax, daily: pd.DataFrame) -> None:
    ax.fill_between(
        daily["date"],
        daily["extraction"],
        color="#0284c7",
        alpha=0.35,
        label="Total Output",
    )
    ax.plot(daily["date"], daily["extraction"], color="#0284c7", linewidth=1.2)


def plot_total_line(ax, daily: pd.DataFrame) -> None:
    ax.plot(
        daily["date"],
        daily["extraction"],
        color="#0284c7",
        linewidth=1.4,
        label="Total Output",
    )


def plot_total_data(ax, daily: pd.DataFrame, geom: str, is_stacked: bool) -> None:
    if geom == "bar":
        plot_total_bar(ax, daily)
    elif is_stacked:
        plot_total_stacked(ax, daily)
    else:
        plot_total_line(ax, daily)


def plot_total_dispatch(
    ax,
    daily: pd.DataFrame,
    anomalies: pd.DataFrame,
    deg: int,
    geom: str,
    is_stacked: bool,
) -> None:
    plot_total_data(ax, daily, geom, is_stacked)
    plot_trendline(ax, daily, deg)
    plot_anomalies_overlay(ax, anomalies)


def setup_subplot_axis(ax, title: str) -> None:
    ax.set_title(title, fontsize=7, fontweight="bold", pad=2)
    ax.legend(loc="upper left", fontsize=5.5, frameon=True)
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d, %Y"))
    ax.tick_params(labelsize=5.5, rotation=15)


def get_chart_mode_label(geom: str, is_stacked: bool) -> str:
    layout = "STACKED" if is_stacked else ("GROUPED" if geom == "bar" else "STANDARD")
    return f"{geom.upper()} // {layout}"


def draw_mine_subplot(
    ax,
    raw: pd.DataFrame,
    daily: pd.DataFrame,
    m_out: pd.DataFrame,
    deg: int,
    geom: str,
    is_stacked: bool,
) -> None:
    plot_mine_dispatch(ax, raw, daily, m_out, deg, geom, is_stacked)
    lbl = get_chart_mode_label(geom, is_stacked)
    setup_subplot_axis(ax, f"PER MINE EXTRACTION & ANOMALIES ({lbl})")


def draw_total_subplot(
    ax,
    daily: pd.DataFrame,
    t_out: pd.DataFrame,
    deg: int,
    geom: str,
    is_stacked: bool,
) -> None:
    plot_total_dispatch(ax, daily, t_out, deg, geom, is_stacked)
    lbl = get_chart_mode_label(geom, is_stacked)
    setup_subplot_axis(ax, f"TOTAL AGGREGATED EXTRACTION & TRENDLINE ({lbl})")


def draw_dual_charts(
    fig,
    raw: pd.DataFrame,
    daily: pd.DataFrame,
    m_out: pd.DataFrame,
    t_out: pd.DataFrame,
    deg: int,
    geom: str = "line",
    is_stacked: bool = False,
) -> None:
    ax1, ax2 = fig.subplots(2, 1, sharex=True)
    draw_mine_subplot(ax1, raw, daily, m_out, deg, geom, is_stacked)
    draw_total_subplot(ax2, daily, t_out, deg, geom, is_stacked)


def create_chart_bytes(fig) -> io.BytesIO:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    buf.seek(0)
    return buf


def generate_chart_image_buffer(
    raw: pd.DataFrame,
    daily: pd.DataFrame,
    m_out: pd.DataFrame,
    t_out: pd.DataFrame,
    deg: int,
    geom: str = "line",
    is_stacked: bool = False,
) -> io.BytesIO:
    fig = plt.figure(figsize=(6.8, 6.6))
    draw_dual_charts(fig, raw, daily, m_out, t_out, deg, geom, is_stacked)
    fig.tight_layout()
    buf = create_chart_bytes(fig)
    return plt.close(fig) or buf
