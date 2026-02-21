import streamlit as st
import pandas as pd

from core.transform import pick_default_x, pick_default_y
from core.data_loader import load_data
from core.export_render import chart_to_png_bytes, chart_to_svg_bytes
from exports.excel_export import df_to_formatted_xlsx_bytes
from exports.pdf_export import df_to_pdf_bytes
from core.watermark import add_png_watermark
from core.charts import bar_chart, line_chart, scatter_chart, histogram
from core.recommend import profile_columns, recommend_charts


@st.cache_data(show_spinner=False)
def _cached_profiles(df: pd.DataFrame):
    return profile_columns(df)


@st.cache_data(show_spinner=False)
def _cached_suggestions(df: pd.DataFrame, user_x: str | None, user_y: str | None):
    profiles = profile_columns(df)
    return recommend_charts(df, profiles, user_x=user_x, user_y=user_y)


st.set_page_config(page_title="Atlas Lite", layout="wide")

# Ensure entitlement state exists (dev stub for now)
st.session_state.setdefault("export_entitled", False)

# -----------------------------
# Sidebar: Upload + Controls
# -----------------------------
with st.sidebar:
    st.image("assets/MAtlas01.png", use_container_width=True)

    data_mode = st.radio("Data source", ["Upload file", "Demo dataset (dev)"])

    uploaded = None
    if data_mode == "Upload file":
        uploaded = st.file_uploader("Upload data (CSV or XLSX)", type=["csv", "xlsx"])

    chart_type_ui = st.selectbox("Chart type", ["Auto", "Bar", "Line", "Scatter", "Histogram"])
    st.subheader("Chart settings")

# -----------------------------
# Load data
# -----------------------------
df = None

if data_mode == "Demo dataset (dev)":
    df = load_data("demo_data/bh_completed_by_mon.csv")
else:
    if not uploaded:
        st.title("Atlas Lite")
        st.caption("Upload data → choose X and Y → export publication-ready charts.")
        st.info("Upload a CSV or XLSX to begin.")
        st.stop()
    df = load_data(uploaded)

# Clean column names defensively (Altair likes strings)
df.columns = [str(c).strip() for c in df.columns]

numeric_cols = df.select_dtypes(include="number").columns.tolist()
cat_cols = [c for c in df.columns if c not in numeric_cols]

if not numeric_cols:
    st.error("No numeric columns detected.")
    st.stop()

# -----------------------------
# Auto recommendation (translate Auto -> concrete chart + suggested defaults)
# -----------------------------
auto_info = None
auto_suggestions = None
chart_type = chart_type_ui  # working chart type (may be overridden by Auto)

if chart_type_ui == "Auto":
    auto_suggestions = _cached_suggestions(df, None, None)
    auto_info = auto_suggestions[0]

    label_map = {"bar": "Bar", "line": "Line", "scatter": "Scatter", "histogram": "Histogram"}
    chart_type = label_map.get(auto_info.chart_type, "Bar")


# Defaults (your existing logic; bar-leaning but fine)
def pick_default_xy(chart_type_local, numeric_cols_local, cat_cols_local, df_local):
    if chart_type_local == "Scatter":
        if len(numeric_cols_local) >= 2:
            return numeric_cols_local[0], numeric_cols_local[1]
        if len(numeric_cols_local) == 1:
            return numeric_cols_local[0], numeric_cols_local[0]  # fallback, will be handled
        return None, None

    if chart_type_local == "Histogram":
        return (numeric_cols_local[0], None) if numeric_cols_local else (None, None)

    if chart_type_local == "Line":
        # Prefer a datetime-like column
        for col in df_local.columns:
            if pd.api.types.is_datetime64_any_dtype(df_local[col]):
                return col, numeric_cols_local[0]
        # Fallback: use first column as X (often Month) and first numeric as Y
        return df_local.columns[0], numeric_cols_local[0]

    # Bar default (your existing logic)
    y_default = pick_default_y(numeric_cols_local)
    x_default = pick_default_x(df_local, cat_cols_local, y_default) if cat_cols_local else df_local.columns[0]
    return x_default, y_default


default_x, default_y = pick_default_xy(chart_type, numeric_cols, cat_cols, df)

# If Auto suggested X/Y, prefer them as defaults (without breaking existing logic)
if auto_info is not None:
    sx = auto_info.spec.get("x")
    sy = auto_info.spec.get("y")

    if sx in df.columns:
        default_x = sx
    if sy in df.columns:
        default_y = sy

# -----------------------------
# Sidebar: Chart controls (single source of truth)
# -----------------------------
with st.sidebar:
    # X candidates
    if chart_type in ["Scatter", "Histogram"]:
        x_candidates = numeric_cols
        x_label = "X (numeric)"
    else:
        x_candidates = cat_cols if cat_cols else df.columns.tolist()
        x_label = "X"

    if not x_candidates:
        st.error("No valid X columns for this chart type.")
        st.stop()

    x_index = x_candidates.index(default_x) if default_x in x_candidates else 0
    x_col = st.selectbox(x_label, x_candidates, index=x_index)

    # Y candidates
    if chart_type in ["Bar", "Line", "Scatter"]:
        if chart_type == "Scatter":
            y_candidates = [c for c in numeric_cols if c != x_col]
            if not y_candidates:
                st.error("Need at least two numeric columns for a scatter chart.")
                st.stop()
            y_index = y_candidates.index(default_y) if default_y in y_candidates else 0
            y_col = st.selectbox("Y (numeric)", y_candidates, index=min(y_index, len(y_candidates) - 1))
        else:
            y_index = numeric_cols.index(default_y) if default_y in numeric_cols else 0
            y_col = st.selectbox("Y (value)", numeric_cols, index=y_index)
    else:
        y_col = None

    # Bar-only options
    if chart_type == "Bar":
        sort_desc = st.toggle("Sort descending", value=True)
        as_rate = st.toggle("Show as % of total", value=False)
        top_n = st.slider("Top N", 5, 50, 20, 5)
        show_labels = st.toggle("Show value labels", value=True)
    else:
        # safe defaults for non-bar charts
        sort_desc, as_rate, top_n, show_labels = True, False, 20, False

# -----------------------------
# Build selected chart (explicit if/elif chain)
# -----------------------------
if chart_type == "Bar":
    chart_clean = bar_chart(
        df, x_col, y_col,
        top_n=top_n,
        show_labels=show_labels,
        sort_desc=sort_desc,
        as_rate=as_rate,
    )
elif chart_type == "Line":
    chart_clean = line_chart(df, x_col, y_col)
elif chart_type == "Scatter":
    chart_clean = scatter_chart(df, x_col, y_col)
elif chart_type == "Histogram":
    chart_clean = histogram(df, x_col, bins=30)
else:
    st.error(f"Unknown chart type: {chart_type}")
    st.stop()

# -----------------------------
# Build preview image (watermarked)
# -----------------------------
preview_png = chart_to_png_bytes(chart_clean, scale=0.9)
preview_png = add_png_watermark(preview_png, text="Atlas Lite")

# -----------------------------
# Pre-calc premium exports ONLY if entitled
# -----------------------------
hi_png = svg = xlsx = pdf = None

if st.session_state.get("export_entitled", False):
    hi_png = chart_to_png_bytes(chart_clean, scale=3.0)
    svg = chart_to_svg_bytes(chart_clean)

    # Table export:
    # - Bar: aggregated top-N table
    # - Line/Scatter: selected columns (first 500 rows)
    # - Histogram: selected X (first 500 rows)
    if chart_type == "Bar":
        d = df[[x_col, y_col]].dropna()
        agg = d.groupby(x_col, as_index=False)[y_col].sum()

        if as_rate:
            total = agg[y_col].sum()
            if total > 0:
                agg[y_col] = (agg[y_col] / total) * 100

        agg = agg.sort_values(y_col, ascending=not sort_desc).head(top_n)
        table_df = agg
        subtitle = f"{chart_type} | Top {top_n} by {y_col} | X={x_col} | % of total={as_rate}"

    elif chart_type in ["Line", "Scatter"]:
        table_df = df[[x_col, y_col]].dropna().head(500)
        subtitle = f"{chart_type} | X={x_col} | Y={y_col} | First 500 rows"

    else:  # Histogram
        table_df = df[[x_col]].dropna().head(500)
        subtitle = f"{chart_type} | X={x_col} | First 500 rows"

    title = "Atlas Export"
    xlsx = df_to_formatted_xlsx_bytes(table_df, title=title, subtitle=subtitle)
    pdf = df_to_pdf_bytes(table_df, title=title, subtitle=subtitle)

# -----------------------------
# Main: Quadrant layout
# -----------------------------
st.title("Atlas Lite")
st.caption("Clean charts with presentation-ready exports.")
st.caption(f"{chart_type_ui} • {uploaded.name if uploaded else 'Demo dataset'}")

left_top, right_top = st.columns([2, 1], gap="large")
left_bottom, right_bottom = st.columns([2, 1], gap="large")

with left_top:
    st.subheader("Chart")
    st.image(preview_png, width=720)
    st.caption(f"{len(df):,} rows • {len(df.columns)} columns")

with right_top:
    st.subheader("Summary")
    st.metric("Rows", f"{len(df):,}")
    st.metric("Columns", f"{len(df.columns):,}")
    st.write(f"**Chart:** {chart_type}")
    st.write(f"**X:** {x_col}")
    if y_col:
        st.write(f"**Y:** {y_col}")

    if auto_info is not None:
        st.write(f"**Auto confidence:** {auto_info.confidence}%")
        st.caption(auto_info.reason)

        if auto_suggestions is not None:
            with st.expander("Other auto suggestions"):
                for s in auto_suggestions[1:]:
                    st.write(f"- `{s.chart_type}` ({s.confidence}%) — {s.reason}")

    if chart_type == "Bar":
        st.write(f"**Top N:** {top_n}")
        st.write(f"**Sorted desc:** {sort_desc}")
        st.write(f"**% of total:** {as_rate}")
        st.write(f"**Labels:** {show_labels}")

with left_bottom:
    st.subheader("Data preview")
    st.dataframe(df.head(15), use_container_width=True, height=260)

with right_bottom:
    st.subheader("Export")

    st.download_button(
        "PNG (Free, watermarked)",
        data=preview_png,
        file_name="atlas-lite.png",
        mime="image/png"
    )

    with st.expander("Export Pack (one-off)"):
        st.caption("Remove watermark and unlock high-quality exports (PNG, SVG, Excel, PDF).")
        st.session_state["export_entitled"] = st.toggle(
            "Simulate purchase (dev)",
            value=st.session_state.get("export_entitled", False)
        )

    if st.session_state.get("export_entitled", False):
        st.download_button("PNG (High quality)", hi_png, "atlas.png", "image/png")
        st.download_button("SVG (Vector)", svg, "atlas.svg", "image/svg+xml")
        st.download_button(
            "Excel (Formatted)",
            data=xlsx,
            file_name="atlas-table.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.download_button(
            "PDF (Table)",
            data=pdf,
            file_name="atlas-table.pdf",
            mime="application/pdf"
        )
    else:
        st.caption("Unlock Export Pack for high-quality PNG + SVG, formatted Excel + PDF.")