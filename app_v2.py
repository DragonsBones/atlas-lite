import streamlit as st
import pandas as pd

from core.data_loader import load_data
from core.charts import bar_chart, line_chart, scatter_chart, histogram
from core.export_render import chart_to_png_bytes, chart_to_svg_bytes
from core.watermark import add_png_watermark
from core.recommend import profile_columns, recommend_charts
from core.themes import get_style, MIDAS, STYLES
from exports.excel_export import df_to_formatted_xlsx_bytes
from exports.pdf_export import df_to_pdf_bytes

st.set_page_config(page_title="Atlas Lite", layout="wide")

with open("assets/style.css") as _f:
    st.markdown(f"<style>{_f.read()}</style>", unsafe_allow_html=True)

# -----------------------------
# Session state
# -----------------------------
st.session_state.setdefault("df", None)
st.session_state.setdefault("dev_mode", True)
st.session_state.setdefault("chart_type_ui", "Auto")
st.session_state.setdefault("x_col", None)
st.session_state.setdefault("y_col", None)
st.session_state.setdefault("assign_target", "X")
st.session_state.setdefault("export_entitled", False)
st.session_state.setdefault("top_n", 20)
st.session_state.setdefault("sort_desc", True)
st.session_state.setdefault("as_rate", False)
st.session_state.setdefault("show_labels", True)
st.session_state.setdefault("style_name", "midas")
st.session_state.setdefault("last_chart_png_watermarked", None)
st.session_state.setdefault("last_chart_type", None)
st.session_state.setdefault("last_chart_obj", None)

# -----------------------------
# Helpers
# -----------------------------
def reset_state_for_new_df():
    st.session_state["x_col"] = None
    st.session_state["y_col"] = None
    st.session_state["chart_type_effective"] = None
    st.session_state["auto_info"] = None

@st.cache_data(show_spinner=False)
def cached_profiles(df: pd.DataFrame):
    return profile_columns(df)

def highlight_used_columns(df: pd.DataFrame, used_cols: list[str]):
    used = {c for c in used_cols if c}

    def _highlight(col: pd.Series):
        return [
            "background-color: rgba(255, 215, 0, 0.20)" if col.name in used else ""
            for _ in col
        ]

    return df.head(20).style.apply(_highlight, axis=0)

def set_default_xy_from_auto(df: pd.DataFrame):
    profiles = cached_profiles(df)
    best = recommend_charts(df, profiles, user_x=None, user_y=None)[0]
    label_map = {"bar": "Bar", "line": "Line", "scatter": "Scatter", "histogram": "Histogram"}

    st.session_state["chart_type_effective"] = label_map.get(best.chart_type, "Bar")

    if st.session_state["x_col"] is None and best.spec.get("x") in df.columns:
        st.session_state["x_col"] = best.spec["x"]
    if st.session_state["y_col"] is None and best.spec.get("y") in df.columns:
        st.session_state["y_col"] = best.spec["y"]

    st.session_state["auto_info"] = best

def pick_fallback_xy(df: pd.DataFrame):
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = [c for c in df.columns if c not in numeric_cols]

    if not numeric_cols:
        return None, None

    x = cat_cols[0] if cat_cols else df.columns[0]
    y = numeric_cols[0]
    return x, y

def build_chart(df, chart_type, x_col, y_col, top_n=20, show_labels=True, sort_desc=True, as_rate=False, style=MIDAS, chart_title: str = ""):
    if chart_type == "Bar":
        return bar_chart(df, x_col, y_col, top_n=top_n, show_labels=show_labels, sort_desc=sort_desc, as_rate=as_rate, style=style, chart_title=chart_title)
    if chart_type == "Line":
        return line_chart(df, x_col, y_col, style=style, chart_title=chart_title)
    if chart_type == "Scatter":
        return scatter_chart(df, x_col, y_col, style=style, chart_title=chart_title)
    if chart_type == "Histogram":
        return histogram(df, x_col, bins=30, style=style, chart_title=chart_title)
    return bar_chart(df, x_col, y_col, top_n=top_n, show_labels=show_labels, sort_desc=sort_desc, as_rate=as_rate, style=style, chart_title=chart_title)

# -----------------------------
# Page Header
# -----------------------------
st.title("Atlas Lite")
st.caption("Upload \u2192 Auto chart \u2192 Explain (soon) \u2192 Export")

# -----------------------------
# Layout — outer split
# -----------------------------
left, right = st.columns([2, 1], gap="large")

# ============================================================
# LEFT PANEL
# ============================================================
with left:

    # ── Data controls (load / upload) ────────────────────────
    df = st.session_state["df"]

    if df is not None:
        if st.button("Load different data", key="btn_load_new"):
            st.session_state["df"] = None
            reset_state_for_new_df()
            st.rerun()

    if df is None:
        upload_cols = st.columns(2)
        with upload_cols[0]:
            uploaded = st.file_uploader("Upload CSV or XLSX", type=["csv", "xlsx"], key="uploader_main")
        with upload_cols[1]:
            demo = st.toggle("Demo dataset (dev)", value=False, key="toggle_demo")

        if demo:
            df = load_data("demo_data/bh_completed_by_mon.csv")
            reset_state_for_new_df()
            st.session_state["df"] = df
            st.rerun()

        if uploaded:
            df = load_data(uploaded)
            reset_state_for_new_df()
            st.session_state["df"] = df
            st.rerun()

        st.info("Load data to begin.")
        st.stop()

    # Clean column names
    df.columns = [str(c).strip() for c in df.columns]

    # Initialise X/Y if needed
    if st.session_state["x_col"] is None or st.session_state["y_col"] is None:
        set_default_xy_from_auto(df)
        if st.session_state["x_col"] is None or st.session_state["y_col"] is None:
            x, y = pick_fallback_xy(df)
            st.session_state["x_col"] = x
            st.session_state["y_col"] = y

    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    mode_now = st.session_state["chart_type_ui"]

    # Normalise X/Y inline — no extra st.rerun() needed, chart builds in one pass
    if mode_now == "Scatter":
        _x = st.session_state.get("x_col")
        _y = st.session_state.get("y_col")
        if _x not in numeric_cols or _y not in numeric_cols or _x == _y:
            if len(numeric_cols) >= 2:
                st.session_state["x_col"] = numeric_cols[0]
                st.session_state["y_col"] = numeric_cols[1]
            elif len(numeric_cols) == 1:
                st.session_state["x_col"] = numeric_cols[0]
                st.session_state["y_col"] = numeric_cols[0]
            else:
                st.session_state["x_col"] = None
                st.session_state["y_col"] = None
    elif mode_now == "Histogram":
        if st.session_state.get("x_col") not in numeric_cols:
            st.session_state["x_col"] = numeric_cols[0] if numeric_cols else None
        st.session_state["y_col"] = None

    x_col = st.session_state["x_col"]
    y_col = st.session_state["y_col"]

    if mode_now == "Auto":
        set_default_xy_from_auto(df)
        chart_type = st.session_state.get("chart_type_effective", "Bar")
        auto_info = st.session_state.get("auto_info")
    else:
        chart_type = mode_now
        auto_info = None

    # Bar controls — read from session state; widgets rendered inside Chart tab
    if chart_type == "Bar":
        top_n = st.session_state.get("top_n", 20)
        sort_desc = st.session_state.get("sort_desc", True)
        as_rate = st.session_state.get("as_rate", False)
        show_labels = st.session_state.get("show_labels", True)
    else:
        top_n, sort_desc, as_rate, show_labels = 20, True, False, True

    y_col_effective = None if chart_type == "Histogram" else y_col
    _active_style = get_style(st.session_state.get("style_name", "midas"))

    # Derive chart title from column names
    if chart_type == "Histogram":
        _chart_title = f"Distribution of {x_col}"
    elif y_col_effective and x_col:
        _chart_title = f"{y_col_effective} by {x_col}"
    elif x_col:
        _chart_title = x_col
    else:
        _chart_title = "Chart"

    # Build chart before tabs render so result is available in Chart tab
    chart = None
    png_watermarked = None
    _chart_warning = None
    _chart_error = None
    try:
        if chart_type == "Scatter" and (x_col is None or y_col is None):
            _chart_warning = "Scatter needs two numeric columns."
        elif chart_type == "Scatter" and x_col == y_col:
            _chart_warning = "Scatter requires X \u2260 Y"
        else:
            chart = build_chart(df, chart_type, x_col, y_col_effective, top_n, show_labels, sort_desc, as_rate, style=_active_style, chart_title=_chart_title)
    except Exception as e:
        _chart_error = str(e)

    # Persist chart objects for right panel
    if chart:
        _wm_text = f"{_active_style.display_name} \u00b7 Atlas Lite"
        png_watermarked = add_png_watermark(chart_to_png_bytes(chart, scale=2.0), text=_wm_text, bg_color=_active_style.bg_page)
        st.session_state["last_chart_png_watermarked"] = png_watermarked
        st.session_state["last_chart_obj"] = chart
        st.session_state["last_chart_type"] = chart_type
    else:
        st.session_state["last_chart_obj"] = None

    # Column pool for chip buttons
    if mode_now in ["Scatter", "Histogram"]:
        header_cols = numeric_cols
    else:
        header_cols = df.columns.tolist()

    MAX_HEADERS = 8
    visible_cols = header_cols[:MAX_HEADERS] if header_cols else []

    # ── Tabbed container — Chart first (hero) ──────────────────
    with st.container(border=True):
        chart_tab, data_tab = st.tabs(["Chart", "Data"])

        # ── Chart tab — hero image + always-visible controls ──────
        with chart_tab:
            # Hero: chart is the dominant element
            if _chart_warning:
                st.warning(_chart_warning)
            elif _chart_error:
                st.error(_chart_error)
            elif png_watermarked:
                st.image(png_watermarked, use_container_width=True)

            if auto_info:
                st.caption(f"Auto: {auto_info.confidence}% \u2014 {auto_info.reason}")

            # Controls — compact strip below the chart, always rendered
            # (avoids expander collapsing on st.rerun() losing widget state)
            st.divider()
            _type_col, _style_col = st.columns([3, 2])
            with _type_col:
                st.radio(
                    "",
                    ["Auto", "Bar", "Line", "Scatter", "Histogram"],
                    horizontal=True,
                    key="chart_type_ui",
                )
            with _style_col:
                st.radio(
                    "Style",
                    options=list(STYLES.keys()),
                    format_func=lambda k: STYLES[k].display_name,
                    horizontal=True,
                    key="style_name",
                )

            if chart_type == "Bar":
                bc1, bc2, bc3, bc4 = st.columns(4)
                with bc1:
                    st.slider("Top N", 5, 50, st.session_state.get("top_n", 20), 5, key="top_n")
                with bc2:
                    st.toggle("Sort desc", value=st.session_state.get("sort_desc", True), key="sort_desc")
                with bc3:
                    st.toggle("% of total", value=st.session_state.get("as_rate", False), key="as_rate")
                with bc4:
                    st.toggle("Labels", value=st.session_state.get("show_labels", True), key="show_labels")

        # ── Data tab — compact column picker | table ────────────
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
                        "Filter columns", value="", placeholder="type to filter\u2026", key="filter_columns"
                    ).lower()

                    pool = numeric_cols if mode_now in ["Scatter", "Histogram"] else df.columns.tolist()
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
                                    st.rerun()

# ============================================================
# RIGHT PANEL — Style / Explain / Export
# ============================================================
with right:
    _df = st.session_state.get("df")
    _chart_type = st.session_state.get("last_chart_type")

    # Spacer to align with the "Load different data" button on the left
    if _df is not None:
        st.markdown('<div style="height: 3.4rem"></div>', unsafe_allow_html=True)

    with st.container(border=True):
        # ---- Explain ----
        st.caption("Explain — AI insight coming soon")
        st.text_area(
            "",
            value="Insight generation will be available in the next release.",
            height=120,
            disabled=True,
            key="explain_text",
            label_visibility="collapsed",
        )
        st.button("Explain", disabled=True, use_container_width=True, key="btn_explain")

        st.divider()

        # ---- Export ----
        st.caption("Export")

        _png_wm = st.session_state.get("last_chart_png_watermarked")
        _chart_obj = st.session_state.get("last_chart_obj")

        if _png_wm:
            st.download_button(
                "PNG (Free, watermarked)",
                data=_png_wm,
                file_name="atlas-lite.png",
                mime="image/png",
                use_container_width=True,
            )
        else:
            st.button("PNG (Free, watermarked)", disabled=True, use_container_width=True)

        with st.expander("Export Pack (one-off)"):
            st.caption("Remove watermark \u00b7 unlock high-quality PNG, SVG, Excel, PDF.")
            st.session_state["export_entitled"] = st.toggle(
                "Simulate purchase (dev)",
                value=st.session_state.get("export_entitled", False),
                key="toggle_entitled",
            )

        if st.session_state.get("export_entitled", False) and _chart_obj is not None:
            hi_png = chart_to_png_bytes(_chart_obj, scale=3.0)
            svg = chart_to_svg_bytes(_chart_obj)

            _x = st.session_state.get("x_col")
            _y = st.session_state.get("y_col")

            if _chart_type == "Bar" and _x and _y and _df is not None:
                _agg = _df[[_x, _y]].dropna().groupby(_x, as_index=False)[_y].sum()
                if st.session_state.get("as_rate", False):
                    _total = _agg[_y].sum()
                    if _total > 0:
                        _agg[_y] = (_agg[_y] / _total) * 100
                _top_n = st.session_state.get("top_n", 20)
                _agg = _agg.sort_values(_y, ascending=not st.session_state.get("sort_desc", True)).head(_top_n)
                table_df = _agg
                subtitle = f"Bar \u00b7 Top {_top_n} by {_y} \u00b7 X={_x} \u00b7 % of total={st.session_state.get('as_rate', False)}"

            elif _chart_type in ("Line", "Scatter") and _x and _y and _df is not None:
                table_df = _df[[_x, _y]].dropna().head(500)
                subtitle = f"{_chart_type} \u00b7 X={_x} \u00b7 Y={_y} \u00b7 First 500 rows"

            elif _chart_type == "Histogram" and _x and _df is not None:
                table_df = _df[[_x]].dropna().head(500)
                subtitle = f"Histogram \u00b7 X={_x} \u00b7 First 500 rows"

            else:
                table_df = None
                subtitle = ""

            xlsx = df_to_formatted_xlsx_bytes(table_df, title="Atlas Export", subtitle=subtitle) if table_df is not None else None
            pdf = df_to_pdf_bytes(table_df, title="Atlas Export", subtitle=subtitle) if table_df is not None else None

            st.download_button("PNG (High quality)", hi_png, "atlas.png", "image/png", use_container_width=True)
            st.download_button("SVG (Vector)", svg, "atlas.svg", "image/svg+xml", use_container_width=True)
            if xlsx:
                st.download_button(
                    "Excel (Formatted)",
                    data=xlsx,
                    file_name="atlas-table.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            if pdf:
                st.download_button(
                    "PDF (Table)",
                    data=pdf,
                    file_name="atlas-table.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
        elif not st.session_state.get("export_entitled", False):
            st.caption("Unlock Export Pack for high-quality PNG + SVG + Excel + PDF.")
