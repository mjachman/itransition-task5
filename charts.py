import numpy as np
import pandas as pd
import plotly.graph_objects as go


def fit_polynomial_trend(y_series: pd.Series, degree: int = 1) -> np.ndarray:
    x_idx = np.arange(len(y_series))
    coeffs = np.polyfit(x_idx, y_series.values, deg=degree)
    return np.polyval(coeffs, x_idx)


def make_bar_trace(sub: pd.DataFrame, mine: str) -> go.Bar:
    return go.Bar(x=sub["date"], y=sub["extraction"], name=mine)


def make_scatter_trace(sub: pd.DataFrame, mine: str, stacked: bool) -> go.Scatter:
    stack = "one" if stacked else None
    mode = "lines" if stacked else "lines+markers"
    return go.Scatter(
        x=sub["date"], y=sub["extraction"], name=mine, stackgroup=stack, mode=mode
    )


def add_series_trace(
    fig: go.Figure, df: pd.DataFrame, mine: str, geom: str, is_stacked: bool
) -> None:
    sub = df[df["mine"] == mine]
    trace = (
        make_bar_trace(sub, mine)
        if geom == "bar"
        else make_scatter_trace(sub, mine, is_stacked)
    )
    fig.add_trace(trace)


def format_outlier_text(outliers: pd.DataFrame) -> list[str]:
    return [
        f"{r['mine']}: {r['extraction']}t [{r.get('detected_by', 'Anomaly')}]"
        for _, r in outliers.iterrows()
    ]


def add_outlier_trace(fig: go.Figure, outliers: pd.DataFrame) -> None:
    if not outliers.empty:
        marker = {"color": "red", "size": 10, "symbol": "x"}
        fig.add_trace(
            go.Scatter(
                x=outliers["date"],
                y=outliers["extraction"],
                mode="markers",
                marker=marker,
                name="Anomaly",
                text=format_outlier_text(outliers),
            )
        )


def add_trendline_trace(fig: go.Figure, df: pd.DataFrame, degree: int) -> None:
    daily = df.groupby("date")["extraction"].sum().reset_index()
    trend = fit_polynomial_trend(daily["extraction"], degree)
    line = {"dash": "dash", "color": "#f59e0b", "width": 3}
    fig.add_trace(
        go.Scatter(
            x=daily["date"],
            y=trend,
            mode="lines",
            line=line,
            name=f"Trend (Deg {degree})",
        )
    )


def configure_chart_layout(fig: go.Figure, is_stacked: bool) -> go.Figure:
    bmode = "stack" if is_stacked else "group"
    fig.update_xaxes(
        type="date",
        tickformatstops=[{"dtickrange": [None, None], "value": "%b %d"}],
        tickangle=-30,
    )
    margin = {"l": 30, "r": 20, "t": 35, "b": 45}
    fig.update_layout(
        title="Daily Mineral Extraction & Anomalies",
        barmode=bmode,
        hovermode="x unified",
        height=360,
        margin=margin,
    )
    return fig


def populate_series_traces(
    fig: go.Figure, df: pd.DataFrame, geom: str, is_stacked: bool
) -> None:
    for m in df["mine"].unique():
        add_series_trace(fig, df, m, geom, is_stacked)


def should_draw_trendline(df: pd.DataFrame, is_stacked: bool) -> bool:
    return df["mine"].nunique() == 1 or is_stacked


def try_add_trendline(
    fig: go.Figure, df: pd.DataFrame, is_stacked: bool, degree: int
) -> None:
    if should_draw_trendline(df, is_stacked):
        add_trendline_trace(fig, df, degree)


def build_interactive_chart(
    df: pd.DataFrame,
    outliers: pd.DataFrame,
    geom: str = "line",
    is_stacked: bool = False,
    poly_deg: int = 1,
) -> go.Figure:
    fig = go.Figure()
    populate_series_traces(fig, df, geom, is_stacked)
    add_outlier_trace(fig, outliers)
    try_add_trendline(fig, df, is_stacked, poly_deg)
    return configure_chart_layout(fig, is_stacked)
