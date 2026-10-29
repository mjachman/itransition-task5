import pandas as pd
import streamlit as st
from anomalies import (
    compute_daily_totals,
    detect_per_mine_anomalies,
    detect_total_output_anomalies,
)
from charts import build_interactive_chart
from data_loader import DEFAULT_URL, VIEW_URL, fetch_production_data
from stats import build_full_stats_summary, calculate_total_stats
from typst_report import generate_typst_report


def get_custom_css() -> str:
    return """
    <style>
    .block-container {
        padding-top: 3.5rem !important;
        padding-bottom: 2rem !important;
    }
    [data-testid="stSidebarContent"] {
        padding-top: 2.2rem !important;
    }
    h1 {
        margin-top: 0.2rem !important;
        padding-top: 0 !important;
        line-height: 1.25 !important;
    }
    [data-testid="stSidebar"] [data-testid="stLinkButton"] a,
    [data-testid="stSidebar"] a[href*="docs.google.com"] {
        background-color: #0f9d58 !important;
        color: #ffffff !important;
        border: 1px solid #0b8043 !important;
        font-weight: 600 !important;
    }
    [data-testid="stSidebar"] [data-testid="stLinkButton"] a:hover,
    [data-testid="stSidebar"] a[href*="docs.google.com"]:hover {
        background-color: #0b8043 !important;
        border-color: #086334 !important;
    }
    [data-testid="stSidebar"] [data-testid="stLinkButton"] a *,
    [data-testid="stSidebar"] a[href*="docs.google.com"] * {
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    </style>
    """


def setup_page() -> None:
    st.set_page_config(page_title="Weyland-Yutani Mining Ops", layout="wide")
    st.markdown(get_custom_css(), unsafe_allow_html=True)


def render_chart_controls() -> tuple[str, bool, int]:
    st.sidebar.header("CHART TYPE")
    geom = st.sidebar.radio(
        "Chart Type",
        ["line", "bar"],
        index=0,
        format_func=str.capitalize,
        label_visibility="collapsed",
    )
    is_stacked = st.sidebar.toggle("Stack Series", value=False)
    deg = st.sidebar.slider(
        "Polynomial Trendline Degree", min_value=1, max_value=4, value=1
    )
    return geom, is_stacked, deg


def render_iqr_block() -> float | None:
    if st.sidebar.toggle("IQR Rule", value=True):
        return st.sidebar.slider("IQR Multiplier (k)", 1.0, 3.0, 1.5, 0.1)
    return None


def render_zscore_block() -> float | None:
    if st.sidebar.toggle("Z-Score", value=False):
        return st.sidebar.slider("Z-Score Sensitivity Threshold", 1.5, 4.0, 2.5, 0.1)
    return None


def render_ma_block() -> tuple[int, float] | None:
    if not st.sidebar.toggle("Moving Average", value=False):
        return None
    w = st.sidebar.slider("Moving Average Window (days)", 3, 14, 7)
    return w, st.sidebar.slider("Deviation Threshold (%)", 10.0, 100.0, 40.0, 5.0)


def render_grubbs_block() -> float | None:
    if st.sidebar.toggle("Grubbs' Test", value=False):
        return st.sidebar.slider("Grubbs Significance Alpha", 0.01, 0.10, 0.05, 0.01)
    return None


def pack_anomaly_params(
    k: float | None, z: float | None, ma: tuple | None, g: float | None
) -> dict:
    w = ma[0] if ma else None
    pct = ma[1] if ma else None
    return {"iqr_k": k, "z_thresh": z, "ma_w": w, "ma_pct": pct, "alpha": g}


def render_sidebar_anomaly() -> dict:
    st.sidebar.header("DETECTION ALGORITHMS")
    k, z = render_iqr_block(), render_zscore_block()
    ma, g = render_ma_block(), render_grubbs_block()
    return pack_anomaly_params(k, z, ma, g)


def render_metric_quad(container, row: pd.Series) -> None:
    c1, c2 = container.columns(2)
    c1.metric("Mean Daily Output", f"{row['mean']} t")
    c2.metric("Standard Deviation", f"{row['std']} t")
    c1.metric("Median Extraction", f"{row['median']} t")
    c2.metric("IQR Range", f"{row['iqr']} t")


def get_stats_column_config() -> dict:
    return {
        "mean": st.column_config.NumberColumn(
            "Mean", format="%.2f", alignment="center"
        ),
        "std": st.column_config.NumberColumn(
            "Std Dev", format="%.2f", alignment="center"
        ),
        "median": st.column_config.NumberColumn(
            "Median", format="%.2f", alignment="center"
        ),
        "iqr": st.column_config.NumberColumn(
            "IQR", format="%.2f", alignment="center"
        ),
        "is_total": None,
    }


def style_stats_row(row: pd.Series) -> list[str]:
    is_total = bool(row.get("is_total", False))
    bg = (
        "background-color: rgba(2, 132, 199, 0.22); font-weight: bold;"
        if is_total
        else ""
    )
    return [bg] * len(row)


def render_stats_content(box, stats_df: pd.DataFrame) -> None:
    if len(stats_df) == 1:
        render_metric_quad(box, stats_df.iloc[0])
    else:
        cfg = get_stats_column_config()
        df = stats_df.set_index("mine").rename_axis("Mine")
        styled = df.style.apply(style_stats_row, axis=1)
        box.dataframe(styled, column_config=cfg, use_container_width=True)


def render_stats_column(col, stats_df: pd.DataFrame) -> None:
    box = col.container(border=True)
    box.subheader("STATISTICAL SUMMARY")
    render_stats_content(box, stats_df)


def classify_type(row: pd.Series, base: float) -> str:
    return "SPIKE" if row["extraction"] >= base else "DROP"


def enrich_anomaly_row(row: pd.Series, bases: dict) -> dict:
    base = bases.get(row["mine"], row["extraction"])
    return {
        "DATE": row["date"],
        "MINE": row["mine"],
        "TYPE": classify_type(row, base),
        "RECORDED": f"{row['extraction']:.2f}",
        "FLAGGED BY": row.get("detected_by", ""),
    }


def format_anomalies_table(
    outliers: pd.DataFrame, stats_df: pd.DataFrame
) -> pd.DataFrame:
    bases = dict(zip(stats_df["mine"], stats_df["mean"]))
    rows = [enrich_anomaly_row(r, bases) for _, r in outliers.iterrows()]
    cols = ["DATE", "MINE", "TYPE", "RECORDED", "FLAGGED BY"]
    return pd.DataFrame(rows, columns=cols)


def style_anomaly_row(row: pd.Series) -> list[str]:
    is_spike = row["TYPE"] == "SPIKE"
    bg = (
        "background-color: rgba(239, 68, 68, 0.20);"
        if is_spike
        else "background-color: rgba(59, 130, 246, 0.20);"
    )
    return [bg] * len(row)


def render_anomaly_content(box, outliers: pd.DataFrame, stats_df: pd.DataFrame) -> None:
    if outliers.empty:
        box.info("Zero anomalies detected under active criteria.")
    else:
        df = format_anomalies_table(outliers, stats_df)
        styled = df.style.apply(style_anomaly_row, axis=1)
        box.dataframe(styled, use_container_width=True, hide_index=True)


def render_anomaly_tabs(
    box,
    m_out: pd.DataFrame,
    t_out: pd.DataFrame,
    m_stats: pd.DataFrame,
    t_stats: pd.DataFrame,
) -> None:
    t1, t2 = box.tabs(
        [f"MINE ANOMALIES ({len(m_out)})", f"GLOBAL ANOMALIES ({len(t_out)})"]
    )
    render_anomaly_content(t1, m_out, m_stats)
    render_anomaly_content(t2, t_out, t_stats)


def render_anomaly_section(
    col,
    m_out: pd.DataFrame,
    t_out: pd.DataFrame,
    m_stats: pd.DataFrame,
    t_stats: pd.DataFrame,
) -> None:
    box = col.container(border=True)
    box.subheader("DETECTED ANOMALIES")
    render_anomaly_tabs(box, m_out, t_out, m_stats, t_stats)


def create_audit_pdf(
    m_pack: tuple,
    t_pack: tuple,
    stats: pd.DataFrame,
    params: dict,
    deg: int,
    geom: str,
    is_stacked: bool,
) -> bytes:
    return generate_typst_report(
        m_pack[0], t_pack[0], stats, m_pack[2], t_pack[2], params, deg, geom, is_stacked
    )


def render_download_button(box, pdf_bytes: bytes) -> None:
    box.download_button(
        "**Download Report (PDF)**",
        data=pdf_bytes,
        file_name="weyland_yutani_production_report.pdf",
        mime="application/pdf",
        type="primary",
        use_container_width=True,
    )


def render_sidebar_actions(
    box, m_pack: tuple, t_pack: tuple, params: dict, deg: int, geom: str, is_stk: bool
) -> None:
    pdf = create_audit_pdf(m_pack, t_pack, m_pack[1], params, deg, geom, is_stk)
    box.link_button("Open Generator Spreadsheet", VIEW_URL, use_container_width=True)
    render_download_button(box, pdf)
    box.divider()


def format_chips_markup(df: pd.DataFrame) -> str:
    d_min, d_max, n = df["date"].min(), df["date"].max(), df["date"].nunique()
    return f'<div style="font-size:18px;color:#94a3b8;margin-top:4px;margin-bottom:8px;"><strong style="color:#f8fafc;">{d_min} &ndash; {d_max}</strong> &nbsp;&bull;&nbsp; <strong style="color:#f8fafc;">{n} Days</strong> &nbsp;&bull;&nbsp; <span style="color:#cbd5e1;">Units: Metric Tons [t]</span></div>'


def render_header(df: pd.DataFrame) -> None:
    st.title("Weyland-Yutani Corporation - Mine Extraction Analysis")
    st.markdown(format_chips_markup(df), unsafe_allow_html=True)


def draw_single_chart(
    container,
    df: pd.DataFrame,
    out: pd.DataFrame,
    geom: str,
    is_stk: bool,
    deg: int,
) -> None:
    fig = build_interactive_chart(df, out, geom, is_stk, deg)
    container.plotly_chart(fig, use_container_width=True)


def render_chart_section(
    m_pack: tuple, t_pack: tuple, geom: str, is_stacked: bool, deg: int
) -> None:
    box = st.container(border=True)
    t1, t2 = box.tabs(["PER MINE", "TOTAL OUTPUT"])
    draw_single_chart(t1, m_pack[0], m_pack[2], geom, is_stacked, deg)
    draw_single_chart(t2, t_pack[0], t_pack[2], geom, False, deg)


def render_lower_sections(m_pack: tuple, t_pack: tuple) -> None:
    c1, c2 = st.columns([1, 1])
    render_stats_column(c1, m_pack[1])
    render_anomaly_section(c2, m_pack[2], t_pack[2], m_pack[1], t_pack[1])


def render_dashboard_content(
    m_pack: tuple,
    t_pack: tuple,
    geom: str,
    is_stacked: bool,
    deg: int,
) -> None:
    render_header(m_pack[0])
    render_chart_section(m_pack, t_pack, geom, is_stacked, deg)
    render_lower_sections(m_pack, t_pack)


def compute_all_metrics(
    raw_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    daily = compute_daily_totals(raw_df)
    m_stats = build_full_stats_summary(raw_df)
    t_stats = pd.DataFrame([{"mine": "Total Output", **calculate_total_stats(raw_df)}])
    return daily, m_stats, t_stats


def check_data_availability(raw: pd.DataFrame) -> None:
    if raw.empty:
        st.error("Extraction data unavailable. Please verify spreadsheet accessibility.")
        st.stop()


def load_analyzed_data(url: str, params: dict) -> tuple[tuple, tuple]:
    raw = fetch_production_data(url)
    check_data_availability(raw)
    daily, m_stats, t_stats = compute_all_metrics(raw)
    m_out = detect_per_mine_anomalies(raw, params)
    return (raw, m_stats, m_out), (
        daily,
        t_stats,
        detect_total_output_anomalies(raw, params),
    )


def get_sidebar_settings() -> tuple[str, bool, int, dict]:
    geom, is_stacked, deg = render_chart_controls()
    params = render_sidebar_anomaly()
    return geom, is_stacked, deg, params


def run_app_pipeline(
    sb_top, geom: str, is_stk: bool, deg: int, params: dict
) -> None:
    m_pack, t_pack = load_analyzed_data(DEFAULT_URL, params)
    render_sidebar_actions(sb_top, m_pack, t_pack, params, deg, geom, is_stk)
    render_dashboard_content(m_pack, t_pack, geom, is_stk, deg)


def main() -> None:
    setup_page()
    sb_top = st.sidebar.container()
    geom, is_stk, deg, params = get_sidebar_settings()
    run_app_pipeline(sb_top, geom, is_stk, deg, params)


if __name__ == "__main__":
    main()
