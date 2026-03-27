import streamlit as st
import pandas as pd

from core.data_loader import load_data, detect_pid_columns
from core.charts import (
    bar_chart, line_chart, scatter_chart, histogram,
    agg_bar_data, pareto_chart, agg_pareto_data,
)
from core.export_render import chart_to_png_bytes, chart_to_svg_bytes
from core.watermark import add_png_watermark
from core.recommend import profile_columns, recommend_charts
from core.themes import get_style, MIDAS, STYLES
from exports.excel_export import df_to_formatted_xlsx_bytes
from exports.pdf_export import df_to_pdf_bytes
from payments.entitlement import is_export_entitled

st.set_page_config(
    page_title="Atlas",
    layout="wide",
    initial_sidebar_state="expanded",
)

with open("assets/style.css", encoding="utf-8") as _f:
    st.markdown(f"<style>{_f.read()}</style>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────
st.session_state.setdefault("df", None)
st.session_state.setdefault("chart_type_ui", "Pareto")
st.session_state.setdefault("x_col", None)
st.session_state.setdefault("y_col", None)
st.session_state.setdefault("assign_target", "X")
st.session_state.setdefault("export_entitled", False)
st.session_state.setdefault("top_n", 20)
st.session_state.setdefault("sort_desc", True)
st.session_state.setdefault("as_rate", False)
st.session_state.setdefault("show_labels", True)
st.session_state.setdefault("bar_flip", False)
st.session_state.setdefault("style_name", "cicero")
st.session_state.setdefault("user_uploaded", False)
st.session_state.setdefault("chart_title_override", "")
st.session_state.setdefault("last_chart_png_watermarked", None)
st.session_state.setdefault("last_chart_type", None)
st.session_state.setdefault("last_chart_obj", None)
st.session_state.setdefault("chart_type_effective", None)
st.session_state.setdefault("auto_info", None)
st.session_state.setdefault("auto_suggestions", [])
st.session_state.setdefault("pid_columns", [])
st.session_state.setdefault("_last_rendered_x", None)
st.session_state.setdefault("_last_rendered_y", None)

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def reset_state_for_new_df():
    st.session_state["x_col"] = None
    st.session_state["y_col"] = None
    st.session_state["chart_type_effective"] = None
    st.session_state["auto_info"] = None
    st.session_state["auto_suggestions"] = []
    st.session_state["pid_columns"] = []

@st.cache_data(show_spinner=False)
def cached_profiles(df: pd.DataFrame):
    return profile_columns(df)

def highlight_used_columns(df: pd.DataFrame, used_cols: list[str]):
    used = {c for c in used_cols if c}
    def _highlight(col: pd.Series):
        return [
            "background-color: rgba(28,167,166,0.12)" if col.name in used else ""
            for _ in col
        ]
    return df.head(20).style.apply(_highlight, axis=0)

_CHART_LABEL_MAP = {
    "bar": "Bar", "line": "Line", "scatter": "Scatter",
    "histogram": "Histogram", "pareto": "Pareto",
}

def set_default_xy_from_auto(df: pd.DataFrame):
    profiles = cached_profiles(df)
    suggestions = recommend_charts(df, profiles, user_x=None, user_y=None)
    best = suggestions[0]
    st.session_state["chart_type_effective"] = _CHART_LABEL_MAP.get(best.chart_type, "Bar")
    if st.session_state["x_col"] is None and best.spec.get("x") in df.columns:
        st.session_state["x_col"] = best.spec["x"]
    if st.session_state["y_col"] is None and best.spec.get("y") in df.columns:
        st.session_state["y_col"] = best.spec["y"]
    st.session_state["auto_info"] = best
    st.session_state["auto_suggestions"] = suggestions

def pick_fallback_xy(df: pd.DataFrame):
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = [c for c in df.columns if c not in numeric_cols]
    if not numeric_cols:
        return None, None
    return (cat_cols[0] if cat_cols else df.columns[0]), numeric_cols[0]

def build_chart(
    df, chart_type, x_col, y_col,
    top_n=20, show_labels=True, sort_desc=True, as_rate=False,
    orient="h", style=MIDAS, chart_title: str = "",
):
    if chart_type == "Bar":
        return bar_chart(df, x_col, y_col, top_n=top_n, show_labels=show_labels,
                         sort_desc=sort_desc, as_rate=as_rate, orient=orient,
                         style=style, chart_title=chart_title)
    if chart_type == "Line":
        return line_chart(df, x_col, y_col, style=style, chart_title=chart_title)
    if chart_type == "Scatter":
        return scatter_chart(df, x_col, y_col, style=style, chart_title=chart_title)
    if chart_type == "Histogram":
        return histogram(df, x_col, bins=30, style=style, chart_title=chart_title)
    if chart_type == "Pareto":
        return pareto_chart(df, x_col, y_col, top_n=top_n, style=style, chart_title=chart_title)
    return bar_chart(df, x_col, y_col, top_n=top_n, show_labels=show_labels,
                     sort_desc=sort_desc, as_rate=as_rate, style=style, chart_title=chart_title)

# ─────────────────────────────────────────────────────────────
# Auto-load demo dataset on first visit (or after reset)
# ─────────────────────────────────────────────────────────────
if st.session_state["df"] is None:
    _demo_df = load_data("demo_data/uk_gov_spending_2024_25.csv")
    st.session_state["df"] = _demo_df
    st.session_state["pid_columns"] = []
    st.session_state["x_col"] = "Department"
    st.session_state["y_col"] = "Spending_GBP_Billions"
    st.session_state["chart_type_ui"] = "Pareto"
    st.session_state["style_name"] = "cicero"
    st.session_state["chart_title_override"] = "UK Government Spending 2024/25 (£bn)"

# ─────────────────────────────────────────────────────────────
# SIDEBAR — Navy panel
# ─────────────────────────────────────────────────────────────
with st.sidebar:

    # ── Wordmark ─────────────────────────────────────────────
    st.markdown('<p class="atlas-wordmark">ATLAS</p>', unsafe_allow_html=True)

    st.markdown("---")

    # ── Data source ──────────────────────────────────────────
    st.markdown('<span class="sidebar-label">Data</span>', unsafe_allow_html=True)

    if st.session_state.get("user_uploaded", False):
        _df_sidebar = st.session_state["df"]
        _r, _c = _df_sidebar.shape
        st.caption(f"{_r:,} rows · {_c} columns")

        uploaded = st.file_uploader(
            "Try with your own data",
            type=["csv", "tsv", "xlsx"],
            key="uploader_main",
            label_visibility="collapsed",
        )
        if uploaded:
            try:
                _loaded = load_data(uploaded)
            except ValueError as _e:
                st.error(str(_e))
                st.stop()
            except Exception as _e:
                st.error(f"Could not read file: {_e}")
                st.stop()
            reset_state_for_new_df()
            st.session_state["df"] = _loaded
            st.session_state["user_uploaded"] = True
            st.session_state["chart_title_override"] = ""
            st.session_state["pid_columns"] = detect_pid_columns(_loaded)
            st.rerun()

        if st.button("↩  Reset to demo data", key="btn_reset_demo", use_container_width=True):
            st.session_state["df"] = None
            st.session_state["user_uploaded"] = False
            st.session_state["chart_title_override"] = ""
            reset_state_for_new_df()
            st.rerun()
    else:
        st.markdown(
            '<p style="font-size:0.78rem;color:#8A8278;margin:0 0 6px;">Demo: UK Government Spending 2024/25</p>',
            unsafe_allow_html=True,
        )
        uploaded = st.file_uploader(
            "Try with your own data",
            type=["csv", "tsv", "xlsx"],
            key="uploader_main",
            label_visibility="collapsed",
        )
        if uploaded:
            try:
                _loaded = load_data(uploaded)
            except ValueError as _e:
                st.error(str(_e))
                st.stop()
            except Exception as _e:
                st.error(f"Could not read file: {_e}")
                st.stop()
            reset_state_for_new_df()
            st.session_state["df"] = _loaded
            st.session_state["user_uploaded"] = True
            st.session_state["chart_title_override"] = ""
            st.session_state["pid_columns"] = detect_pid_columns(_loaded)
            st.rerun()

    st.markdown("---")

    # ── Chart style ──────────────────────────────────────────
    st.markdown('<span class="sidebar-label">Chart Style</span>', unsafe_allow_html=True)
    st.radio(
        "",
        options=list(STYLES.keys()),
        format_func=lambda k: "Archim" if k == "archimedes" else STYLES[k].display_name,
        horizontal=True,
        key="style_name",
        label_visibility="collapsed",
    )

    # ── Chart type ───────────────────────────────────────────
    st.markdown('<span class="sidebar-label">Chart Type</span>', unsafe_allow_html=True)
    st.radio(
        "",
        ["Auto", "Bar", "Line", "Scatter", "Histogram", "Pareto"],
        key="chart_type_ui",
        label_visibility="collapsed",
    )

    st.markdown("---")

    # ── Export ───────────────────────────────────────────────
    st.markdown('<span class="sidebar-label">Export</span>', unsafe_allow_html=True)

    _png_wm     = st.session_state.get("last_chart_png_watermarked")
    _chart_obj  = st.session_state.get("last_chart_obj")
    _chart_type_sb = st.session_state.get("last_chart_type")
    _df_sb      = st.session_state.get("df")
    _x_sb       = st.session_state.get("x_col")
    _y_sb       = st.session_state.get("y_col")

    if _png_wm:
        st.download_button(
            "↓  PNG — Free (watermarked)",
            data=_png_wm,
            file_name="atlas.png",
            mime="image/png",
            use_container_width=True,
        )
    else:
        st.button("↓  PNG — Free (watermarked)", disabled=True, use_container_width=True)

    with st.expander("Export Pack"):
        st.caption("Remove watermark · high-quality PNG, SVG, Excel, PDF.")
        st.caption("Coming soon — purchase to unlock.")

    _entitled = is_export_entitled()
    st.session_state["export_entitled"] = _entitled

    if _entitled and _chart_obj is not None:
        hi_png = chart_to_png_bytes(_chart_obj, scale=3.0)
        svg    = chart_to_svg_bytes(_chart_obj)

        if _chart_type_sb == "Bar" and _x_sb and _y_sb and _df_sb is not None:
            _tn = st.session_state.get("top_n", 20)
            _ar = st.session_state.get("as_rate", False)
            _sd = st.session_state.get("sort_desc", True)
            table_df = agg_bar_data(_df_sb, _x_sb, _y_sb, as_rate=_ar, top_n=_tn, sort_desc=_sd)
            subtitle = f"Bar · Top {_tn} by {_y_sb} · X={_x_sb} · % of total={_ar}"
        elif _chart_type_sb == "Pareto" and _x_sb and _y_sb and _df_sb is not None:
            _tn = st.session_state.get("top_n", 20)
            table_df = agg_pareto_data(_df_sb, _x_sb, _y_sb, top_n=_tn)
            subtitle  = f"Pareto · Top {_tn} by {_y_sb} · X={_x_sb}"
        elif _chart_type_sb in ("Line", "Scatter") and _x_sb and _y_sb and _df_sb is not None:
            table_df = _df_sb[[_x_sb, _y_sb]].dropna().head(500)
            subtitle  = f"{_chart_type_sb} · X={_x_sb} · Y={_y_sb} · First 500 rows"
        elif _chart_type_sb == "Histogram" and _x_sb and _df_sb is not None:
            table_df = _df_sb[[_x_sb]].dropna().head(500)
            subtitle  = f"Histogram · X={_x_sb} · First 500 rows"
        else:
            table_df, subtitle = None, ""

        xlsx = df_to_formatted_xlsx_bytes(table_df, title="Atlas Export", subtitle=subtitle) if table_df is not None else None
        pdf  = df_to_pdf_bytes(table_df, title="Atlas Export", subtitle=subtitle) if table_df is not None else None

        st.download_button("PNG (High quality)", hi_png, "atlas-hq.png", "image/png", use_container_width=True)
        st.download_button("SVG (Vector)", svg, "atlas.svg", "image/svg+xml", use_container_width=True)
        if xlsx:
            st.download_button(
                "Excel (Formatted)", data=xlsx, file_name="atlas-table.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        if pdf:
            st.download_button(
                "PDF (Table)", data=pdf, file_name="atlas-table.pdf",
                mime="application/pdf", use_container_width=True,
            )
    elif not _entitled:
        st.caption("Unlock Export Pack for high-quality PNG + SVG + Excel + PDF.")

# ─────────────────────────────────────────────────────────────
# MAIN AREA
# ─────────────────────────────────────────────────────────────
df = st.session_state["df"]

if df is None:
    st.markdown(
        '<div style="display:flex;align-items:center;justify-content:center;height:62vh;">'
        '<div style="text-align:center;max-width:360px;">'
        '<p style="font-size:1.8rem;margin:0;opacity:0.3;">◫</p>'
        '<p style="color:#7A7268;font-size:0.90rem;margin-top:0.75rem;line-height:1.6;">'
        'Upload a CSV, TSV or XLSX file — or enable the demo dataset — using the sidebar.</p>'
        '</div></div>',
        unsafe_allow_html=True,
    )
    st.stop()

# PID warning — shown persistently while flagged data is loaded
_pid_cols = st.session_state.get("pid_columns", [])
if _pid_cols:
    st.warning(
        f"**Possible personal data detected** — the following columns may contain "
        f"patient-identifiable information: **{', '.join(_pid_cols)}**. "
        "Please remove identifiable columns before proceeding. "
        "Atlas does not store your data, but you should not upload patient-identifiable information."
    )

# Clean column names
df.columns = [str(c).strip() for c in df.columns]

# Initialise X/Y
if st.session_state["x_col"] is None or st.session_state["y_col"] is None:
    set_default_xy_from_auto(df)
    if st.session_state["x_col"] is None or st.session_state["y_col"] is None:
        x, y = pick_fallback_xy(df)
        st.session_state["x_col"] = x
        st.session_state["y_col"] = y

numeric_cols = df.select_dtypes(include="number").columns.tolist()
mode_now     = st.session_state["chart_type_ui"]

# Normalise X/Y for chart types with constraints
if mode_now == "Scatter":
    _x, _y = st.session_state.get("x_col"), st.session_state.get("y_col")
    if _x not in numeric_cols or _y not in numeric_cols or _x == _y:
        if len(numeric_cols) >= 2:
            st.session_state["x_col"], st.session_state["y_col"] = numeric_cols[0], numeric_cols[1]
        elif len(numeric_cols) == 1:
            st.session_state["x_col"] = st.session_state["y_col"] = numeric_cols[0]
        else:
            st.session_state["x_col"] = st.session_state["y_col"] = None
elif mode_now == "Histogram":
    if st.session_state.get("x_col") not in numeric_cols:
        st.session_state["x_col"] = numeric_cols[0] if numeric_cols else None
    st.session_state["y_col"] = None

x_col = st.session_state["x_col"]
y_col = st.session_state["y_col"]

if mode_now == "Auto":
    set_default_xy_from_auto(df)
    chart_type = st.session_state.get("chart_type_effective", "Bar")
    auto_info  = st.session_state.get("auto_info")
else:
    chart_type = mode_now
    auto_info  = None

# Bar / Pareto controls
if chart_type in ("Bar", "Pareto"):
    top_n      = st.session_state.get("top_n", 20)
    sort_desc  = st.session_state.get("sort_desc", True)
    as_rate    = st.session_state.get("as_rate", False)
    show_labels = st.session_state.get("show_labels", True)
    bar_flip   = st.session_state.get("bar_flip", False)
else:
    top_n, sort_desc, as_rate, show_labels, bar_flip = 20, True, False, True, False

y_col_effective = None if chart_type == "Histogram" else y_col
_active_style   = get_style(st.session_state.get("style_name", "midas"))

# Chart title
_title_override = st.session_state.get("chart_title_override", "")
if _title_override:
    _chart_title = _title_override
elif chart_type == "Histogram":
    _chart_title = f"Distribution of {x_col}"
elif y_col_effective and x_col:
    _chart_title = f"{y_col_effective} by {x_col}"
elif x_col:
    _chart_title = x_col
else:
    _chart_title = "Chart"

# Build chart
chart           = None
png_watermarked = None
_chart_warning  = None
_chart_error    = None
try:
    if chart_type == "Scatter" and (x_col is None or y_col is None):
        _chart_warning = "Scatter needs two numeric columns."
    elif chart_type == "Scatter" and x_col == y_col:
        _chart_warning = "Scatter requires X \u2260 Y"
    else:
        # Auto mode: choose orientation by category count.
        # ≤12 unique values → vertical column chart; >12 → horizontal bar.
        # Manual mode: respect the user's Flip toggle.
        if mode_now == "Auto" and chart_type == "Bar" and x_col and x_col in df.columns:
            _n_cats = df[x_col].nunique()
            _orient = "v" if _n_cats <= 12 else "h"
        else:
            _orient = "v" if bar_flip else "h"

        chart = build_chart(
            df, chart_type, x_col, y_col_effective,
            top_n, show_labels, sort_desc, as_rate,
            orient=_orient,
            style=_active_style,
            chart_title=_chart_title,
        )
except Exception as e:
    _chart_error = str(e)

# Persist for sidebar export; track rendered columns so any column change
# always triggers a fresh render (guards against any downstream caching).
if chart:
    _wm_text        = f"{_active_style.display_name} \u00b7 Atlas"
    png_watermarked = add_png_watermark(
        chart_to_png_bytes(chart, scale=2.0),
        text=_wm_text,
        bg_color=_active_style.bg_page,
        brand_mark_color=_active_style.brand_mark_color,
    )
    st.session_state["last_chart_png_watermarked"] = png_watermarked
    st.session_state["last_chart_obj"]  = chart
    st.session_state["last_chart_type"] = chart_type
    st.session_state["_last_rendered_x"] = x_col
    st.session_state["_last_rendered_y"] = y_col_effective
else:
    st.session_state["last_chart_obj"]             = None
    st.session_state["last_chart_png_watermarked"] = None

# Column pool for chip buttons
header_cols  = numeric_cols if mode_now in ["Scatter", "Histogram"] else df.columns.tolist()
MAX_HEADERS  = 8
visible_cols = header_cols[:MAX_HEADERS] if header_cols else []

# ─────────────────────────────────────────────────────────────
# Two-column layout: chart workspace (70%) + Analyse panel (30%)
# ─────────────────────────────────────────────────────────────
_chart_col, _analyse_col = st.columns([7, 3])

with _chart_col:
    # ── Tabbed workspace ──────────────────────────────────────
    with st.container(border=True):
        chart_tab, data_tab = st.tabs(["Chart", "Data"])

        # ── Chart tab ─────────────────────────────────────────
        with chart_tab:
            if _chart_warning:
                st.warning(_chart_warning)
            elif _chart_error:
                st.error(_chart_error)
            elif png_watermarked:
                st.image(png_watermarked, use_container_width=True)

            if auto_info:
                st.caption(f"Auto: {auto_info.confidence}% \u2014 {auto_info.reason}")
                _alt_suggestions = [s for s in st.session_state.get("auto_suggestions", []) if s is not auto_info]
                if _alt_suggestions:
                    _alt_cols = st.columns(len(_alt_suggestions))
                    for _i, _sug in enumerate(_alt_suggestions):
                        _sug_label = _CHART_LABEL_MAP.get(_sug.chart_type, _sug.chart_type.title())
                        with _alt_cols[_i]:
                            if st.button(
                                f"{_sug_label} ({_sug.confidence}%)",
                                help=_sug.reason,
                                use_container_width=True,
                                key=f"alt_sug_{_i}",
                            ):
                                st.session_state["chart_type_ui"] = _sug_label
                                if _sug.spec.get("x") in df.columns:
                                    st.session_state["x_col"] = _sug.spec["x"]
                                if _sug.spec.get("y") in df.columns:
                                    st.session_state["y_col"] = _sug.spec["y"]
                                st.rerun()

            # ── Chart-specific option strip ────────────────────
            st.divider()
            if chart_type == "Bar":
                bc1, bc2, bc3, bc4, bc5 = st.columns(5)
                with bc1:
                    st.slider("Top N", 5, 50, st.session_state.get("top_n", 20), 5, key="top_n")
                with bc2:
                    st.toggle("Sort desc", value=st.session_state.get("sort_desc", True), key="sort_desc")
                with bc3:
                    st.toggle("% of total", value=st.session_state.get("as_rate", False), key="as_rate")
                with bc4:
                    st.toggle("Labels", value=st.session_state.get("show_labels", True), key="show_labels")
                with bc5:
                    st.toggle("Flip", value=st.session_state.get("bar_flip", False), key="bar_flip")
            elif chart_type == "Pareto":
                pc1, _pc_rest = st.columns([1, 4])
                with pc1:
                    st.slider("Top N", 5, 50, st.session_state.get("top_n", 20), 5, key="top_n")

        # ── Data tab ──────────────────────────────────────────
        with data_tab:
            _picker_col, _table_col = st.columns([1, 3])

            with _picker_col:
                st.radio("Assign to:", ["X", "Y"], horizontal=True, key="assign_target")
                if not visible_cols:
                    st.warning("No columns.")
                else:
                    for col_name in visible_cols:
                        label = col_name
                        if col_name == st.session_state["x_col"]:
                            label = f"X \u00b7 {col_name}"
                        elif col_name == st.session_state.get("y_col"):
                            label = f"Y \u00b7 {col_name}"
                        if st.button(label, use_container_width=True, key=f"hdr_{mode_now}_{col_name}"):
                            if st.session_state["assign_target"] == "X":
                                st.session_state["x_col"] = col_name
                            else:
                                st.session_state["y_col"] = col_name
                            # Invalidate cached chart so the next render is always fresh
                            st.session_state["last_chart_png_watermarked"] = None
                            st.session_state["last_chart_obj"] = None
                            st.rerun()

            with _table_col:
                if visible_cols:
                    st.dataframe(
                        highlight_used_columns(
                            df[visible_cols].copy(),
                            [st.session_state.get("x_col"), st.session_state.get("y_col")],
                        ),
                        use_container_width=True,
                        height=380,
                    )

            if len(df.columns) > 6:
                with st.expander("More columns"):
                    filter_text = st.text_input(
                        "Filter columns", value="", placeholder="type to filter\u2026",
                        key="filter_columns",
                    ).lower()
                    pool     = numeric_cols if mode_now in ["Scatter", "Histogram"] else df.columns.tolist()
                    filtered = [c for c in pool if filter_text in c.lower()]
                    if mode_now in ["Scatter", "Histogram"] and not filtered:
                        st.info("No numeric columns match your filter.")
                    else:
                        more_cols = st.columns(4, gap="small")
                        for i, col_name in enumerate(filtered):
                            with more_cols[i % 4]:
                                if st.button(col_name, use_container_width=True, key=f"more_{mode_now}_{col_name}"):
                                    if st.session_state["assign_target"] == "X":
                                        st.session_state["x_col"] = col_name
                                    else:
                                        st.session_state["y_col"] = col_name
                                    st.session_state["last_chart_png_watermarked"] = None
                                    st.session_state["last_chart_obj"] = None
                                    st.rerun()

# ── Analyse panel (right column — same vertical level as chart) ──
with _analyse_col:
    st.markdown(
        '<p class="analyse-header">Analyse</p>',
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.text_area(
            "",
            value="AI insight generation coming in the next release.",
            height=96,
            disabled=True,
            key="explain_text",
            label_visibility="collapsed",
        )
        st.button("Explain", disabled=True, use_container_width=True, key="btn_explain")
