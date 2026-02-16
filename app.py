import streamlit as st
from core.transform import pick_default_x, pick_default_y
from core.data_loader import load_csv
from core.charts import bar_chart
from core.export_render import chart_to_png_bytes, chart_to_svg_bytes
from exports.excel_export import df_to_formatted_xlsx_bytes
from exports.pdf_export import df_to_pdf_bytes
from core.watermark import add_png_watermark

st.set_page_config(page_title="Atlas Lite", layout="wide")

# -----------------------------
# Sidebar: Upload + Controls
# -----------------------------
with st.sidebar:
    st.image("assets/MAtlas01.png", use_container_width=True)
    uploaded = st.file_uploader("Upload CSV", type=["csv"])

if not uploaded:
    st.title("Atlas Lite")
    st.caption("Upload a CSV → choose X and Y → get a clean bar chart.")
    st.info("Upload a CSV to begin.")
    st.stop()

df = load_csv(uploaded)

numeric_cols = df.select_dtypes(include="number").columns.tolist()
cat_cols = [c for c in df.columns if c not in numeric_cols]

if not numeric_cols:
    st.error("No numeric columns detected for Y.")
    st.stop()

if not cat_cols:
    st.error("No categorical columns detected for X.")
    st.stop()

default_y = pick_default_y(numeric_cols)
default_x = pick_default_x(df, cat_cols, default_y)

x_index = cat_cols.index(default_x) if default_x in cat_cols else 0
y_index = numeric_cols.index(default_y) if default_y in numeric_cols else 0

with st.sidebar:
    st.subheader("Chart settings")
    x_col = st.selectbox("X (category)", cat_cols, index=x_index)
    y_col = st.selectbox("Y (value)", numeric_cols, index=y_index)
    sort_desc = st.toggle("Sort descending", value=True)
    as_rate = st.toggle("Show as % of total", value=False)
    top_n = st.slider("Top N", min_value=5, max_value=50, value=20, step=5)
    show_labels = st.toggle("Show value labels", value=True)

# Ensure entitlement state exists (dev stub for now)
st.session_state.setdefault("export_entitled", False)

# -----------------------------
# Build chart + preview image
# -----------------------------
chart_clean = bar_chart(
    df, x_col, y_col,
    top_n=top_n,
    show_labels=show_labels,
    sort_desc=sort_desc,
    as_rate=as_rate,
)

# Preview: smaller raster + watermark (snip deterrence)
preview_png = chart_to_png_bytes(chart_clean, scale=0.9)
preview_png = add_png_watermark(preview_png, text="Atlas Lite")

# Pre-calc premium exports ONLY if entitled
hi_png = svg = xlsx = pdf = None
if st.session_state.get("export_entitled", False):
    hi_png = chart_to_png_bytes(chart_clean, scale=3.0)
    svg = chart_to_svg_bytes(chart_clean)

    # Aggregated table for exports (same logic as chart)
    d = df[[x_col, y_col]].dropna()
    agg = d.groupby(x_col, as_index=False)[y_col].sum()
    if as_rate:
        total = agg[y_col].sum()
        if total > 0:
            agg[y_col] = (agg[y_col] / total) * 100
    agg = agg.sort_values(y_col, ascending=not sort_desc).head(top_n)

    title = "Atlas Export"
    subtitle = f"Top {top_n} by {y_col} | X={x_col} | % of total={as_rate}"
    xlsx = df_to_formatted_xlsx_bytes(agg, title=title, subtitle=subtitle)
    pdf = df_to_pdf_bytes(agg, title=title, subtitle=subtitle)

# -----------------------------
# Main: Quadrant layout
# -----------------------------
st.title("Atlas Lite")
st.caption("Clean bar charts with presentation-ready exports.")
st.caption(f"Top {top_n} {x_col} by {y_col}")

left_top, right_top = st.columns([2, 1], gap="large")
left_bottom, right_bottom = st.columns([2, 1], gap="large")

with left_top:
    st.subheader("Chart")
    st.image(preview_png, width=720)
    st.caption(f"{uploaded.name} • {len(df):,} rows • {len(df.columns)} columns")

with right_top:
    st.subheader("Summary")
    st.metric("Rows", f"{len(df):,}")
    st.metric("Columns", f"{len(df.columns):,}")
    st.write(f"**X:** {x_col}")
    st.write(f"**Y:** {y_col}")
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
