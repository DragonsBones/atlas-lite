import streamlit as st
from core.transform import pick_default_x, pick_default_y
from core.data_loader import load_csv
from core.charts import bar_chart

st.set_page_config(page_title="Atlas Lite", layout="wide")

st.title("Atlas Lite")
st.caption("Upload a CSV → choose X and Y → get a clean bar chart.")

uploaded = st.file_uploader("Upload CSV", type=["csv"])

if not uploaded:
    st.info("Upload a CSV to begin.")
    st.stop()

df = load_csv(uploaded)

st.success("File loaded successfully.")
st.write(f"Rows: {len(df):,} | Columns: {len(df.columns):,}")
st.dataframe(df.head(10), use_container_width=True)

numeric_cols = df.select_dtypes(include="number").columns.tolist()
cat_cols = [c for c in df.columns if c not in numeric_cols]

st.divider()
st.subheader("Chart settings")

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

x_col = st.selectbox("X (category)", cat_cols, index=x_index)
y_col = st.selectbox("Y (value)", numeric_cols, index=y_index)
sort_desc = st.toggle("Sort descending", value=True)
as_rate = st.toggle("Show as % of total", value=False)
st.caption(f"Auto-selected: X = {x_col} | Y = {y_col}")

top_n = st.slider("Show top N categories", min_value=5, max_value=50, value=25, step=5)
show_labels = st.toggle("Show value labels", value=True)

st.markdown("## Bar chart")
st.caption(f"Showing top {top_n} by total {y_col}")
st.altair_chart(bar_chart(df, x_col, y_col, top_n=top_n, show_labels=show_labels,sort_desc=sort_desc,as_rate=as_rate,), use_container_width=True)
st.caption(f"Source: {uploaded.name}")