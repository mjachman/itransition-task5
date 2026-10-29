import io
import json
import pathlib
import tempfile

import pandas as pd
import typst
from report_chart import generate_chart_image_buffer


def format_date_range(d_min, d_max, n: int) -> tuple[str, str]:
    tl = f"{d_min.strftime('%d %b %Y')} – {d_max.strftime('%d %b %Y')} ({n} Days)"
    short_tl = f"{d_min.strftime('%b %Y')} – {d_max.strftime('%b %Y')}"
    return tl, short_tl


def format_param_tokens(p: dict) -> list[str]:
    t = [f"IQR (k={p['iqr_k']})"] if p.get("iqr_k") is not None else []
    if p.get("z_thresh") is not None:
        t.append(f"Z-Score (|z|>{p['z_thresh']})")
    return t


def format_param_tokens_adv(p: dict) -> list[str]:
    t = [f"CMA ({p['ma_w']}d, {p['ma_pct']:.0f}%)"] if p.get("ma_w") is not None else []
    if p.get("alpha") is not None:
        t.append(f"Grubbs (α={p['alpha']})")
    return t


def build_criteria_string(p: dict, deg: int) -> str:
    tokens = format_param_tokens(p) + format_param_tokens_adv(p)
    det = " · ".join(tokens) if tokens else "None Active"
    return f"{det} | Poly Deg {deg}"


def build_threshold_subtitle(p: dict) -> str:
    tokens = format_param_tokens(p) + format_param_tokens_adv(p)
    body = " · ".join(tokens) if tokens else "No active algorithmic filters selected."
    return f"Active detection thresholds: {body}"


def prepare_meta(raw: pd.DataFrame, deg: int, p: dict) -> dict:
    d_min, d_max, n = raw["date"].min(), raw["date"].max(), raw["date"].nunique()
    tl, short_tl = format_date_range(d_min, d_max, n)
    crit, sub = build_criteria_string(p, deg), build_threshold_subtitle(p)
    return {
        "timeline": tl,
        "short_timeline": short_tl,
        "criteria": crit,
        "threshold_sub": sub,
        "unit_upper": "METRIC TONS",
        "unit_lower": "metric tons",
    }


def format_stat_entry(r: pd.Series) -> dict:
    m, mn, s = r["mine"], float(r["mean"]), float(r["std"])
    md, iqr = float(r["median"]), float(r["iqr"])
    return {
        "mine": m,
        "mean": f"{mn:.2f}",
        "std": f"{s:.2f}",
        "median": f"{md:.2f}",
        "iqr": f"{iqr:.2f}",
        "is_total": (m == "Total Output"),
    }


def prepare_stats(stats: pd.DataFrame) -> list[dict]:
    return [format_stat_entry(r) for _, r in stats.iterrows()]


def compute_diff_pct(ext: float, base: float, spike: bool) -> str:
    diff = ext - base if spike else base - ext
    pct = (diff / base * 100) if base else 0.0
    sign = "+" if spike else "-"
    return f"{sign}{diff:.2f} ({sign}{pct:.1f}%)"


def format_anomaly_entry(r: pd.Series, base: float) -> dict:
    ext = float(r["extraction"])
    spike = ext >= base
    var_str = compute_diff_pct(ext, base, spike)
    return {
        "date": str(r["date"]),
        "mine": str(r["mine"]),
        "kind": "SPIKE" if spike else "DROP",
        "val": f"{ext:.2f}",
        "base": f"{base:.2f}",
        "variance": var_str,
        "detected_by": str(r.get("detected_by", "")),
    }


def extract_anomaly_list(all_out: pd.DataFrame, bases: dict[str, float]) -> list[dict]:
    return [
        format_anomaly_entry(r, bases.get(r["mine"], 30.0))
        for _, r in all_out.iterrows()
    ]


def filter_by_kind(anoms: list[dict], kind: str) -> list[dict]:
    return [a for a in anoms if a["kind"] == kind]


def add_anomaly_to_map(
    amap: dict[tuple[str, str], str], r: pd.Series, base: float
) -> None:
    k = "SPIKE" if float(r["extraction"]) >= base else "DROP"
    amap[(str(r["date"]), str(r["mine"]).upper())] = k
    if r["mine"] == "Total Output":
        amap[(str(r["date"]), "TOTAL OUTPUT")] = k


def build_anomaly_map(
    all_out: pd.DataFrame, bases: dict[str, float]
) -> dict[tuple[str, str], str]:
    amap: dict[tuple[str, str], str] = {}
    for _, r in all_out.iterrows():
        add_anomaly_to_map(amap, r, bases.get(r["mine"], 30.0))
    return amap


def format_ledger_cell_dict(
    val: float, d_str: str, col_name: str, amap: dict[tuple[str, str], str]
) -> dict:
    return {"text": f"{val:.2f}", "kind": amap.get((d_str, col_name), "NONE")}


def format_ledger_row_dict(
    r: pd.Series, cols: list[str], amap: dict[tuple[str, str], str]
) -> list[dict]:
    d_str = str(r["date"])
    cells = [{"text": d_str, "kind": "NONE"}]
    cells += [
        format_ledger_cell_dict(float(r[c]), d_str, c.upper(), amap)
        for c in cols
        if c != "date"
    ]
    return cells


def pivot_ledger_df(raw: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    piv = raw.pivot(index="date", columns="mine", values="extraction").round(2)
    piv["TOTAL OUTPUT"] = daily.set_index("date")["extraction"].round(2)
    return piv.reset_index()


def format_ledger_subtable_rows(
    sub_df: pd.DataFrame, cols: list[str], amap: dict[tuple[str, str], str]
) -> list[list[dict]]:
    return [format_ledger_row_dict(r, cols, amap) for _, r in sub_df.iterrows()]


def split_ledger_halves(df: pd.DataFrame, cols: list[str], amap: dict) -> tuple:
    half = (len(df) + 1) // 2
    l_rows = format_ledger_subtable_rows(df.iloc[:half], cols, amap)
    r_rows = format_ledger_subtable_rows(df.iloc[half:], cols, amap)
    return l_rows, r_rows


def assemble_ledger_dict(hdrs: list, left: list, right: list, full: list) -> dict:
    is_wide = len(hdrs) > 8
    return {
        "headers": hdrs,
        "num_cols": len(hdrs) - 1,
        "is_wide": is_wide,
        "left_rows": left,
        "right_rows": right,
        "full_rows": full,
    }


def prepare_ledger(
    raw: pd.DataFrame,
    daily: pd.DataFrame,
    all_out: pd.DataFrame,
    bases: dict[str, float],
) -> dict:
    df, amap = pivot_ledger_df(raw, daily), build_anomaly_map(all_out, bases)
    cols = list(df.columns)
    hdrs = ["DATE"] + [c.upper() for c in cols if c != "date"]
    left, right = split_ledger_halves(df, cols, amap)
    return assemble_ledger_dict(
        hdrs, left, right, format_ledger_subtable_rows(df, cols, amap)
    )


def assemble_payload(
    meta: dict, stats: list, spikes: list, drops: list, ledger: dict
) -> dict:
    return {
        "meta": meta,
        "stats": stats,
        "spikes": spikes,
        "drops": drops,
        "ledger": ledger,
    }


def build_json_payload(
    raw: pd.DataFrame,
    daily: pd.DataFrame,
    stats: pd.DataFrame,
    all_out: pd.DataFrame,
    deg: int,
    params: dict,
) -> dict:
    bases = dict(zip(stats["mine"], stats["mean"]))
    anoms = extract_anomaly_list(all_out, bases)
    spikes, drops = filter_by_kind(anoms, "SPIKE"), filter_by_kind(anoms, "DROP")
    led = prepare_ledger(raw, daily, all_out, bases)
    return assemble_payload(
        prepare_meta(raw, deg, params), prepare_stats(stats), spikes, drops, led
    )


def write_compiler_files(
    t_path: pathlib.Path, payload: dict, chart_buf: io.BytesIO
) -> None:
    tmpl = (
        pathlib.Path(__file__)
        .parent.joinpath("report_template.typ")
        .read_text(encoding="utf-8")
    )
    (t_path / "data.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    (t_path / "chart.png").write_bytes(chart_buf.getvalue())
    (t_path / "report_template.typ").write_text(tmpl, encoding="utf-8")


def execute_compilation(tmp_dir: str, payload: dict, chart_buf: io.BytesIO) -> bytes:
    write_compiler_files(pathlib.Path(tmp_dir), payload, chart_buf)
    return typst.compile(pathlib.Path(tmp_dir) / "report_template.typ")


def compile_from_template(payload: dict, chart_buf: io.BytesIO) -> bytes:
    with tempfile.TemporaryDirectory() as tmp_dir:
        return execute_compilation(tmp_dir, payload, chart_buf)


def generate_typst_report(
    raw: pd.DataFrame,
    daily: pd.DataFrame,
    stats: pd.DataFrame,
    m_out: pd.DataFrame,
    t_out: pd.DataFrame,
    params: dict,
    deg: int,
    geom: str = "line",
    is_stacked: bool = False,
) -> bytes:
    all_out = pd.concat([m_out, t_out], ignore_index=True)
    chart_buf = generate_chart_image_buffer(
        raw, daily, m_out, t_out, deg, geom, is_stacked
    )
    payload = build_json_payload(raw, daily, stats, all_out, deg, params)
    return compile_from_template(payload, chart_buf)
